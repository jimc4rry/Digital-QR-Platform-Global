from django.http import Http404
from django.shortcuts import render

from .feature_pages import FEATURE_PAGES
from .tool_views import get_demo_examples


def home(request):
    return render(request, 'home.html', {'examples': get_demo_examples()})


def feature_detail(request, slug):
    feature = FEATURE_PAGES.get(slug)
    if not feature:
        raise Http404
    return render(request, 'features/feature_detail.html', {'feature': feature, 'slug': slug, 'features': FEATURE_PAGES})
