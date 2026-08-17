from django.contrib.auth.models import Group


class Role(Group):
    """
    Proxy of Django's own auth.Group -- same table, same rows, same
    User.groups relation -- so existing group-based checks (has_perm,
    LoginAccountTypeFilter, etc.) keep working unchanged. Only exists so the
    admin can present "Roles" under a dedicated Access Control section
    instead of the generic "Authentication and Authorization / Groups" the
    default django.contrib.auth admin registration would otherwise show.
    """

    class Meta:
        proxy = True
        verbose_name = "Role"
        verbose_name_plural = "Roles"
