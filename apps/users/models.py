from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.core.models import TimeStampedModel

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Public site visitors browse without an account. Registration (email or
    phone) is required only to place an order or use the wishlist.
    Staff roles (admin vs. accounts) are expressed via is_staff + Groups
    ("AccountsFull" / "AccountsLimited"), not a hardcoded role field, so
    permissions stay data-driven and adjustable from the admin.
    """

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=150, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
