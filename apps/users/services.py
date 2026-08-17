from .models import User


def get_or_create_guest_user(*, email: str = "", phone: str = "") -> User | None:
    """
    Finds an existing account by email or phone, or creates an inactive
    "shell" account to attach history to. Used whenever a quote comes in
    without the submitter being logged in -- a website guest, or a staff-
    entered lead from a phone call/social DM -- so every quote/order
    references *some* account from day one, before the customer has ever
    formally registered. The account stays unusable (no password) until
    they claim it: either by registering with the same email (routed
    through the password-reset-style claim flow) or by signing in with
    Google using that email (which activates it automatically).
    """
    email = email or ""
    phone = phone or ""
    if not email and not phone:
        return None

    if email:
        user = User.objects.filter(email__iexact=email).first()
        if user:
            return user
    if phone:
        user = User.objects.filter(phone=phone).first()
        if user:
            return user

    user = User(email=email or None, phone=phone or None, is_active=False)
    user.set_unusable_password()
    user.save()
    return user
