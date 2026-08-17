from django.contrib.auth.models import AbstractBaseUser, Group, PermissionsMixin
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

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

    # Nullable (not just blank) so two phone-only accounts don't collide on
    # email="" -- Postgres treats multiple NULLs in a unique column as distinct.
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=150, blank=True)
    # Points at Google's own CDN copy (from the ID token's `picture` claim) --
    # not re-uploaded to our storage. Blank for accounts that never signed in
    # with Google.
    avatar_url = models.URLField(max_length=500, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()
    # Who/when for every change (e.g. is_active flipping True on account
    # claim, an admin changing a group) -- password excluded since a hash
    # snapshot per change isn't useful and needlessly widens the blast
    # radius if the history table were ever exposed.
    history = HistoricalRecords(excluded_fields=["password"])

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email or self.phone or str(self.pk)


class StaffInvite(TimeStampedModel):
    """
    Invite-only path for creating staff accounts -- an existing admin invites
    an email address to a specific Group, the recipient follows the link and
    sets their own password. No open self-serve staff registration endpoint.
    """

    email = models.EmailField()
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="staff_invites")
    invited_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, related_name="staff_invites_sent"
    )
    token = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} -> {self.group.name}"

    @property
    def is_valid(self):
        return self.accepted_at is None and timezone.now() < self.expires_at
