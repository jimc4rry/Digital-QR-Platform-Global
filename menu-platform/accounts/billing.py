"""Paddle Billing integration helpers for subscription billing.

Kept separate from views.py so the Checkout/webhook views stay thin: every
place that needs to talk to Paddle or translate a Paddle object into our
User/Payment fields lives here, in one place, callable from both the
post-checkout confirmation (for a snappy UI) and the webhook (the durable
source of truth) without the two ever disagreeing.

Paddle's flow differs from a Stripe-style redirect-to-hosted-page: checkout
happens client-side via Paddle.js (an embedded/overlay widget), so there's no
server-created "checkout session" to redirect to - this module only needs to
resolve a plan to a Paddle Price id for the client, then react to whatever
Paddle reports afterwards via webhook.
"""
import hashlib
import hmac
import ipaddress
import logging
from decimal import Decimal

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _

from .models import User, Payment

logger = logging.getLogger(__name__)

PLAN_PRICE_IDS = {
    'basic': lambda: settings.PADDLE_PRICE_BASIC,
    'pro': lambda: settings.PADDLE_PRICE_PRO,
    'business': lambda: settings.PADDLE_PRICE_BUSINESS,
}

API_BASES = {
    'sandbox': 'https://sandbox-api.paddle.com',
    'production': 'https://api.paddle.com',
}


def _api_base():
    return API_BASES.get(settings.PADDLE_ENV, API_BASES['sandbox'])


def _headers():
    return {
        'Authorization': f'Bearer {settings.PADDLE_API_KEY}',
        'Content-Type': 'application/json',
    }


def price_id_to_plan(price_id):
    mapping = {
        settings.PADDLE_PRICE_BASIC: 'basic',
        settings.PADDLE_PRICE_PRO: 'pro',
        settings.PADDLE_PRICE_BUSINESS: 'business',
    }
    return mapping.get(price_id)


def price_for_plan(plan):
    """Resolves a plan code to a Paddle Price id, for the client-side
    Checkout overlay (Paddle.Checkout.open) to open."""
    price_id = PLAN_PRICE_IDS[plan]() if plan in PLAN_PRICE_IDS else None
    if not price_id:
        raise ValueError(f'No Paddle price configured for plan "{plan}" - run manage.py sync_paddle_plans.')
    return price_id


def get_or_create_customer(user):
    """Every user gets at most one Paddle Customer, created lazily on first
    checkout and reused for every later checkout/portal lookup."""
    if user.paddle_customer_id:
        return user.paddle_customer_id
    response = requests.post(
        f'{_api_base()}/customers',
        headers=_headers(),
        json={
            'email': user.email or f'{user.username}@example.invalid',
            'name': user.business_name or user.username,
            'custom_data': {'user_id': str(user.id)},
        },
        timeout=10,
    )
    response.raise_for_status()
    customer_id = response.json()['data']['id']
    user.paddle_customer_id = customer_id
    user.save(update_fields=['paddle_customer_id'])
    return customer_id


def get_subscription(subscription_id):
    response = requests.get(f'{_api_base()}/subscriptions/{subscription_id}', headers=_headers(), timeout=10)
    response.raise_for_status()
    return response.json()['data']


def get_transaction(transaction_id):
    response = requests.get(f'{_api_base()}/transactions/{transaction_id}', headers=_headers(), timeout=10)
    response.raise_for_status()
    return response.json()['data']


def management_urls(user):
    """Paddle's self-serve update-payment-method/cancel links - Paddle returns
    these live on the subscription object itself, no separate "portal
    session" call like Stripe's billing_portal.Session.create()."""
    if not user.paddle_subscription_id:
        return None
    try:
        subscription = get_subscription(user.paddle_subscription_id)
    except requests.RequestException:
        return None
    return subscription.get('management_urls')


def user_from_customer_id(customer_id):
    if not customer_id:
        return None
    return User.objects.filter(paddle_customer_id=customer_id).first()


