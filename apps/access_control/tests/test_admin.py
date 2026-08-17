import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from apps.access_control.fields import GroupedPermissionField
from apps.access_control.models import Role
from apps.users.admin_2fa import SESSION_VERIFIED_KEY
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _client_for(user):
    client = Client()
    client.force_login(user)
    session = client.session
    session[SESSION_VERIFIED_KEY] = True
    session.save()
    return client


@pytest.fixture
def superuser():
    return UserFactory(email="super@example.com", is_staff=True, is_superuser=True)


@pytest.fixture
def staff():
    return UserFactory(email="regularstaff@example.com", is_staff=True, is_superuser=False)


def test_grouped_permission_field_groups_by_app():
    field = GroupedPermissionField(queryset=Permission.objects.select_related("content_type"))
    groups = dict(field.choices)
    assert "Orders" in groups
    order_labels = [label for _value, label in groups["Orders"]]
    assert "View order" in order_labels


def test_role_changelist_requires_superuser(staff):
    client = _client_for(staff)
    response = client.get(reverse("admin:access_control_role_changelist"))
    assert response.status_code == 403


def test_role_changelist_allows_superuser(superuser):
    client = _client_for(superuser)
    response = client.get(reverse("admin:access_control_role_changelist"))
    assert response.status_code == 200


def test_role_admin_uses_full_width_fields(superuser):
    from apps.access_control.admin import RoleAdmin

    # compressed_fields=True (Unfold's default) reserves a fixed left label
    # column that's redundant here -- the Members/Permissions fieldset
    # headings already say what the wide widgets below them are.
    assert RoleAdmin.compressed_fields is False


def test_create_role_assigns_permissions_and_members(superuser):
    client = _client_for(superuser)
    member = UserFactory(email="member@example.com", is_staff=True)
    perm = Permission.objects.get(codename="view_order", content_type__app_label="orders")

    response = client.post(
        reverse("admin:access_control_role_add"),
        {
            "name": "Order Viewers",
            "permissions": [perm.pk],
            "members": [member.pk],
        },
    )

    assert response.status_code == 302
    role = Role.objects.get(name="Order Viewers")
    assert list(role.permissions.all()) == [perm]
    assert list(role.user_set.all()) == [member]


def test_editing_role_updates_members(superuser):
    client = _client_for(superuser)
    role = Role.objects.create(name="Editable Role")
    original_member = UserFactory(email="original@example.com", is_staff=True)
    new_member = UserFactory(email="newmember@example.com", is_staff=True)
    role.user_set.add(original_member)

    response = client.post(
        reverse("admin:access_control_role_change", args=[role.pk]),
        {"name": "Editable Role", "permissions": [], "members": [new_member.pk]},
    )

    assert response.status_code == 302
    role.refresh_from_db()
    assert list(role.user_set.all()) == [new_member]


def test_group_admin_hidden_from_module_list(superuser):
    from django.contrib import admin
    from django.contrib.auth.models import Group

    group_admin = admin.site._registry[Group]
    client = _client_for(superuser)
    request = client.get(reverse("admin:index")).wsgi_request
    assert group_admin.has_module_permission(request) is False


def test_user_permissions_field_uses_grouped_widget(superuser):
    from apps.users.admin import UserAdmin
    from apps.users.models import User

    admin_instance = UserAdmin(User, __import__("django.contrib.admin").contrib.admin.site)
    field = User._meta.get_field("user_permissions")
    formfield = admin_instance.formfield_for_manytomany(field, request=None)
    assert isinstance(formfield, GroupedPermissionField)
