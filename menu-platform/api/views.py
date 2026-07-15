from datetime import timedelta

from django.db import IntegrityError
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from orders.models import Order
from orders.views import _apply_order_status_change
from restaurants.models import Product, Category, StaffMember, LoyaltyAccount, PromoCode

from .permissions import HasRestaurantRole, IsRestaurantAdmin, IsRestaurantOwner
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderStatusUpdateSerializer,
    ProductSerializer, CategorySerializer, DeviceTokenSerializer,
    StaffMemberSerializer, StaffCreateSerializer, RestaurantSettingsSerializer,
    LoyaltyAccountSerializer, LoyaltyPointsUpdateSerializer, PromoCodeSerializer,
)


class MeView(APIView):
    """Tells the app who's logged in and what they're allowed to do - mirrors
    what restaurant_context already injects into every web page."""
    permission_classes = [HasRestaurantRole]

    def get(self, request):
        restaurant = request.restaurant
        role = request.staff_role
        owner = restaurant.user
        return Response({
            'username': request.user.username,
            'role': role,
            'restaurant_id': restaurant.id,
            'restaurant_name': restaurant.name,
            'can_manage_menu': role in ('owner', 'admin'),
            'can_use_pro_features': role in ('owner', 'admin') and owner.has_ordering(),
            'can_view_stats': role in ('owner', 'admin') and owner.has_stats_dashboard(),
            'can_manage_staff': role == 'owner' and owner.has_staff_management(),
            'restaurant_accepts_orders': restaurant.allow_ordering and owner.has_ordering(),
        })


class OrderListView(generics.ListAPIView):
    """Any staff role (owner/admin/employee) can see the order queue."""
    serializer_class = OrderListSerializer
    permission_classes = [HasRestaurantRole]

    def get_queryset(self):
        queryset = Order.objects.filter(restaurant=self.request.restaurant)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [HasRestaurantRole]

    def get_queryset(self):
        return Order.objects.filter(restaurant=self.request.restaurant).prefetch_related(
            'order_items', 'status_logs__changed_by',
        )


class OrderStatusUpdateView(APIView):
    """Same status-change path the web dashboard uses (order_detail / update_order_status),
    so loyalty-point awarding and the audit trail behave identically from the app."""
    permission_classes = [HasRestaurantRole]

    def post(self, request, pk):
        order = generics.get_object_or_404(Order, pk=pk, restaurant=request.restaurant)
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']

        if new_status == order.status:
            return Response(OrderDetailSerializer(order).data)

        loyalty_points = _apply_order_status_change(order, new_status, request.user)
        order.refresh_from_db()
        data = OrderDetailSerializer(order).data
        data['loyalty_points_awarded'] = loyalty_points
        return Response(data)


class ProductListView(generics.ListAPIView):
    """Any staff role can view products (matches the web product_list view)."""
    serializer_class = ProductSerializer
    permission_classes = [HasRestaurantRole]

    def get_queryset(self):
        return Product.objects.filter(category__restaurant=self.request.restaurant).select_related('category')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ProductAvailabilityUpdateView(APIView):
    """Quick 86-an-item toggle - admin/owner only, matches product management
    permissions on the web (employees can view but not edit products)."""
    permission_classes = [IsRestaurantAdmin]

    def post(self, request, pk):
        product = generics.get_object_or_404(
            Product, pk=pk, category__restaurant=request.restaurant,
        )
        is_available = request.data.get('is_available')
        if not isinstance(is_available, bool):
            return Response({'error': 'is_available must be a boolean'}, status=status.HTTP_400_BAD_REQUEST)
        product.is_available = is_available
        product.save(update_fields=['is_available'])
        return Response(ProductSerializer(product, context={'request': request}).data)


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [HasRestaurantRole]

    def get_queryset(self):
        return Category.objects.filter(restaurant=self.request.restaurant, is_active=True)


class StatsView(APIView):
    """Owner/admin sales stats - identical query logic to stats_dashboard on the
    web, same Business-plan gate (owner.has_stats_dashboard())."""
    permission_classes = [IsRestaurantAdmin]

    def get(self, request):
        from orders.models import OrderItem

        restaurant = request.restaurant
        if not restaurant.user.has_stats_dashboard():
            return Response({'available': False})

        now = timezone.localtime(timezone.now())
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        orders_qs = Order.objects.filter(restaurant=restaurant).exclude(status='cancelled')

        def summarize(since):
            agg = orders_qs.filter(created_at__gte=since).aggregate(revenue=Sum('total'), count=Count('id'))
            return {'revenue': float(agg['revenue'] or 0), 'count': agg['count'] or 0}

        top_products = list(
            OrderItem.objects.filter(order__restaurant=restaurant)
            .exclude(order__status='cancelled')
            .values('name')
            .annotate(total_quantity=Sum('quantity'), total_revenue=Sum(F('price') * F('quantity')))
            .order_by('-total_quantity')[:5]
        )
        for row in top_products:
            row['total_revenue'] = float(row['total_revenue'] or 0)

        trend_start = today_start - timedelta(days=13)
        daily_revenue = (
            orders_qs.filter(created_at__gte=trend_start)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(revenue=Sum('total'))
        )
        trend_map = {row['day']: float(row['revenue'] or 0) for row in daily_revenue}
        trend = []
        for i in range(14):
            day = (trend_start + timedelta(days=i)).date()
            trend.append({'date': day.strftime('%d/%m'), 'revenue': trend_map.get(day, 0)})

        return Response({
            'available': True,
            'today': summarize(today_start),
            'week': summarize(week_start),
            'month': summarize(month_start),
            'top_products': top_products,
            'trend': trend,
        })


