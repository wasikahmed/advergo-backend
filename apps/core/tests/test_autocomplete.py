import json

import pytest
from django.contrib import admin
from django.test import Client
from django.urls import reverse

from apps.users.admin_2fa import SESSION_VERIFIED_KEY
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    staff = UserFactory(email="siteadmin@example.com", is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(staff)
    session = client.session
    session[SESSION_VERIFIED_KEY] = True
    session.save()
    return client, staff


def test_autocomplete_view_is_the_avatar_subclass():
    from apps.core.autocomplete import AvatarAutocompleteJsonView

    assert admin.site.autocomplete_view.view_class is AvatarAutocompleteJsonView


def test_user_autocomplete_includes_avatar_key(admin_client):
    client, staff = admin_client
    UserFactory(full_name="Findable Person", email="findable@example.com")

    response = client.get(
        reverse("admin:autocomplete"),
        {
            "app_label": "orders",
            "model_name": "order",
            "field_name": "customer",
            "term": "Findable",
        },
    )

    assert response.status_code == 200
    results = json.loads(response.content)["results"]
    assert len(results) == 1
    assert results[0]["avatar"] == ""
    assert results[0]["initial"] == "F"


def test_non_user_autocomplete_has_no_avatar_key(admin_client):
    client, staff = admin_client
    from apps.catalog.models import Category

    Category.objects.create(name="Findable Category", slug="findable-category")

    response = client.get(
        reverse("admin:autocomplete"),
        {
            "app_label": "orders",
            "model_name": "order",
            "field_name": "category",
            "term": "Findable",
        },
    )

    assert response.status_code == 200
    results = json.loads(response.content)["results"]
    assert len(results) == 1
    assert "avatar" not in results[0]
