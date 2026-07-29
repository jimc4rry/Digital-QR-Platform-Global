import logging
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageDraw, ImageFont
import qrcode
from io import BytesIO
from django.core.files import File
import uuid
import os
from .utils import validate_image_file_size, generate_unique_slug

logger = logging.getLogger(__name__)

# Same DejaVu Sans used by the PDF menu export (restaurants/menu_pdf.py) -
# PIL's default font has no Greek/accented glyphs, which would silently
# corrupt a restaurant name printed on a table QR card.
_FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
_QR_CARD_PRIMARY = (99, 102, 241)   # #6366f1
_QR_CARD_TEXT = (31, 41, 55)        # #1f2937
_QR_CARD_MUTED = (107, 114, 128)    # #6b7280


def _fit_font(measurer, text, max_width, bold, max_size, min_size=16):
    """Largest font size (within [min_size, max_size]) that keeps `text` no
    wider than max_width. Falls back to min_size (letting long text run to
    the edge) rather than shrinking indefinitely - a card's name should
    stay readable even if it doesn't fully avoid a tight fit."""
    weight = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    path = os.path.join(_FONTS_DIR, weight)
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(path, size)
        left, top, right, bottom = measurer.textbbox((0, 0), text, font=font)
        if right - left <= max_width:
            return font
    return ImageFont.truetype(path, min_size)


