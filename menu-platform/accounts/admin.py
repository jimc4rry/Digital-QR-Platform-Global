from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Payment

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'business_name', 'business_type', 'subscription_plan', 'subscription_active')
    list_filter = ('business_type', 'subscription_plan', 'subscription_active')
    search_fields = ('username', 'email', 'business_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Business Info', {
            'fields': ('phone', 'business_name', 'business_type', 'tax_id',
                      'subscription_plan', 'subscription_active', 'subscription_ends')
        }),
    )

admin.site.register(User, CustomUserAdmin)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'plan', 'amount', 'status', 'created_at')
    list_filter = ('status', 'plan')
    search_fields = ('transaction_id', 'user__username')