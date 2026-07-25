import re
from urllib.parse import urlparse

from django.conf import settings
from django.utils import translation

_ROOT_RE = re.compile(r'^/$')
_TABLE_RE = re.compile(r'^/table/(?P<table_id>\d+)/$')


class RestaurantSubdomainMiddleware:
    """Requests to <slug>.getmenuhub.com serve that restaurant's public menu
    directly at the root path (and /table/<id>/ for a specific table), the
    same page the legacy /menu/<token>/ URL renders. Only those two paths are
    intercepted - everything else (the order API, static/media, the
    dashboard) falls through to normal routing unchanged, so it keeps working
    identically regardless of which host it's reached through.

    Must run after CsrfViewMiddleware (so short-circuiting here still lets its
    response-phase cookie-setting logic run, needed for the order form's CSRF
    token on this same page) and after LanguageMiddleware (so translation.activate()
    has already run deterministically before we potentially short-circuit -
    otherwise this page could inherit whatever language a previous request on
    the same worker thread last activated)."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._base_domain = urlparse(settings.SITE_URL).netloc.split(':')[0]

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()
        suffix = f'.{self._base_domain}'
        if self._base_domain and host.endswith(suffix):
            slug = host[: -len(suffix)]
            if slug and slug != 'www' and '.' not in slug:
                match = _ROOT_RE.match(request.path_info) or _TABLE_RE.match(request.path_info)
                if match:
                    from restaurants.views import public_menu_by_slug
                    table_id = match.groupdict().get('table_id')
                    return public_menu_by_slug(request, slug, table_id=int(table_id) if table_id else None)
        return self.get_response(request)


class LanguageMiddleware:
    """Anonymous/public requests always render in English, regardless of the
    browser's Accept-Language header - this keeps the marketing site, blog,
    and guides consistent for SEO and for every visitor, and avoids Google
    ever seeing a partially-translated public page. Only authenticated users
    can pick a UI language (via the standard Django set_language view, e.g.
    a dashboard language switcher); Django 4.2's set_language view stores
    the choice in a cookie (settings.LANGUAGE_COOKIE_NAME), not the session.

    Replaces django.middleware.locale.LocaleMiddleware, whose automatic
    Accept-Language detection is exactly what we don't want for anonymous
    visitors. Must run after AuthenticationMiddleware (request.user)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = 'en'
        if request.user.is_authenticated:
            cookie_language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
            if cookie_language and cookie_language in dict(settings.LANGUAGES):
                language = cookie_language

        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

        response = self.get_response(request)

        translation.deactivate()
        return response
