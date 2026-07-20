from django.http import HttpResponse
from django.urls import reverse
from blog.models import Post
from restaurants.models import Restaurant


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse('sitemap_xml'))
    lines = [
        'User-agent: *',
        'Allow: /$',
        'Allow: /menu/',
        'Disallow: /accounts/',
        'Disallow: /restaurant/',
        'Disallow: /orders/',
        'Disallow: /admin/',
        f'Sitemap: {sitemap_url}',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


def sitemap_xml(request):
    urls = [
        request.build_absolute_uri(reverse('home')),
        request.build_absolute_uri(reverse('guides_index')),
        request.build_absolute_uri(reverse('guide_how_to_create')),
        request.build_absolute_uri(reverse('guide_cost')),
        request.build_absolute_uri(reverse('guide_vs_printed')),
        request.build_absolute_uri(reverse('blog:blog_list')),
        request.build_absolute_uri(reverse('free_qr_code_generator')),
        request.build_absolute_uri(reverse('printing_cost_calculator')),
        request.build_absolute_uri(reverse('qr_menu_examples')),
    ]
    for post in Post.objects.filter(is_published=True):
        urls.append(request.build_absolute_uri(reverse('blog:blog_detail', args=[post.slug])))
    for restaurant in Restaurant.objects.filter(is_active=True):
        urls.append(request.build_absolute_uri(reverse('public_menu', args=[restaurant.qr_code_token])))

    entries = '\n'.join(f'  <url><loc>{url}</loc></url>' for url in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'{entries}\n'
        '</urlset>'
    )
    return HttpResponse(xml, content_type='application/xml')
