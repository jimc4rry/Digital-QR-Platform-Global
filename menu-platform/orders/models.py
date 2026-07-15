from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from restaurants.models import Restaurant, Product, RestaurantTable
import uuid

class Order(models.Model):
    ORDER_STATUS = [
        ('pending', _('Εκκρεμεί')),
        ('confirmed', _('Επιβεβαιωμένη')),
        ('preparing', _('Παρασκευάζεται')),
        ('ready', _('Έτοιμη')),
        ('delivered', _('Παραδόθηκε')),
        ('cancelled', _('Ακυρώθηκε')),
    ]

    PAYMENT_STATUS = [
        ('pending', _('Εκκρεμεί')),
        ('paid', _('Πληρώθηκε')),
        ('failed', _('Απέτυχε')),
        ('refunded', _('Επιστροφή')),
    ]
    
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    # Both are denormalized snapshots taken at order time (not a FK to
    # RestaurantTable), same as table_number always was - so a table/sunbed
    # being renamed or deleted later never changes historical orders.
    table_type = models.CharField(max_length=10, choices=RestaurantTable.TABLE_TYPE_CHOICES, default='table', blank=True)
    table_number = models.CharField(max_length=10, blank=True)
    customer_name = models.CharField(max_length=100, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_notes = models.TextField(blank=True)
    
    items = models.JSONField(default=list)  # Store items as JSON
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    promo_code = models.CharField(max_length=30, blank=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    payment_id = models.CharField(max_length=200, blank=True)
    loyalty_points_awarded = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['restaurant', '-created_at']),
        ]

    def __str__(self):
        return f"#{self.order_number} - {self.restaurant.name}"
        
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        import random
        import string
        for _ in range(10):
            candidate = ''.join(random.choices(string.digits, k=10))
            if not Order.objects.filter(order_number=candidate).exists():
                return candidate
        raise RuntimeError('Could not generate a unique order number')

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    options = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} x{self.quantity}"

    @property
    def line_total(self):
        return self.price * self.quantity

class OrderStatusLog(models.Model):
    """Audit trail of who changed an order's status and when - lets an owner/admin
    see what each staff member (employee) actually did on their device."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_logs')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    old_status = models.CharField(max_length=20, choices=Order.ORDER_STATUS, blank=True)
    new_status = models.CharField(max_length=20, choices=Order.ORDER_STATUS)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        who = self.changed_by.username if self.changed_by else 'Unknown'
        return f"{who}: {self.old_status} -> {self.new_status}"