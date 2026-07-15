from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DeviceToken(models.Model):
    """A push-notification token registered by the Flutter app for one user's
    device. A user can have multiple tokens (multiple devices)."""
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.platform} - {self.token[:12]}..."
