from rest_framework.permissions import BasePermission
from restaurants.permissions import get_restaurant_and_role, ROLE_LEVELS


class HasRestaurantRole(BasePermission):
    """DRF equivalent of restaurant_role_required - resolves request.restaurant/
    request.staff_role from the same helper the web dashboard uses, so the mobile
    API enforces exactly the same owner/admin/employee rules, including the
    lapsed-subscription lockout."""
    min_role = 'employee'
    message = 'The business subscription/trial has expired.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        restaurant, role = get_restaurant_and_role(request.user)
        if restaurant is None:
            return False
        if not restaurant.user.has_active_subscription():
            return False
        request.restaurant = restaurant
        request.staff_role = role
        return ROLE_LEVELS[role] >= ROLE_LEVELS[self.min_role]


class IsRestaurantAdmin(HasRestaurantRole):
    min_role = 'admin'


class IsRestaurantOwner(HasRestaurantRole):
    min_role = 'owner'
