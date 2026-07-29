from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_accounts_full(user):
    """Superusers, is_staff, or explicit AccountsFull group membership."""
    return bool(user.is_staff or user.groups.filter(name="AccountsFull").exists())


def is_accounts_limited(user):
    """In AccountsLimited but *not* already covered by is_accounts_full."""
    return not is_accounts_full(user) and user.groups.filter(name="AccountsLimited").exists()


def is_accounts_staff(user):
    return is_accounts_full(user) or is_accounts_limited(user)


class CanManageOrders(BasePermission):
    """
    Read: any authenticated user (queryset scoping in the view handles who
    actually sees what -- accounts staff see everything, a plain customer
    only their own orders).
    Write: Admin / AccountsFull only. Orders are staff-entered after a phone
    confirmation (spec: no self-service checkout), and AccountsLimited is
    explicitly read-only.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return is_accounts_full(user)
