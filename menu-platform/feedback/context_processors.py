from .models import Feedback


def feedback_context(request):
    """Unread feedback count for the platform admin nav badge - only queried
    for superusers, so regular page loads pay nothing for this."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_superuser:
        return {}
    return {'unread_feedback_count': Feedback.objects.filter(is_read=False).count()}
