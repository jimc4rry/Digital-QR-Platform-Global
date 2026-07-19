from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.decorators.cache import never_cache
from . import views

urlpatterns = [
    path('signup/', never_cache(views.signup), name='signup'),
    # never_cache is required here: this page embeds a one-time CSRF token tied to
    # the session's csrftoken cookie, so a cached copy (browser or CDN/proxy) served
    # on a later visit carries a stale token that no longer matches the current
    # cookie - the login POST then fails CSRF verification even though nothing is
    # actually wrong with the account or credentials.
    path('login/', never_cache(auth_views.LoginView.as_view(template_name='accounts/login.html')), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('post-login/', views.post_login_redirect, name='post_login_redirect'),
    path('password-change/', views.password_change, name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html',
    ), name='password_change_done'),
    path('checkout/', views.checkout, name='checkout'),
    path('payments/success/', views.payment_success, name='payment_success'),
    path('payments/', views.payment_history, name='payment_history'),
    path('billing-portal/', views.billing_portal, name='billing_portal'),
    path('webhooks/paddle/', views.paddle_webhook, name='paddle_webhook'),
    path('platform-admin/', views.platform_admin_dashboard, name='platform_admin_dashboard'),
    path('platform-admin/payments/', views.platform_admin_payments, name='platform_admin_payments'),
    path('platform-admin/<int:pk>/', views.platform_admin_business_detail, name='platform_admin_business_detail'),
    path('platform-admin/<int:pk>/delete/', views.platform_admin_business_delete, name='platform_admin_business_delete'),
]
