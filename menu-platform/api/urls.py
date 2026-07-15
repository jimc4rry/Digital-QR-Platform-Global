from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path('auth/login/', TokenObtainPairView.as_view(), name='api_login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('me/', views.MeView.as_view(), name='api_me'),

    path('orders/', views.OrderListView.as_view(), name='api_order_list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='api_order_detail'),
    path('orders/<int:pk>/status/', views.OrderStatusUpdateView.as_view(), name='api_order_status_update'),

    path('products/', views.ProductListView.as_view(), name='api_product_list'),
    path('products/<int:pk>/availability/', views.ProductAvailabilityUpdateView.as_view(), name='api_product_availability'),
    path('categories/', views.CategoryListView.as_view(), name='api_category_list'),

    path('device-tokens/', views.DeviceTokenRegisterView.as_view(), name='api_device_token_register'),

    path('stats/', views.StatsView.as_view(), name='api_stats'),

    path('staff/', views.StaffListView.as_view(), name='api_staff_list'),
    path('staff/<int:pk>/', views.StaffDeleteView.as_view(), name='api_staff_delete'),

    path('settings/', views.RestaurantSettingsView.as_view(), name='api_settings'),

    path('loyalty/', views.LoyaltyListView.as_view(), name='api_loyalty_list'),
    path('loyalty/<int:pk>/', views.LoyaltyUpdateView.as_view(), name='api_loyalty_update'),

    path('promo-codes/', views.PromoCodeListView.as_view(), name='api_promo_code_list'),
    path('promo-codes/<int:pk>/', views.PromoCodeDeleteView.as_view(), name='api_promo_code_delete'),
]
