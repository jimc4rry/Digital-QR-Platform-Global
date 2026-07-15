import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

PLAN_PRICES = {'basic': 7, 'pro': 19, 'business': 39}

BUSINESS_TYPE_CHOICES = [
    ('restaurant', _('Restaurant')),
    ('cafe', _('Cafe')),
    ('bar', _('Bar')),
    ('beach_bar', _('Beach Bar')),
    ('other', _('Other')),
]


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    business_name = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(
        max_length=32, blank=True,
        help_text=_('Optional - VAT/Tax ID, if your business has one.'),
    )
    business_type = models.CharField(
        max_length=50,
        choices=BUSINESS_TYPE_CHOICES,
        default='restaurant'
    )
    subscription_plan = models.CharField(
        max_length=20,
        choices=[
            (plan, f'{plan.capitalize()} - ${price}/month')
            for plan, price in PLAN_PRICES.items()
        ],
        default='basic'
    )
    subscription_active = models.BooleanField(default=True)
    subscription_ends = models.DateTimeField(null=True, blank=True)
    paddle_customer_id = models.CharField(max_length=255, blank=True)
    paddle_subscription_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

    def has_active_subscription(self):
        """True if this account currently has paid (or trial) access. Checked
        live at request time rather than via a cron job flipping a flag, so a
        lapsed subscription_ends date blocks access immediately - no
        background task needed to "notice" a trial or paid period ended.

        During BETA_MODE (billing not live yet - e.g. waiting on Paddle
        production approval) every account is treated as fully subscribed, so
        beta users never get locked out over trial/plan status."""
        if settings.BETA_MODE:
            return True
        if not self.subscription_active:
            return False
        if self.subscription_ends and self.subscription_ends < timezone.now():
            return False
        return True

    def has_ordering(self):
        if settings.BETA_MODE:
            return True
        return self.subscription_plan in ('pro', 'business') and self.has_active_subscription()

    def has_stats_dashboard(self):
        if settings.BETA_MODE:
            return True
        return self.subscription_plan == 'business' and self.has_active_subscription()

    def has_staff_management(self):
        if settings.BETA_MODE:
            return True
        return self.subscription_plan == 'business' and self.has_active_subscription()


class Payment(models.Model):
    """One Paddle transaction for a subscription payment - created from the
    `transaction.completed` / `transaction.payment_failed` webhook events, so
    this is a log of what Paddle actually charged, not something the app
    decides on its own."""
    STATUS_CHOICES = [
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    plan = models.CharField(max_length=20, choices=User._meta.get_field('subscription_plan').choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    transaction_id = models.CharField(max_length=40, unique=True, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    failure_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.plan} - {self.amount} {self.currency} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            # Should only happen if a Payment is ever created outside the Paddle
            # webhook flow - falls back to a random id rather than violating the
            # unique constraint.
            self.transaction_id = f"MANUAL-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)
