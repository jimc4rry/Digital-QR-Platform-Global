from django.conf import settings


def beta_context(request):
    """Exposes BETA_MODE to every template (including anonymous/public pages
    like the homepage), so the beta banner doesn't need a view to pass it."""
    return {'beta_mode': settings.BETA_MODE}