class StaffListView(APIView):
    """Owner-only: list/create staff accounts - mirrors staff_list on the web,
    same Business-plan gate (owner.has_staff_management())."""
    permission_classes = [IsRestaurantOwner]

    def get(self, request):
        restaurant = request.restaurant
        if not restaurant.user.has_staff_management():
            return Response({'available': False, 'results': []})
        members = StaffMember.objects.filter(restaurant=restaurant).select_related('user')
        return Response({'available': True, 'results': StaffMemberSerializer(members, many=True).data})

    def post(self, request):
        restaurant = request.restaurant
        if not restaurant.user.has_staff_management():
            return Response(
                {'error': 'Staff management is available on the Business plan.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = StaffCreateSerializer(data=request.data, context={'restaurant': restaurant})
        serializer.is_valid(raise_exception=True)
        staff = serializer.save()
        return Response(StaffMemberSerializer(staff).data, status=status.HTTP_201_CREATED)


class StaffDeleteView(APIView):
    permission_classes = [IsRestaurantOwner]

    def delete(self, request, pk):
        if not request.restaurant.user.has_staff_management():
            return Response(
                {'error': 'Staff management is available on the Business plan.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        staff = generics.get_object_or_404(StaffMember, pk=pk, restaurant=request.restaurant)
        user_to_remove = staff.user
        staff.delete()
        user_to_remove.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RestaurantSettingsView(APIView):
    """Mirrors restaurant_settings on the web - admin/owner, no plan gate."""
    permission_classes = [IsRestaurantAdmin]

    def get(self, request):
        return Response(RestaurantSettingsSerializer(request.restaurant).data)

    def patch(self, request):
        serializer = RestaurantSettingsSerializer(request.restaurant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class LoyaltyListView(APIView):
    """Mirrors loyalty_list on the web, same Pro-plan gate (owner.has_ordering())."""
    permission_classes = [IsRestaurantAdmin]

    def get(self, request):
        restaurant = request.restaurant
        if not restaurant.user.has_ordering():
            return Response({'available': False, 'results': []})
        accounts = LoyaltyAccount.objects.filter(restaurant=restaurant)
        search = request.query_params.get('q', '').strip()
        if search:
            accounts = accounts.filter(phone__icontains=search)
        return Response({'available': True, 'results': LoyaltyAccountSerializer(accounts, many=True).data})


class LoyaltyUpdateView(APIView):
    permission_classes = [IsRestaurantAdmin]

    def patch(self, request, pk):
        if not request.restaurant.user.has_ordering():
            return Response(
                {'error': 'Loyalty is available from the Pro plan.'}, status=status.HTTP_403_FORBIDDEN,
            )
        account = generics.get_object_or_404(LoyaltyAccount, pk=pk, restaurant=request.restaurant)
        serializer = LoyaltyPointsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account.points = serializer.validated_data['points']
        account.save(update_fields=['points'])
        return Response(LoyaltyAccountSerializer(account).data)

    def delete(self, request, pk):
        if not request.restaurant.user.has_ordering():
            return Response(
                {'error': 'Loyalty is available from the Pro plan.'}, status=status.HTTP_403_FORBIDDEN,
            )
        account = generics.get_object_or_404(LoyaltyAccount, pk=pk, restaurant=request.restaurant)
        account.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PromoCodeListView(APIView):
    """Mirrors promo_code_list on the web, same Pro-plan gate (owner.has_ordering())."""
    permission_classes = [IsRestaurantAdmin]

    def get(self, request):
        restaurant = request.restaurant
        if not restaurant.user.has_ordering():
            return Response({'available': False, 'results': []})
        promo_codes = PromoCode.objects.filter(restaurant=restaurant)
        return Response({'available': True, 'results': PromoCodeSerializer(promo_codes, many=True).data})

    def post(self, request):
        restaurant = request.restaurant
        if not restaurant.user.has_ordering():
            return Response(
                {'error': 'Discount codes are available from the Pro plan.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = PromoCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            promo = serializer.save(restaurant=restaurant)
        except IntegrityError:
            return Response({'error': 'This code already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PromoCodeSerializer(promo).data, status=status.HTTP_201_CREATED)


class PromoCodeDeleteView(APIView):
    permission_classes = [IsRestaurantAdmin]

    def delete(self, request, pk):
        if not request.restaurant.user.has_ordering():
            return Response(
                {'error': 'Discount codes are available from the Pro plan.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        promo = generics.get_object_or_404(PromoCode, pk=pk, restaurant=request.restaurant)
        promo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeviceTokenRegisterView(APIView):
    """Called once on app login / token refresh so the backend knows where to
    push new-order notifications for this user."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True}, status=status.HTTP_201_CREATED)
