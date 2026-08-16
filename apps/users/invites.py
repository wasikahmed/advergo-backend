from django.conf import settings
from django.core.mail import send_mail


def send_staff_invite_email(invite):
    """Shared by the API (StaffInviteCreateView) and the Django admin
    (StaffInviteAdmin.save_model) -- both create a StaffInvite the same way,
    so the notification email lives in one place instead of being
    duplicated (and silently forgotten, as it was in the admin path)."""
    accept_link = f"{settings.FRONTEND_URL}/admin/accept-invite?token={invite.token}"
    send_mail(
        subject="You've been invited to the Advergo admin",
        message=(
            f"You've been invited to join the Advergo admin as part of the "
            f"'{invite.group.name}' group. Accept the invite and set your password here: "
            f"{accept_link}\n\nThis link expires in 7 days."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invite.email],
    )