def sync_subscription(user, subscription):
    """Applies a Paddle subscription object onto our local plan/status fields.
    Idempotent - safe to call from both a client-side confirmation and the
    webhook for the same event without double-applying anything odd."""
    items = subscription.get('items') or []
    price_id = items[0]['price']['id'] if items and items[0].get('price') else None
    plan = price_id_to_plan(price_id)
    status = subscription.get('status')

    user.paddle_subscription_id = subscription.get('id') or user.paddle_subscription_id
    if status in ('active', 'trialing'):
        if plan:
            user.subscription_plan = plan
        user.subscription_active = True
    elif status in ('canceled', 'paused', 'past_due'):
        user.subscription_active = False
        if status == 'canceled':
            user.subscription_plan = 'basic'

    period = subscription.get('current_billing_period') or {}
    ends_at = period.get('ends_at')
    if ends_at:
        user.subscription_ends = parse_datetime(ends_at)

    user.save(update_fields=['paddle_subscription_id', 'subscription_plan', 'subscription_active', 'subscription_ends'])
    return user


def record_payment_from_transaction(transaction, failed=False):
    """Logs one Payment row per Paddle transaction - transaction_id is the
    Paddle transaction id, so re-delivered webhook events update the same row via
    update_or_create instead of creating duplicate rows. Uses update (not
    get_or_create) because a transaction can legitimately go through a
    payment_failed event before a later retry succeeds - freezing on whichever
    event arrives first would leave the row permanently wrong."""
    user = user_from_customer_id(transaction.get('customer_id'))
    if not user:
        return None

    items = transaction.get('items') or []
    price_id = items[0]['price']['id'] if items and items[0].get('price') else None
    plan = price_id_to_plan(price_id) or user.subscription_plan

    totals = (transaction.get('details') or {}).get('totals') or {}
    # Paddle amounts are strings in the lowest currency denomination (e.g. cents).
    amount = Decimal(totals.get('grand_total', totals.get('total', '0'))) / 100
    currency = totals.get('currency_code') or transaction.get('currency_code') or 'USD'

    payment, _created = Payment.objects.update_or_create(
        transaction_id=transaction['id'],
        defaults={
            'user': user,
            'plan': plan,
            'amount': amount,
            'currency': currency,
            'status': 'failed' if failed else 'completed',
            'failure_reason': _('The payment for this transaction failed.') if failed else '',
        },
    )
    return payment


def verify_webhook_signature(raw_body, signature_header):
    """Verifies the `Paddle-Signature` header (`ts=...;h1=...`) against
    PADDLE_WEBHOOK_SECRET - HMAC-SHA256 over "{ts}:{raw_body}", compared with
    a timing-safe equality check."""
    if not signature_header or not settings.PADDLE_WEBHOOK_SECRET:
        return False
    parts = dict(part.split('=', 1) for part in signature_header.split(';') if '=' in part)
    ts, h1 = parts.get('ts'), parts.get('h1')
    if not ts or not h1:
        return False
    signed_payload = f'{ts}:{raw_body.decode("utf-8")}'
    expected = hmac.new(settings.PADDLE_WEBHOOK_SECRET.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, h1)


PADDLE_IPS_CACHE_KEY = 'paddle_webhook_ip_ranges'
PADDLE_IPS_CACHE_TTL = 60 * 60 * 6  # 6 hours - these change rarely, per Paddle


def _paddle_webhook_ip_ranges():
    """Fetches and caches Paddle's current webhook-sending IPv4 ranges from their own
    /ips endpoint (never hardcoded - Paddle documents this list can change). Returns
    None on any failure so the caller can treat "unknown" differently from "mismatch"."""
    cached = cache.get(PADDLE_IPS_CACHE_KEY)
    if cached is not None:
        return cached
    try:
        response = requests.get('https://api.paddle.com/ips', timeout=5)
        response.raise_for_status()
        networks = [ipaddress.ip_network(cidr) for cidr in response.json()['data']['ipv4_cidrs']]
    except Exception:
        logger.exception('Could not fetch Paddle webhook IP ranges')
        return None
    cache.set(PADDLE_IPS_CACHE_KEY, networks, PADDLE_IPS_CACHE_TTL)
    return networks


def is_known_paddle_webhook_ip(remote_addr):
    """Checks remote_addr against Paddle's published webhook IP ranges - logging only,
    not enforced. This deployment sits behind Railway's proxy and REMOTE_ADDR has not
    been confirmed to reflect the real caller (vs. the proxy's own address), so a
    mismatch here is a signal to investigate, not proof the request is forged. The
    HMAC signature in verify_webhook_signature() is the actual authentication - do not
    reject webhook requests based on this check without first confirming REMOTE_ADDR
    is trustworthy on this deployment (see the log line this produces)."""
    networks = _paddle_webhook_ip_ranges()
    if networks is None:
        return None  # couldn't fetch the list - unknown, not a mismatch
    try:
        ip = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    return any(ip in network for network in networks)
