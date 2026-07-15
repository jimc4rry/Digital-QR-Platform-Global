from .permissions import get_restaurant_and_role


def restaurant_context(request):
    """Injects the active restaurant/role and role-based permission flags into
    every template, so the navbar (and any page) can adapt to owner/admin/employee
    without every view having to pass these manually."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    restaurant, role = get_restaurant_and_role(user)
    if restaurant is None:
        return {}

    owner = restaurant.user
    return {
        'active_restaurant': restaurant,
        'staff_role': role,
        'is_owner': role == 'owner',
        'can_manage_menu': role in ('owner', 'admin'),
        'can_use_pro_features': role in ('owner', 'admin') and owner.has_ordering(),
        'can_view_stats': role in ('owner', 'admin') and owner.has_stats_dashboard(),
        'can_manage_staff': role == 'owner' and owner.has_staff_management(),
        'restaurant_accepts_orders': restaurant.allow_ordering and owner.has_ordering(),
    }
