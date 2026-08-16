from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from unfold.widgets import INPUT_CLASSES


class AdminPasswordResetForm(PasswordResetForm):
    """Django's built-in PasswordResetForm doesn't go through Unfold's admin
    form machinery, so its widgets render with no styling at all. Same fix
    Unfold's own AdminPasswordChangeForm uses -- see unfold/forms.py."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["class"] = " ".join(INPUT_CLASSES)


class AdminSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs["class"] = " ".join(INPUT_CLASSES)
        self.fields["new_password2"].widget.attrs["class"] = " ".join(INPUT_CLASSES)
