from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import Permission

from apps.users.models import User

from .fields import GroupedPermissionField
from .models import Role


class RoleForm(forms.ModelForm):
    """
    Group.permissions is a real m2m on the model, so ModelForm handles it
    normally (via save_m2m). "members" isn't -- it's the reverse side of
    User.groups -- so it's added as a plain field here and synced onto
    role.user_set manually in save_m2m(), which is the same hook + timing
    Django's own admin uses for m2m saves (after the object has a pk).
    """

    permissions = GroupedPermissionField(
        queryset=Permission.objects.select_related("content_type"),
        required=False,
    )
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_staff=True).order_by("full_name", "email"),
        required=False,
        widget=FilteredSelectMultiple("staff members", is_stacked=False),
    )

    class Meta:
        model = Role
        fields = ["name", "permissions"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["members"].initial = self.instance.user_set.all()

    def _save_m2m(self):
        # ModelForm.save(commit=True) calls this directly, and
        # save(commit=False) does `self.save_m2m = self._save_m2m` -- an
        # *instance* attribute that would shadow a same-named class method,
        # which is why this overrides the private hook instead of the public
        # save_m2m() Django's own docs point at for custom ModelForms.
        super()._save_m2m()
        self.instance.user_set.set(self.cleaned_data.get("members", []))
