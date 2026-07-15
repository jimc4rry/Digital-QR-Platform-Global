import json
from datetime import timedelta
from decimal import Decimal
from functools import wraps

import requests
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Sum, Q
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from . import billing
from .forms import UserRegistrationForm, StyledPasswordChangeForm, PlatformSubscriptionForm, get_purchasable_plans
from .models import User, Payment, PLAN_PRICES
from restaurants.models import Restaurant
from restaurants.permissions import get_restaurant_and_role


@login_required
def password_change(request):
    """Employees don't manage their own credentials - the admin controls the
    account they use on the shared device, so employees can't change it themselves."""
    _restaurant, role = get_restaurant_and_role(request.user)
    if role == 'employee':
        return HttpResponseForbidden(_('You do not have permission to change the password. Contact your store administrator.'))
    return auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        form_class=StyledPasswordChangeForm,
        success_url=reverse_lazy('password_change_done'),
    )(request)


def signup(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                # 30-day free trial of Basic - no payment needed yet, but once
                # subscription_ends passes, has_active_subscription() goes
                # False on its own and the dashboard locks until they check out.
                user.subscription_plan = 'basic'
                user.subscription_active = True
                user.subscription_ends = timezone.now() + timedelta(days=30)
                user.save(update_fields=['subscription_plan', 'subscription_active', 'subscription_ends'])

                # Auto-create the restaurant that goes with this account
                Restaurant.objects.create(
                    user=user,
                    name=user.business_name or f"{user.username}'s Restaurant",
                    is_active=True,
                    allow_ordering=True,
                )

            login(request, user)
            messages.success(request, _('Your account has been created! You have a 30-day free trial of the Basic plan.'))
            return redirect('restaurant_dashboard')
        else:
            messages.error(request, _('There are errors in the form. Please correct them.'))
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@login_required
def checkout(request):
    """Picks a plan and hands off to Paddle's own embedded Checkout overlay -
    card details are entered there, never on our servers."""
    restaurant, role = get_restaurant_and_role(request.user)
    if restaurant is None or role != 'owner':
        return HttpResponseForbidden(_('Only the business owner can manage the subscription.'))

    current_plan = request.user.subscription_plan
    subscription_active = request.user.subscription_active
    available_plans = get_purchasable_plans(current_plan, subscription_active)

    preselected_plan = request.GET.get('plan')
    if preselected_plan not in available_plans:
        preselected_plan = available_plans[0] if available_plans else None

    plan_rows = []
    for plan in available_plans:
        try:
            price_id = billing.price_for_plan(plan)
        except ValueError:
            price_id = None
        plan_rows.append({'code': plan, 'price': PLAN_PRICES[plan], 'price_id': price_id})

    try:
        billing.get_or_create_customer(request.user)
    except requests.RequestException as exc:
        messages.error(request, _('Could not reach Paddle: %(error)s') % {'error': str(exc)})

    context = {
        'plan_rows': plan_rows,
        'current_plan': current_plan,
        'available_plans': available_plans,
        'preselected_plan': preselected_plan,
        'paddle_client_token': settings.PADDLE_CLIENT_TOKEN,
        'paddle_env': settings.PADDLE_ENV,
        'customer_email': request.user.email,
    }
    return render(request, 'accounts/checkout.html', context)


@login_required
def payment_success(request):
    """Our own Paddle.js `checkout.completed` handler sends the browser here
    with the transaction id, right after a completed checkout. We try a quick
    client-triggered sync for a snappy UI - the webhook does the same sync
    independently and is the durable source of truth, so nothing depends on
    the user's browser making it back here."""
    txn_id = request.GET.get('txn_id')
    amount = None
    currency = None

    if txn_id:
        try:
            transaction_obj = billing.get_transaction(txn_id)
        except requests.RequestException:
            transaction_obj = None

        if transaction_obj and transaction_obj.get('customer_id') == request.user.paddle_customer_id:
            totals = (transaction_obj.get('details') or {}).get('totals') or {}
            grand_total = totals.get('grand_total') or totals.get('total')
            if grand_total is not None:
                amount = Decimal(grand_total) / 100
                currency = totals.get('currency_code')

            subscription_id = transaction_obj.get('subscription_id')
            if subscription_id:
                try:
                    subscription = billing.get_subscription(subscription_id)
                    billing.sync_subscription(request.user, subscription)
                except requests.RequestException:
                    pass
            messages.success(request, _('Payment completed! Your plan has been upgraded.'))

    context = {
        'plan_display': dict(User._meta.get_field('subscription_plan').choices).get(request.user.subscription_plan),
        'amount': amount,
        'currency': currency,
        'subscription_ends': request.user.subscription_ends,
    }
    return render(request, 'accounts/payment_success.html', context)


@login_required
def billing_portal(request):
    """Paddle's own hosted customer-portal links for updating a card or
    canceling - no custom UI needed for either."""
    restaurant, role = get_restaurant_and_role(request.user)
    if restaurant is None or role != 'owner':
        return HttpResponseForbidden(_('Only the business owner can manage the subscription.'))

    urls = billing.management_urls(request.user)
    if not urls or not urls.get('update_payment_method'):
        messages.info(request, _('There is no active subscription to manage yet.'))
        return redirect('profile')
    return redirect(urls['update_payment_method'])


@csrf_exempt
@require_POST
def paddle_webhook(request):
    """Paddle calls this directly (no login, no CSRF token) - the signature
    check is what proves a request actually came from Paddle."""
    if not settings.PADDLE_WEBHOOK_SECRET:
        return HttpResponse(status=503)

    signature = request.META.get('HTTP_PADDLE_SIGNATURE', '')
    if not billing.verify_webhook_signature(request.body, signature):
        return HttpResponseBadRequest()

    try:
        event = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest()

    event_type = event.get('event_type')
    obj = event.get('data') or {}

    if event_type in ('subscription.created', 'subscription.updated', 'subscription.activated', 'subscription.trialing'):
        user = billing.user_from_customer_id(obj.get('customer_id'))
        if user:
            billing.sync_subscription(user, obj)

    elif event_type == 'subscription.canceled':
        user = billing.user_from_customer_id(obj.get('customer_id'))
        if user:
            user.subscription_active = False
            user.subscription_plan = 'basic'
            user.save(update_fields=['subscription_active', 'subscription_plan'])

    elif event_type == 'transaction.completed':
        billing.record_payment_from_transaction(obj)

    elif event_type == 'transaction.payment_failed':
        billing.record_payment_from_transaction(obj, failed=True)

    return HttpResponse(status=200)


@login_required
def payment_history(request):
    payments = Payment.objects.filter(user=request.user)
    page_obj = Paginator(payments, 20).get_page(request.GET.get('page'))
    return render(request, 'accounts/payment_history.html', {'payments': page_obj, 'page_obj': page_obj})


@login_required
def post_login_redirect(request):
    """Where to send a user right after login - business owners/staff go to their
    restaurant dashboard, platform admins (no restaurant) go to their own panel."""
    restaurant, _role = get_restaurant_and_role(request.user)
    if restaurant is not None:
        return redirect('restaurant_dashboard')
    if request.user.is_superuser:
        return redirect('platform_admin_dashboard')
    return redirect('profile')


def platform_admin_required(view_func):
    """Restricts a view to Django superusers - this is the SaaS operator's own
    cross-tenant support panel, entirely separate from the per-restaurant
    owner/admin/employee roles."""
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden(_('You do not have access to this page.'))
        return view_func(request, *args, **kwargs)
    return wrapper


@platform_admin_required
def platform_admin_dashboard(request):
    """Cross-tenant list of every business on the platform, for support/billing purposes."""
    businesses = User.objects.filter(restaurant__isnull=False).select_related('restaurant').annotate(
        order_count=Count('restaurant__orders', distinct=True),
        total_revenue=Sum('restaurant__orders__total'),
    ).order_by('-created_at')

    plan_filter = request.GET.get('plan', '').strip()
    if plan_filter:
        businesses = businesses.filter(subscription_plan=plan_filter)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        businesses = businesses.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(business_name__icontains=search_query) |
            Q(restaurant__name__icontains=search_query)
        )

    page_obj = Paginator(businesses, 20).get_page(request.GET.get('page'))

    context = {
        'businesses': page_obj,
        'page_obj': page_obj,
        'plan_filter': plan_filter,
        'search_query': search_query,
        'plan_choices': User._meta.get_field('subscription_plan').choices,
    }
    return render(request, 'accounts/platform_admin_dashboard.html', context)


