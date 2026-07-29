import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_register_creates_user(api_client):
    payload = {
        "email": "new.customer@example.com",
        "password": "Str0ngPassw0rd!",
        "full_name": "New Customer",
    }
    response = api_client.post("/api/v1/auth/register/", payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["email"] == payload["email"]
    assert "password" not in response.data


def test_register_rejects_weak_password(api_client):
    payload = {"email": "weak@example.com", "password": "123"}
    response = api_client.post("/api/v1/auth/register/", payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_register_requires_email_or_phone(api_client):
    response = api_client.post("/api/v1/auth/register/", {"password": "Str0ngPassw0rd!"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_with_email_returns_tokens(api_client):
    UserFactory(email="login@example.com", password="Str0ngPassw0rd!")
    response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "login@example.com", "password": "Str0ngPassw0rd!"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


def test_login_with_phone_returns_tokens(api_client):
    UserFactory(email="phoneuser@example.com", phone="+8801700000000", password="Str0ngPassw0rd!")
    response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "+8801700000000", "password": "Str0ngPassw0rd!"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


def test_login_with_wrong_password_fails(api_client):
    UserFactory(email="badlogin@example.com", password="Str0ngPassw0rd!")
    response = api_client.post(
        "/api/v1/auth/login/", {"identifier": "badlogin@example.com", "password": "wrong"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_requires_authentication(api_client):
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_returns_profile_when_authenticated(api_client):
    user = UserFactory(email="me@example.com", password="Str0ngPassw0rd!")
    login = api_client.post(
        "/api/v1/auth/login/", {"identifier": "me@example.com", "password": "Str0ngPassw0rd!"}
    )
    access = login.data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == user.email
