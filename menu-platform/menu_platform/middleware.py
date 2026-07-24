from django.conf import settings
from django.utils import translation


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
