from itertools import groupby

from django import forms
from django.apps import apps as django_apps
from django.forms.models import ModelChoiceIterator
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget


def _strip_can_prefix(name: str) -> str:
    # Permission.name defaults to "Can view order" -- the group header
    # already says "Orders", so "Can " just repeats the obvious.
    if name.lower().startswith("can "):
        name = name[4:]
    return name[:1].upper() + name[1:]


class GroupedPermissionIterator(ModelChoiceIterator):
    """
    Groups the flat ~150-row Permission queryset by app (e.g. "Orders",
    "Catalog") instead of Django's raw alphabetical "Order | Can add order"
    list -- ChoiceWidget.optgroups() renders a (label, [choices]) pair as a
    fieldset automatically, so this is the only piece needed to turn
    CheckboxSelectMultiple into a grouped picker. Each permission's own
    label still names its model ("View category") since optgroups only
    nests one level deep and most apps here own several models.
    """

    def __iter__(self):
        queryset = self.queryset.select_related("content_type").order_by(
            "content_type__app_label", "content_type__model", "codename"
        )
        for app_label, perms in groupby(queryset, key=lambda p: p.content_type.app_label):
            try:
                group_label = django_apps.get_app_config(app_label).verbose_name
            except LookupError:
                group_label = app_label
            yield (group_label, [self.choice(p) for p in perms])


class GroupedPermissionsWidget(UnfoldAdminCheckboxSelectMultipleWidget):
    template_name = "access_control/widgets/grouped_permissions.html"


class GroupedPermissionField(forms.ModelMultipleChoiceField):
    iterator = GroupedPermissionIterator
    widget = GroupedPermissionsWidget

    def label_from_instance(self, obj):
        return _strip_can_prefix(obj.name)
