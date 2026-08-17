from django.contrib import admin
from django.contrib.auth.models import Group

from unfold.admin import ModelAdmin

from .forms import RoleForm
from .models import Role

# The default django.contrib.auth registration renders Group as a generic
# "Authentication and Authorization" entry with Django's raw permission
# multi-select. Role (models.py) is a proxy of the same table, registered
# below with a friendlier form instead. Group itself can't be fully
# unregistered though: StaffInvite.group is a real FK to auth.Group (not the
# proxy) and its autocomplete_fields entry requires *some* ModelAdmin
# registered for that exact model. Re-registering it with has_module_permission
# always False keeps it out of any app list / menu -- Role is the only place
# staff actually browse or edit groups -- while still letting the
# StaffInvite autocomplete search resolve normally for whoever has ordinary
# view access to it.
if admin.site.is_registered(Group):
    admin.site.unregister(Group)


@admin.register(Group)
class HiddenGroupAdmin(ModelAdmin):
    search_fields = ["name"]

    def has_module_permission(self, request):
        return False


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    """
    Superuser-only: this controls who can see/do what everywhere else in the
    admin, so unlike every other section here it isn't gated by a normal
    view/change permission -- granting someone "can manage roles" would let
    them hand themselves any other permission they wanted.
    """

    form = RoleForm
    list_display = ["name", "member_count", "permission_count"]
    search_fields = ["name"]
    fieldsets = (
        (None, {"fields": ("name",)}),
        ("Members", {"fields": ("members",)}),
        ("Permissions", {"fields": ("permissions",)}),
    )
    # Unfold's default puts every field label in a fixed 224px left column
    # (compressed_fields=True) -- fine for short "Name: [____]" rows, but
    # here it just reserves dead space next to a full-width widget whose
    # fieldset heading ("Members"/"Permissions") already says what it is.
    compressed_fields = False

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.user_set.count()

    @admin.display(description="Permissions")
    def permission_count(self, obj):
        return obj.permissions.count()

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)
