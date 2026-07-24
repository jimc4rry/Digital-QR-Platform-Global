import re
from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.views.generic import TemplateView
from django.views.static import serve as serve_static
from restaurants import views as restaurant_views
from . import seo_views, tool_views, views as menu_platform_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', menu_platform_views.home, name='home'),
    path('terms/', TemplateView.as_view(template_name='terms.html'), name='terms'),
    path('privacy/', TemplateView.as_view(template_name='privacy.html'), name='privacy'),
    path('refund-policy/', TemplateView.as_view(template_name='refund_policy.html'), name='refund_policy'),
    path('guides/', TemplateView.as_view(template_name='guides/index.html'), name='guides_index'),
    path('guides/how-to-create-a-qr-code-menu/', TemplateView.as_view(template_name='guides/how_to_create_qr_menu.html'), name='guide_how_to_create'),
    path('guides/qr-code-menu-cost/', TemplateView.as_view(template_name='guides/qr_menu_cost.html'), name='guide_cost'),
    path('guides/qr-code-menu-vs-printed-menu/', TemplateView.as_view(template_name='guides/qr_vs_printed_menu.html'), name='guide_vs_printed'),
    path('blog/', include('blog.urls', namespace='blog')),
    path('feedback/', include('feedback.urls', namespace='feedback')),
    path('free-qr-code-generator/', tool_views.free_qr_code_generator, name='free_qr_code_generator'),
    path('tools/printing-cost-calculator/', TemplateView.as_view(template_name='tools/printing_cost_calculator.html'), name='printing_cost_calculator'),
    path('examples/', tool_views.qr_menu_examples, name='qr_menu_examples'),
    path('accounts/', include('accounts.urls')),
    path('restaurant/', include('restaurants.urls')),
    path('orders/', include('orders.urls')),
    path('api/v1/', include('api.urls')),
    path('menu/<str:token>/', restaurant_views.public_menu, name='public_menu'),
    path('menu/<str:token>/table/<int:table_id>/', restaurant_views.public_menu, name='public_menu_table'),
    path('robots.txt', seo_views.robots_txt, name='robots_txt'),
    path('sitemap.xml', seo_views.sitemap_xml, name='sitemap_xml'),
]

# Served by Django itself, deliberately not using django.conf.urls.static.static() - that
# helper silently no-ops whenever DEBUG=False, which would 404 every uploaded/generated file
# (QR codes, product photos) in production. There's no separate media server/CDN in front of
# this app, so Django has to serve these itself. Fine for this app's traffic level; a
# dedicated object storage service (S3/R2/etc, already supported via AWS_STORAGE_BUCKET_NAME)
# is the better long-term fix if traffic or file volume grows.
urlpatterns += [
    re_path(r'^%s(?P<path>.*)$' % re.escape(settings.MEDIA_URL.lstrip('/')), serve_static, {'document_root': settings.MEDIA_ROOT}),
]