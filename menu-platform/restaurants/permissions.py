from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from .models import Restaurant, StaffMember

ROLE_LEVELS = {'employee': 1, 'admin': 2, 'owner': 3}


def get_restaurant_and_role(user):
    """Resolve which restaurant this user acts on and their role there.

    Returns (restaurant, role) where role is 'owner', 'admin', or 'employee'.
    Returns (None, None) if the user owns no restaurant and isn't staff anywhere.
    """
    try:
        return user.restaurant, 'owner'
    except Restaurant.DoesNotExist:
        pass

    staff = StaffMember.objects.select_related('restaurant').filter(user=user).first()
    if staff:
        return staff.restaurant, staff.role
    return None, None


def restaurant_role_required(min_role='employee'):
    """View decorator: resolves request.restaurant / request.staff_role and
    requires at least `min_role` (employee < admin < owner). 404s if the user
    has no restaurant at all; 403s if their role is below the requirement;
    redirects the owner to checkout (403s everyone else) if the restaurant's
    subscription/trial has lapsed - this is the one gate every dashboard view
    shares, so a trial ending or a payment failing locks the whole thing out
    without having to touch every view individually."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            restaurant, role = get_restaurant_and_role(request.user)
            if restaurant is None:
                return HttpResponseForbidden(_('Δεν έχεις πρόσβαση σε κανένα εστιατόριο.'))
            if not restaurant.user.has_active_subscription():
                if role == 'owner':
                    messages.error(request, _('Η συνδρομή/δοκιμή σου έχει λήξει. Επίλεξε πλάνο για να συνεχίσεις.'))
                    return redirect('checkout')
                return HttpResponseForbidden(_('Η συνδρομή της επιχείρησης έχει λήξει. Επικοινώνησε με τον ιδιοκτήτη.'))
            if ROLE_LEVELS[role] < ROLE_LEVELS[min_role]:
                return HttpResponseForbidden(_('Δεν έχεις δικαίωμα πρόσβασης σε αυτή τη σελίδα.'))
            request.restaurant = restaurant
            request.staff_role = role
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
