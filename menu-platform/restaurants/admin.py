from django.contrib import admin
from .models import Restaurant, Category, Product, ProductOption, StaffMember, PromoCode, LoyaltyAccount, RestaurantTable

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'allow_ordering', 'created_at']
    list_filter = ['is_active', 'allow_ordering']
    search_fields = ['name', 'user__username']
    readonly_fields = ['qr_code', 'qr_code_token']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'is_active', 'order']
    list_filter = ['restaurant', 'is_active']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_en', 'category', 'price', 'is_available', 'is_featured']
    list_filter = ['category__restaurant', 'category', 'is_available', 'is_vegan']
    search_fields = ['name', 'name_en', 'description']

@admin.register(ProductOption)
class ProductOptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'price_adjustment', 'is_default']

@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'restaurant', 'role', 'created_at']
    list_filter = ['role', 'restaurant']
    search_fields = ['user__username', 'restaurant__name']

@admin.register(RestaurantTable)
class RestaurantTableAdmin(admin.ModelAdmin):
    list_display = ['number', 'table_type', 'restaurant', 'created_at']
    list_filter = ['table_type', 'restaurant']
    search_fields = ['number', 'restaurant__name']

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'restaurant', 'discount_percent', 'is_active', 'used_count', 'max_uses']
    list_filter = ['is_active', 'restaurant']
    search_fields = ['code']

@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = ['phone', 'restaurant', 'points', 'updated_at']
    list_filter = ['restaurant']
    search_fields = ['phone']