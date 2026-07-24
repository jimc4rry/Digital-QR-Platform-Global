from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    path('submit/', views.submit_feedback, name='submit'),
    path('manage/', views.feedback_admin_list, name='admin_list'),
    path('manage/<int:pk>/', views.feedback_admin_detail, name='admin_detail'),
    path('manage/<int:pk>/mark-read/', views.feedback_admin_mark_read, name='admin_mark_read'),
    path('manage/<int:pk>/delete/', views.feedback_admin_delete, name='admin_delete'),
]
