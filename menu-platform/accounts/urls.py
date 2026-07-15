from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
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
]
