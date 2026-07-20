from django.shortcuts import render

from .tool_views import get_demo_examples


def home(request):
    return render(request, 'home.html', {'examples': get_demo_examples()})
