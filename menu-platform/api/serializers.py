from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from orders.models import Order, OrderItem, OrderStatusLog
from restaurants.models import Product, Category, StaffMember, Restaurant, LoyaltyAccount, PromoCode
from .models import DeviceToken

User = get_user_model()


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'name', 'price', 'quantity', 'options', 'notes', 'line_total']


class OrderStatusLogSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source='changed_by.username', default=None, read_only=True)
    old_status_display = serializers.CharField(source='get_old_status_display', read_only=True)
    new_status_display = serializers.CharField(source='get_new_status_display', read_only=True)

    class Meta:
        model = OrderStatusLog
        fields = ['id', 'changed_by_username', 'old_status', 'old_status_display',
                  'new_status', 'new_status_display', 'changed_at']


class OrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    table_type_display = serializers.CharField(source='get_table_type_display', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'table_type', 'table_type_display', 'table_number', 'customer_name', 'total',
                  'status', 'status_display', 'created_at']


class OrderDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    table_type_display = serializers.CharField(source='get_table_type_display', read_only=True)
    order_items = OrderItemSerializer(many=True, read_only=True)
    status_logs = OrderStatusLogSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'table_type', 'table_type_display', 'table_number', 'customer_name', 'customer_email',
                  'customer_phone', 'customer_notes', 'subtotal', 'discount', 'promo_code',
                  'tax', 'total', 'status', 'status_display', 'order_items', 'status_logs',
                  'created_at', 'completed_at']


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.ORDER_STATUS)


class ProductSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'category', 'category_name', 'name', 'name_en', 'display_name',
                  'description', 'price', 'old_price', 'image_url', 'is_available',
                  'is_featured', 'is_vegan', 'is_vegetarian', 'is_gluten_free', 'is_spicy',
                  'preparation_time']

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'order', 'is_active']


class StaffMemberSerializer(serializers.ModelSerializer):
    """Mirrors staff_list.html's table - owner-only view of admin/employee accounts."""
    username = serializers.CharField(source='user.username', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = StaffMember
        fields = ['id', 'username', 'role', 'role_display', 'created_at']


class StaffCreateSerializer(serializers.Serializer):
    """Same validation as StaffCreationForm on the web (unique username, Django's
    password validators), minus the confirm-password field - mobile keyboards make
    double entry more error-prone than it's worth."""
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=StaffMember.ROLE_CHOICES)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username already exists.')
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def create(self, validated_data):
        restaurant = self.context['restaurant']
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                password=validated_data['password'],
            )
            staff = StaffMember.objects.create(
                restaurant=restaurant, user=user, role=validated_data['role'],
            )
        return staff


class RestaurantSettingsSerializer(serializers.ModelSerializer):
    """Same editable fields as RestaurantForm on the web, minus logo/cover_image
    (file upload isn't part of this app's scope yet)."""

    class Meta:
        model = Restaurant
        fields = ['name', 'description', 'address', 'phone', 'email',
                  'allow_ordering', 'loyalty_enabled', 'tax_rate']


class LoyaltyAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyAccount
        fields = ['id', 'phone', 'points', 'created_at', 'updated_at']


class LoyaltyPointsUpdateSerializer(serializers.Serializer):
    points = serializers.IntegerField(min_value=0)


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ['id', 'code', 'discount_percent', 'is_active', 'valid_until',
                  'max_uses', 'used_count', 'created_at']
        read_only_fields = ['used_count', 'created_at']


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ['token', 'platform']
        # Re-registering an existing token (reinstall, refresh) is expected and
        # handled by update_or_create below - don't let DRF's auto unique
        # validator reject it before create() ever runs.
        extra_kwargs = {'token': {'validators': []}}

    def create(self, validated_data):
        # A device's token can be re-registered (app reinstall, token refresh) -
        # update the owner rather than erroring on the unique constraint.
        token, _created = DeviceToken.objects.update_or_create(
            token=validated_data['token'],
            defaults={'user': self.context['request'].user, 'platform': validated_data['platform']},
        )
        return token
