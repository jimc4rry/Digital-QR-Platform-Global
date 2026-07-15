import csv
import logging
from decimal import Decimal
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction, DatabaseError
from django.db.models import F
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext as _
from .models import Order, OrderItem, OrderStatusLog
from restaurants.models import Restaurant, Product, ProductOption, PromoCode, LoyaltyAccount, RestaurantTable
from restaurants.permissions import restaurant_role_required
import json

logger = logging.getLogger(__name__)


def _truncate(value, max_length):
    return (value or '')[:max_length]


ORDER_RATE_LIMIT_WINDOW_SECONDS = 300
ORDER_RATE_LIMIT_MAX_REQUESTS = 10


def _is_order_rate_limited(request, token):
    """Simple per-IP-per-restaurant throttle: the qr_code_token isn't secret,
    so anyone who scans it could otherwise script unlimited fake orders."""
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    cache_key = f'order_rate_limit:{token}:{client_ip}'
    count = cache.get(cache_key, 0)
    if count >= ORDER_RATE_LIMIT_MAX_REQUESTS:
        return True
    cache.set(cache_key, count + 1, ORDER_RATE_LIMIT_WINDOW_SECONDS)
    return False


def notify_new_order(order):
    """Best-effort alerts to the restaurant on a new order: email to the owner,
    plus a push notification to every staff device (mobile app). Neither ever
    blocks order creation."""
    recipient = order.restaurant.email or order.restaurant.user.email
    if recipient:
        try:
            send_mail(
                subject=f'New order #{order.order_number} - {order.restaurant.name}',
                message=(
                    f'New order from {order.get_table_type_display().lower()} {order.table_number or "-"}.\n'
                    f'Total: {order.total}\n'
                    f'See the details on your dashboard.'
                ),
                from_email=None,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception:
            logger.exception('Failed to send new-order notification email for order %s', order.order_number)

    try:
        from api.push import notify_staff_new_order
        notify_staff_new_order(order)
    except Exception:
        logger.exception('Failed to send new-order push notification for order %s', order.order_number)


def _apply_order_status_change(order, new_status, changed_by):
    """Moves an order to new_status, logs it, and - the first time an order is
    confirmed - awards loyalty points. Returns the loyalty points total, or None
    if no points were awarded on this call."""
    old_status = order.status
    order.status = new_status
    if new_status in ['delivered', 'cancelled']:
        order.completed_at = timezone.now()

    loyalty_points = None
    if new_status == 'confirmed' and not order.loyalty_points_awarded and order.customer_phone and order.restaurant.loyalty_enabled:
        points_earned = int(order.total)
        account, _created = LoyaltyAccount.objects.get_or_create(restaurant=order.restaurant, phone=order.customer_phone)
        LoyaltyAccount.objects.filter(pk=account.pk).update(points=F('points') + points_earned)
        account.refresh_from_db(fields=['points'])
        loyalty_points = account.points
        order.loyalty_points_awarded = True

    order.save()
    OrderStatusLog.objects.create(
        order=order, changed_by=changed_by, old_status=old_status, new_status=new_status,
    )
    return loyalty_points

@restaurant_role_required('employee')
def order_list(request):
    """List all orders - any staff role (owner/admin/employee) can view and manage orders"""
    restaurant = request.restaurant
    orders = Order.objects.filter(restaurant=restaurant)
    
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    page_obj = Paginator(orders, 20).get_page(request.GET.get('page'))

    context = {
        'orders': page_obj,
        'page_obj': page_obj,
        'restaurant': restaurant,
        'status_choices': Order.ORDER_STATUS,
        'current_status': status_filter,
    }
    return render(request, 'orders/order_list.html', context)

@restaurant_role_required('employee')
def order_detail(request, pk):
    """View order details - any staff role can view and update status"""
    restaurant = request.restaurant
    order = get_object_or_404(Order, pk=pk, restaurant=restaurant)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.ORDER_STATUS) and new_status != order.status:
            loyalty_points = _apply_order_status_change(order, new_status, request.user)
            if loyalty_points is not None:
                messages.success(request, _('Η κατάσταση παραγγελίας ενημερώθηκε! Ο πελάτης κέρδισε πόντους loyalty (σύνολο: %(points)s).') % {'points': loyalty_points})
            else:
                messages.success(request, _('Η κατάσταση παραγγελίας ενημερώθηκε!'))
            return redirect('order_detail', pk=order.pk)

    context = {
        'order': order,
        'restaurant': restaurant,
        'status_choices': Order.ORDER_STATUS,
        'status_logs': order.status_logs.select_related('changed_by')[:20],
    }
    return render(request, 'orders/order_detail.html', context)

