import secrets
from datetime import timedelta

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import action
from unfold.forms import UserChangeForm, UserCreationForm

from .invites import send_staff_invite_email
from .models import StaffInvite, User


@admin.register(User)
class UserAdmin(SimpleHistoryAdmin, ModelAdmin, DjangoUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    model = User
    ordering = ["-created_at"]
    list_display = ["email", "phone", "full_name", "is_staff", "is_active", "created_at"]
    list_filter = ["is_staff", "is_active", "groups"]
    search_fields = ["email", "phone", "full_name"]

    fieldsets = (
        (None, {"fields": ("email", "phone", "password")}),
        ("Personal info", {"fields": ("full_name", "avatar_url")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "phone", "password1", "password2")}),
    )
    readonly_fields = ["last_login", "created_at", "updated_at"]


@admin.register(StaffInvite)
class StaffInviteAdmin(ModelAdmin):
    """
    Once an invite is accepted it's a historical record, not a thing to
    manage -- editing/deleting it after the fact would let an admin silently
    change what a real account-creation event looked like. Group changes and
    account deletion belong on the User it created (apps.users.admin.UserAdmin),
    not here.
    """

    list_display = ["email", "group", "invited_by", "expires_at", "accepted_at", "created_at"]
    list_filter = ["group"]
    search_fields = ["email"]
    ordering = ["-created_at"]
    readonly_fields = ["token", "invited_by", "expires_at", "accepted_at", "created_at", "updated_at"]
    autocomplete_fields = ["group"]
    actions = ["resend_invite"]
    actions_row = ["resend_invite_row"]

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.accepted_at is not None:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.accepted_at is not None:
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        is_new = not change
        if is_new:
            obj.invited_by = request.user
            obj.token = secrets.token_urlsafe(32)
            obj.expires_at = timezone.now() + timedelta(days=7)
        super().save_model(request, obj, form, change)
        if is_new:
            send_staff_invite_email(obj)
            self.message_user(request, f"Invite email sent to {obj.email}.")

    def _resend(self, invite):
        invite.token = secrets.token_urlsafe(32)
        invite.expires_at = timezone.now() + timedelta(days=7)
        invite.save(update_fields=["token", "expires_at"])
        send_staff_invite_email(invite)

    @admin.action(description="Resend invite email (refreshes the link's expiry)")
    def resend_invite(self, request, queryset):
        pending = queryset.filter(accepted_at__isnull=True)
        already_accepted = queryset.count() - pending.count()

        sent = 0
        for invite in pending:
            self._resend(invite)
            sent += 1

        self.message_user(request, f"Resent {sent} invite(s).", level=messages.SUCCESS)
        if already_accepted:
            self.message_user(
                request,
                f"Skipped {already_accepted} already-accepted invite(s).",
                level=messages.WARNING,
            )

    @action(description="Resend", icon="mail")
    def resend_invite_row(self, request, object_id):
        # Unfold's actions_row button list is computed once for the whole
        # table, not per row, so an already-accepted invite still gets the
        # button -- guard here instead and fail gracefully rather than with
        # a raw 403.
        invite = self.get_object(request, object_id)
        if invite is None:
            self.message_user(request, "Invite not found.", level=messages.ERROR)
        elif invite.accepted_at is not None:
            self.message_user(
                request,
                f"{invite.email} already accepted their invite -- nothing to resend.",
                level=messages.WARNING,
            )
        else:
            self._resend(invite)
            self.message_user(request, f"Invite email resent to {invite.email}.", level=messages.SUCCESS)
        return redirect(reverse("admin:users_staffinvite_changelist"))
