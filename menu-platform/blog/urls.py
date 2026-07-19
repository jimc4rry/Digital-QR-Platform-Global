from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.blog_list, name='blog_list'),
    path('manage/', views.blog_admin_list, name='admin_list'),
    path('manage/new/', views.blog_admin_create, name='admin_create'),
    path('manage/<int:pk>/edit/', views.blog_admin_edit, name='admin_edit'),
    path('manage/<int:pk>/delete/', views.blog_admin_delete, name='admin_delete'),
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),
]
