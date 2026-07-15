from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from restaurants import views as restaurant_views
from . import seo_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('terms/', TemplateView.as_view(template_name='terms.html'), name='terms'),
    path('accounts/', include('accounts.urls')),
    path('restaurant/', include('restaurants.urls')),
    path('orders/', include('orders.urls')),
    path('api/v1/', include('api.urls')),
    path('menu/<str:token>/', restaurant_views.public_menu, name='public_menu'),
    path('menu/<str:token>/table/<int:table_id>/', restaurant_views.public_menu, name='public_menu_table'),
    path('robots.txt', seo_views.robots_txt, name='robots_txt'),
    path('sitemap.xml', seo_views.sitemap_xml, name='sitemap_xml'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)