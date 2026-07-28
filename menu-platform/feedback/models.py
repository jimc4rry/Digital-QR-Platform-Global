from django.conf import settings
from django.db import models


class Feedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedback_entries')
    message = models.TextField()
    page_url = models.CharField(max_length=500, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    admin_reply = models.TextField(blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.created_at:%Y-%m-%d %H:%M}'


class Notification(models.Model):
    """In-app notification for a restaurant user (owner or staff) - currently
    only created when the platform admin replies to a Feedback entry, but
    kept generic (not "FeedbackReply") so it can carry other notification
    types later without a model migration."""
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient} - {self.title}'
