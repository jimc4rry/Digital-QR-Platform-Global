from .models import Feedback, Notification


def feedback_context(request):
    """Unread feedback count for the platform admin nav badge - only queried
    for superusers, so regular page loads pay nothing for this."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_superuser:
        return {}
    return {'unread_feedback_count': Feedback.objects.filter(is_read=False).count()}


def notification_context(request):
    """Unread in-app notification count for the restaurant nav badge - not
    queried for superusers, who don't have a restaurant/notifications of
    their own in this context."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or user.is_superuser:
        return {}
    return {'unread_notification_count': Notification.objects.filter(recipient=user, is_read=False).count()}
