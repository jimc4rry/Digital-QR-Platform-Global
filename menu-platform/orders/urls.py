from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
    path('<int:pk>/delete/', views.order_delete, name='order_delete'),
    path('api/create/<str:token>/', views.create_order_api, name='create_order_api'),
    path('api/validate-promo/<str:token>/', views.validate_promo_code, name='validate_promo_code'),
    path('api/<int:pk>/update-status/', views.update_order_status, name='update_order_status'),
    path('api/pending-count/', views.pending_orders_count, name='pending_orders_count'),
    path('export/csv/', views.export_orders_csv, name='export_orders_csv'),
]