from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from PIL import Image
import qrcode
from io import BytesIO
from django.core.files import File
import uuid
import os
from .utils import validate_image_file_size, generate_unique_slug

class Restaurant(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='restaurant')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=500, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to='restaurants/logos/', blank=True, null=True, validators=[validate_image_file_size])
    cover_image = models.ImageField(upload_to='restaurants/covers/', blank=True, null=True, validators=[validate_image_file_size])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # QR Code
    qr_code = models.ImageField(upload_to='restaurants/qr_codes/', blank=True, null=True)
    qr_code_token = models.CharField(max_length=100, unique=True, blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    allow_ordering = models.BooleanField(default=False)
    loyalty_enabled = models.BooleanField(default=False)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='€')
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'restaurant'
            slug = base_slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug

        if not self.qr_code_token:
            self.qr_code_token = str(uuid.uuid4()).replace('-', '')[:20]

        needs_qr_code = not self.qr_code
        super().save(*args, **kwargs)

        if needs_qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])

    def generate_qr_code(self):
        """Populate self.qr_code with a freshly generated image. Does not save the model."""
        url = f"{settings.SITE_URL}/menu/{self.qr_code_token}/"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Save to BytesIO
        buffer = BytesIO()
        qr_img.save(buffer, 'PNG')

        # Save to model
        filename = f"qr_{self.slug}_{self.qr_code_token}.png"
        self.qr_code.save(filename, File(buffer), save=False)

class Category(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ['restaurant', 'slug']
        indexes = [
            models.Index(fields=['restaurant', 'is_active']),
        ]
        
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name, Category.objects.filter(restaurant=self.restaurant))
        super().save(*args, **kwargs)

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True, help_text=_('Αγγλική ονομασία (προαιρετικό) - αν μείνει κενό εμφανίζεται η ελληνική'))
    slug = models.SlugField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='restaurants/products/', blank=True, null=True, validators=[validate_image_file_size])
    
    # Options
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    is_spicy = models.BooleanField(default=False)
    
    order = models.PositiveIntegerField(default=0)
    preparation_time = models.PositiveIntegerField(help_text=_('Χρόνος παρασκευής σε λεπτά'), default=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ['category', 'slug']
        indexes = [
            models.Index(fields=['category', 'is_available']),
        ]
        
    def __str__(self):
        return f"{self.name} - {self.price}€"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name, Product.objects.filter(category=self.category))
        super().save(*args, **kwargs)

        # Optimize image
        if self.image and hasattr(self.image, 'path'):
            self.optimize_image()

    def get_display_name(self):
        from django.utils.translation import get_language
        if get_language() == 'en' and self.name_en:
            return self.name_en
        return self.name
    
    def optimize_image(self):
        try:
            img = Image.open(self.image.path)
            if img.width > 800 or img.height > 800:
                img.thumbnail((800, 800))
                img.save(self.image.path, quality=85, optimize=True)
        except Exception:
            pass

class RestaurantTable(models.Model):
    TABLE_TYPE_CHOICES = [
        ('table', _('Τραπέζι')),
        ('sunbed', _('Ξαπλώστρα')),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_type = models.CharField(max_length=10, choices=TABLE_TYPE_CHOICES, default='table')
    number = models.CharField(max_length=20, help_text=_('π.χ. 1, 2, Πάτιο Α'))
    qr_code = models.ImageField(upload_to='restaurants/table_qr_codes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        # A table and a sunbed can share the same number (e.g. both "5") -
        # they're only required to be unique within their own type.
        unique_together = ['restaurant', 'table_type', 'number']

    def __str__(self):
        return f"{self.restaurant.name} - {self.get_table_type_display()} {self.number}"

    def save(self, *args, **kwargs):
        needs_qr_code = not self.qr_code
        super().save(*args, **kwargs)

        if needs_qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])

    def generate_qr_code(self):
        """Populate self.qr_code with a freshly generated image. Does not save the model."""
        url = f"{settings.SITE_URL}/menu/{self.restaurant.qr_code_token}/table/{self.pk}/"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        qr_img.save(buffer, 'PNG')

        filename = f"qr_table_{self.restaurant.slug}_{self.pk}.png"
        self.qr_code.save(filename, File(buffer), save=False)

class ProductOption(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_default = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"

class StaffMember(models.Model):
    ROLE_CHOICES = [
        ('admin', _('Διαχειριστής')),
        ('employee', _('Υπάλληλος')),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='staff_members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()}) - {self.restaurant.name}"

class LoyaltyAccount(models.Model):
    """Tracks loyalty points per customer phone number for a restaurant.
    Customers don't have accounts, so phone number is the natural key."""
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='loyalty_accounts')
    phone = models.CharField(max_length=20)
    points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['restaurant', 'phone']
        ordering = ['-points']

    def __str__(self):
        return f"{self.phone} - {self.points}pts ({self.restaurant.name})"

class PromoCode(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='promo_codes')
    code = models.CharField(max_length=30)
    discount_percent = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text=_('Άφησέ το κενό για απεριόριστες χρήσεις'))
    used_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['restaurant', 'code']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} (-{self.discount_percent}%) - {self.restaurant.name}"

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def is_valid_now(self):
        if not self.is_active:
            return False
        if self.valid_until and timezone.now() > self.valid_until:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True