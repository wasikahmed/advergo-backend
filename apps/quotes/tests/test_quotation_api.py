from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core import mail
from rest_framework import status
from rest_framework.test import APIClient

from apps.invoices.models import Quotation
from apps.quotes.models import QuoteRequest
from apps.users.tests.factories import UserFactory
from apps.users.tests.helpers import login

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def quote():
    return QuoteRequest.objects.create(
        reference_code="QR-QUOTST01",
        name="Rafiqul Islam",
        phone="0170000",
        email="rafiq@example.com",
        quantity=20,
        estimated_price_low=Decimal("400.00"),
        estimated_price_high=Decimal("500.00"),
    )


def test_admin_can_generate_quotation(api_client, quote):
    admin = UserFactory(email="quoadmin@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, admin.email)
    mail.outbox.clear()

    response = api_client.post(f"/api/v1/quotes/{quote.id}/generate_quotation/")
    assert response.status_code == status.HTTP_202_ACCEPTED

    quotation = Quotation.objects.get(quote_request=quote)
    assert quotation.pdf_file.name
    assert quotation.quotation_number == "QUO-QUOTST01"
    assert quotation.sent_at is not None
    assert len(mail.outbox) == 1


def test_regenerating_quotation_keeps_history(api_client, quote):
    admin = UserFactory(email="quoadmin2@example.com", password="Str0ngPassw0rd!", is_staff=True)
    login(api_client, admin.email)

    api_client.post(f"/api/v1/quotes/{quote.id}/generate_quotation/")
    api_client.post(f"/api/v1/quotes/{quote.id}/generate_quotation/")

    assert Quotation.objects.filter(quote_request=quote).count() == 2


def test_non_admin_cannot_generate_quotation(api_client, quote):
    user = UserFactory(email="quolimited@example.com", password="Str0ngPassw0rd!")
    group, _ = Group.objects.get_or_create(name="AccountsLimited")
    user.groups.add(group)
    login(api_client, user.email)

    response = api_client.post(f"/api/v1/quotes/{quote.id}/generate_quotation/")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Quotation.objects.filter(quote_request=quote).exists()
