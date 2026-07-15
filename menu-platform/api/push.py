import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_firebase_app = None
_firebase_init_attempted = False


def _get_firebase_app():
    """Lazily initializes the Firebase Admin SDK. Returns None if no credentials
    are configured - push notifications are then a silent no-op, the same way
    S3 storage falls back to local disk when AWS_STORAGE_BUCKET_NAME is unset."""
    global _firebase_app, _firebase_init_attempted
    if _firebase_app is not None or _firebase_init_attempted:
        return _firebase_app
    _firebase_init_attempted = True

    if not settings.FIREBASE_CREDENTIALS_PATH:
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception('Failed to initialize Firebase - push notifications disabled.')
    return _firebase_app


def send_push_to_user(user, title, body, data=None):
    """Best-effort push to every device this user has registered. Never raises -
    a push failure should never break order creation or a status update."""
    app = _get_firebase_app()
    if app is None:
        return

    from firebase_admin import messaging
    from .models import DeviceToken

    tokens = list(DeviceToken.objects.filter(user=user).values_list('token', flat=True))
    if not tokens:
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=tokens,
    )
    try:
        messaging.send_each_for_multicast(message, app=app)
    except Exception:
        logger.exception('Failed to send push notification to user %s', user.username)


def notify_staff_new_order(order):
    """Push alert to the restaurant owner and every admin/employee - the mobile-app
    counterpart to the existing email notification in orders/views.py."""
    restaurant = order.restaurant
    recipients = [restaurant.user] + [s.user for s in restaurant.staff_members.select_related('user')]
    title = f'New order #{order.order_number}'
    body = f'{order.get_table_type_display()} {order.table_number or "-"} · {order.total}'
    for user in recipients:
        send_push_to_user(user, title, body, data={'order_id': order.id, 'type': 'new_order'})