@platform_admin_required
def platform_admin_business_detail(request, pk):
    """Support view for one business - lets the platform operator record plan
    changes and payment status by hand, for cases outside the normal Paddle flow."""
    business_user = get_object_or_404(User, pk=pk, restaurant__isnull=False)
    restaurant = business_user.restaurant

    if request.method == 'POST':
        form = PlatformSubscriptionForm(request.POST, instance=business_user)
        if form.is_valid():
            form.save()
            messages.success(request, _('The subscription was updated successfully!'))
            return redirect('platform_admin_business_detail', pk=business_user.pk)
    else:
        form = PlatformSubscriptionForm(instance=business_user)

    order_stats = restaurant.orders.aggregate(count=Count('id'), revenue=Sum('total'))

    context = {
        'business_user': business_user,
        'restaurant': restaurant,
        'form': form,
        'order_count': order_stats['count'] or 0,
        'total_revenue': order_stats['revenue'] or 0,
        'staff_count': restaurant.staff_members.count(),
        'payments': Payment.objects.filter(user=business_user)[:20],
    }
    return render(request, 'accounts/platform_admin_business_detail.html', context)


@platform_admin_required
def platform_admin_payments(request):
    """Cross-tenant view of every payment on the platform."""
    payments = Payment.objects.select_related('user', 'user__restaurant')

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        payments = payments.filter(status=status_filter)

    page_obj = Paginator(payments, 30).get_page(request.GET.get('page'))

    total_revenue = Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'total_revenue': total_revenue,
    }
    return render(request, 'accounts/platform_admin_payments.html', context)