@restaurant_role_required('admin')
@require_http_methods(["POST"])
def order_delete(request, pk):
    """Delete an order - restricted to admin/owner, not employees."""
    order = get_object_or_404(Order, pk=pk, restaurant=request.restaurant)
    order.delete()
    messages.success(request, _('Η παραγγελία διαγράφηκε.'))
    return redirect('order_list')

def validate_promo_code(request, token):
    """Public endpoint the checkout modal calls to preview a discount before submitting."""
    if request.method != 'POST':
        return JsonResponse({'valid': False, 'error': 'Method not allowed'}, status=405)

    restaurant = get_object_or_404(Restaurant, qr_code_token=token, is_active=True)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'error': 'Invalid JSON'}, status=400)

    code = _truncate(data.get('code', ''), 30).upper().strip()
    if not code:
        return JsonResponse({'valid': False, 'error': 'Missing code'}, status=400)

    promo = PromoCode.objects.filter(restaurant=restaurant, code=code).first()
    if not promo or not promo.is_valid_now():
        return JsonResponse({'valid': False, 'error': 'Invalid or expired code'}, status=404)

    return JsonResponse({'valid': True, 'code': promo.code, 'discount_percent': promo.discount_percent})

def create_order_api(request, token):
    """API endpoint for creating orders from public menu"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    restaurant = get_object_or_404(Restaurant, qr_code_token=token, is_active=True)

    if not (restaurant.allow_ordering and restaurant.user.has_ordering()):
        return JsonResponse({'success': False, 'error': 'Ordering is not available for this restaurant'}, status=403)

    if _is_order_rate_limited(request, token):
        return JsonResponse({'success': False, 'error': 'Too many requests, please try again shortly'}, status=429)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    items_data = data.get('items', [])
    if not items_data:
        return JsonResponse({'success': False, 'error': 'No items in order'}, status=400)

    # Ordering is only allowed from a table's/sunbed's own QR code - the main restaurant QR is view-only.
    # Re-validate server-side too, so a scripted request can't bypass the UI gating.
    table_number = _truncate(data.get('table_number', ''), 10).strip()
    table_type = data.get('table_type') or 'table'
    if table_type not in dict(RestaurantTable.TABLE_TYPE_CHOICES):
        table_type = 'table'
    if not table_number or not RestaurantTable.objects.filter(
        restaurant=restaurant, number=table_number, table_type=table_type,
    ).exists():
        return JsonResponse({'success': False, 'error': 'Invalid or missing table'}, status=403)

    try:
        with transaction.atomic():
            order = Order.objects.create(
                restaurant=restaurant,
                table_number=table_number,
                table_type=table_type,
                customer_name=_truncate(data.get('customer_name', ''), 100),
                customer_email=_truncate(data.get('customer_email', ''), 254),
                customer_phone=_truncate(data.get('customer_phone', ''), 20),
                customer_notes=_truncate(data.get('notes', ''), 1000),
            )

            items_snapshot = []
            subtotal = Decimal('0')

            for item_data in items_data:
                quantity = int(item_data.get('quantity', 1))
                if not (1 <= quantity <= 100):
                    raise ValueError('Invalid quantity')

                try:
                    # Only products belonging to this restaurant can be ordered.
                    product = Product.objects.get(pk=item_data['product_id'], category__restaurant=restaurant)
                except Product.DoesNotExist:
                    raise ValueError('Invalid product in order')

                option_ids = item_data.get('options', [])
                options = list(ProductOption.objects.filter(pk__in=option_ids, product=product))
                if len(options) != len(set(option_ids)):
                    raise ValueError('Invalid product option')

                # Prices are always recomputed server-side; client-supplied prices are ignored.
                unit_price = product.price + sum((o.price_adjustment for o in options), Decimal('0'))
                line_total = unit_price * quantity
                subtotal += line_total

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    name=product.get_display_name(),
                    price=unit_price,
                    quantity=quantity,
                    options=[{'id': o.id, 'name': o.name, 'price_adjustment': str(o.price_adjustment)} for o in options],
                    notes=_truncate(item_data.get('notes', ''), 1000),
                )
                items_snapshot.append({
                    'product_id': product.id,
                    'name': product.get_display_name(),
                    'price': str(unit_price),
                    'quantity': quantity,
                })

            promo = None
            promo_code_input = _truncate(data.get('promo_code', ''), 30).upper().strip()
            if promo_code_input:
                promo = PromoCode.objects.filter(restaurant=restaurant, code=promo_code_input).first()
                if not promo or not promo.is_valid_now():
                    raise ValueError('Invalid promo code')

            discount = Decimal('0')
            if promo:
                discount = (subtotal * (Decimal(promo.discount_percent) / 100)).quantize(Decimal('0.01'))

            discounted_subtotal = subtotal - discount
            tax = (discounted_subtotal * (restaurant.tax_rate / 100)).quantize(Decimal('0.01'))
            total = (discounted_subtotal + tax).quantize(Decimal('0.01'))
            order.items = items_snapshot
            order.subtotal = subtotal.quantize(Decimal('0.01'))
            order.discount = discount
            order.promo_code = promo.code if promo else ''
            order.tax = tax
            order.total = total
            order.save(update_fields=['items', 'subtotal', 'discount', 'promo_code', 'tax', 'total'])

            if promo:
                PromoCode.objects.filter(pk=promo.pk).update(used_count=F('used_count') + 1)
    except (KeyError, ValueError, TypeError, DatabaseError):
        return JsonResponse({'success': False, 'error': 'Invalid order data'}, status=400)

    notify_new_order(order)

    return JsonResponse({
        'success': True,
        'order_id': order.id,
        'order_number': order.order_number,
        'total': str(order.total),
    })

@restaurant_role_required('employee')
def pending_orders_count(request):
    """Lightweight JSON endpoint polled by the navbar badge."""
    count = Order.objects.filter(restaurant=request.restaurant, status='pending').count()
    return JsonResponse({'pending_count': count})

@restaurant_role_required('employee')
@require_http_methods(["POST"])
def update_order_status(request, pk):
    """Update order status via AJAX - any staff role"""
    order = get_object_or_404(Order, pk=pk, restaurant=request.restaurant)

    data = json.loads(request.body)
    new_status = data.get('status')

    if new_status in dict(Order.ORDER_STATUS) and new_status != order.status:
        loyalty_points = _apply_order_status_change(order, new_status, request.user)
        return JsonResponse({'success': True, 'status': order.get_status_display(), 'loyalty_points': loyalty_points})

    return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

@restaurant_role_required('admin')
def export_orders_csv(request):
    """Business-tier report: CSV export of all orders for the restaurant."""
    restaurant = request.restaurant
    if not restaurant.user.has_stats_dashboard():
        messages.error(request, _('Οι αναφορές CSV είναι διαθέσιμες μόνο στο πλάνο Business.'))
        return redirect('stats_dashboard')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="orders_{restaurant.slug}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Order Number', 'Date', 'Customer', 'Table/Sunbed', 'Status',
        'Subtotal', 'Discount', 'Promo Code', 'Tax', 'Total',
    ])

    orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at')
    for order in orders:
        writer.writerow([
            order.order_number,
            order.created_at.strftime('%d/%m/%Y %H:%M'),
            order.customer_name,
            f"{order.get_table_type_display()} {order.table_number}" if order.table_number else '',
            order.get_status_display(),
            order.subtotal,
            order.discount,
            order.promo_code,
            order.tax,
            order.total,
        ])

    return response