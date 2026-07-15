from django.contrib import admin
from .models import Order, OrderItem, OrderStatusLog

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'restaurant', 'status', 'payment_status', 'total', 'created_at']
    list_filter = ['status', 'payment_status', 'restaurant']
    search_fields = ['order_number', 'customer_name', 'customer_email']
    readonly_fields = ['order_number', 'created_at']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'name', 'price', 'quantity']

@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ['order', 'changed_by', 'old_status', 'new_status', 'changed_at']
    list_filter = ['new_status']