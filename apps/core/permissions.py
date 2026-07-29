from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdmin(BasePermission):
    """Full access -- staff/superuser only."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsAccountsStaff(BasePermission):
    """Members of the 'accounts' role: order + invoice management."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_staff
                or user.groups.filter(name__in=["AccountsFull", "AccountsLimited"]).exists()
            )
        )


class IsOwnerOrAdmin(BasePermission):
    """Object owner (via `owner_attr`, default 'user') or staff can access."""

    owner_attr = "user"

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        owner = getattr(obj, self.owner_attr, None)
        return owner == request.user


class ReadOnlyOrAdmin(BasePermission):
    """Anyone can read (list/retrieve); only staff can write."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