def _build_table_qr_card(qr_img, restaurant_name, label_text):
    """Composites a bare QR code into a printable card: restaurant name and
    a short tagline above it, the location's label (e.g. "Table 1") below
    it in a colored badge - so a downloaded/printed QR always says what
    table it's for, not just a scannable square."""
    measurer = ImageDraw.Draw(Image.new('RGB', (10, 10)))

    def text_size(text, font):
        left, top, right, bottom = measurer.textbbox((0, 0), text, font=font)
        return right - left, bottom - top

    padding_x = 50
    qr_width, qr_height = qr_img.size
    canvas_width = max(qr_width, 420) + padding_x * 2
    max_text_width = canvas_width - padding_x * 2

    # Long restaurant names would otherwise overflow the card - shrink the
    # font to fit instead of letting it run off both edges.
    name_font = _fit_font(measurer, restaurant_name, max_text_width, bold=True, max_size=32)
    tagline_font = ImageFont.truetype(os.path.join(_FONTS_DIR, 'DejaVuSans.ttf'), 18)
    label_font = ImageFont.truetype(os.path.join(_FONTS_DIR, 'DejaVuSans-Bold.ttf'), 28)
    tagline_text = str(_('Scan to view the menu'))

    name_w, name_h = text_size(restaurant_name, name_font)
    tagline_w, tagline_h = text_size(tagline_text, tagline_font)
    label_w, label_h = text_size(label_text, label_font)

    top_margin, gap_small, gap_medium, bottom_margin = 40, 8, 24, 36
    badge_pad_x, badge_pad_y = 28, 14

    canvas_height = (
        top_margin + name_h + gap_small + tagline_h + gap_medium
        + qr_height + gap_medium
        + label_h + badge_pad_y * 2 + bottom_margin
    )

    card = Image.new('RGB', (canvas_width, canvas_height), 'white')
    draw = ImageDraw.Draw(card)

    y = top_margin
    draw.text(((canvas_width - name_w) / 2, y), restaurant_name, font=name_font, fill=_QR_CARD_TEXT)
    y += name_h + gap_small
    draw.text(((canvas_width - tagline_w) / 2, y), tagline_text, font=tagline_font, fill=_QR_CARD_MUTED)
    y += tagline_h + gap_medium

    card.paste(qr_img, ((canvas_width - qr_width) // 2, y))
    y += qr_height + gap_medium

    badge_w, badge_h = label_w + badge_pad_x * 2, label_h + badge_pad_y * 2
    badge_x = (canvas_width - badge_w) // 2
    draw.rounded_rectangle([badge_x, y, badge_x + badge_w, y + badge_h], radius=badge_h // 2, fill=_QR_CARD_PRIMARY)
    draw.text((badge_x + badge_pad_x, y + badge_pad_y), label_text, font=label_font, fill='white')

    return card


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
    currency = models.CharField(max_length=3, default='USD')
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name

    def get_subdomain_url(self):
        """The restaurant's own branded menu address, e.g. https://my-cafe.getmenuhub.com/ -
        served by menu_platform.middleware.RestaurantSubdomainMiddleware."""
        from urllib.parse import urlparse
        parsed = urlparse(settings.SITE_URL)
        return f'{parsed.scheme}://{self.slug}.{parsed.netloc}/'

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
    name_en = models.CharField(max_length=200, blank=True, help_text=_('English name (optional) - if left blank, the name above is shown'))
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
    preparation_time = models.PositiveIntegerField(help_text=_('Preparation time in minutes'), default=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ['category', 'slug']
        indexes = [
            models.Index(fields=['category', 'is_available']),
        ]
        
    def __str__(self):
        return f"{self.name} - {self.price}"

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

    def get_option_groups(self):
        """Options bucketed by group_name, for the public menu.
        Options that share a non-blank group_name are mutually exclusive
        (radio buttons); each such group gets exactly one 'checked' option
        (its is_default option, or the first one if none is marked default).
        Options with a blank group_name are independent add-ons (checkboxes)
        and keep their own is_default as their checked state."""
        from itertools import groupby
        groups = []
        for group_name, opts_iter in groupby(self.options.all(), key=lambda o: o.group_name):
            opts = list(opts_iter)
            if group_name:
                has_default = any(o.is_default for o in opts)
                for i, o in enumerate(opts):
                    o.checked = o.is_default or (not has_default and i == 0)
            else:
                for o in opts:
                    o.checked = o.is_default
            groups.append({'name': group_name, 'options': opts})
        return groups

    def optimize_image(self):
        try:
            img = Image.open(self.image.path)
            if img.width > 800 or img.height > 800:
                img.thumbnail((800, 800))
                img.save(self.image.path, quality=85, optimize=True)
        except Exception:
            logger.exception("Failed to optimize image for product %s", self.pk)

class RestaurantTable(models.Model):
    TABLE_TYPE_CHOICES = [
        ('table', _('Table')),
        ('sunbed', _('Sunbed')),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_type = models.CharField(max_length=10, choices=TABLE_TYPE_CHOICES, default='table')
    number = models.CharField(max_length=20, help_text=_('e.g. 1, 2, Patio A'))
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
        """Populate self.qr_code with a freshly generated image: the QR
        code plus the restaurant name and this location's label (e.g.
        "Table 1"), laid out as a printable card - not just a bare QR
        square with no indication of which table it belongs to. Does not
        save the model."""
        url = f"{settings.SITE_URL}/menu/{self.restaurant.qr_code_token}/table/{self.pk}/"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white").get_image().convert('RGB')
        label_text = f'{self.get_table_type_display()} {self.number}'
        card = _build_table_qr_card(qr_img, self.restaurant.name, label_text)

        buffer = BytesIO()
        card.save(buffer, 'PNG')

        filename = f"qr_table_{self.restaurant.slug}_{self.pk}.png"
        self.qr_code.save(filename, File(buffer), save=False)

class ProductOption(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='options')
    # Options sharing the same non-blank group_name are mutually exclusive
    # (rendered as a radio group on the menu, e.g. "Sweetness: Plain / Medium /
    # Sweet"). Options with a blank group_name are independent add-ons
    # (rendered as checkboxes, e.g. "Extra cheese +$1").
    group_name = models.CharField(max_length=100, blank=True, help_text=_(
        'Optional. Give two or more options the same group name to make them mutually '
        'exclusive (e.g. group "Sweetness" with options "Plain", "Medium", "Sweet"). '
        'Leave blank for an independent add-on.'
    ))
    name = models.CharField(max_length=100)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['group_name', 'id']

    def __str__(self):
        return f"{self.product.name} - {self.name}"

class StaffMember(models.Model):
    ROLE_CHOICES = [
        ('admin', _('Admin')),
        ('employee', _('Employee')),
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
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text=_('Leave blank for unlimited uses'))
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