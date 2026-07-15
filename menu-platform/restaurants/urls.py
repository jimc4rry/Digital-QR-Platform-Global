from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='restaurant_dashboard'),
    path('settings/', views.restaurant_settings, name='restaurant_settings'),
    path('stats/', views.stats_dashboard, name='stats_dashboard'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('api/product-option/add/', views.product_option_add, name='product_option_add'),
    path('api/product-option/<int:pk>/delete/', views.product_option_delete, name='product_option_delete'),
    path('tables/', views.table_list, name='table_list'),
    path('tables/<int:pk>/delete/', views.table_delete, name='table_delete'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/<int:pk>/delete/', views.staff_delete, name='staff_delete'),
    path('promo-codes/', views.promo_code_list, name='promo_code_list'),
    path('promo-codes/<int:pk>/delete/', views.promo_code_delete, name='promo_code_delete'),
    path('loyalty/', views.loyalty_list, name='loyalty_list'),
    path('loyalty/<int:pk>/edit/', views.loyalty_edit, name='loyalty_edit'),
    path('loyalty/<int:pk>/delete/', views.loyalty_delete, name='loyalty_delete'),
]