from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.contrib.contenttypes.management import create_contenttypes
from django.db import migrations

GROUP_NAME = "Catalog Staff"
# Everything a staff member needs to manage the storefront's catalog and
# on-site content from /admin/ -- categories, products, fabrics (incl.
# multiple fabric images), designs, size charts, and general site content
# (banners, gallery, social links, etc). Grant this Group to a staff user
# (User change form -> Permissions -> Groups) instead of assigning model
# permissions one by one.
APP_LABELS = ["catalog", "content"]


def create_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    # Permission rows are normally created by the `post_migrate` signal,
    # which only fires once *after* the whole `migrate` command finishes --
    # too late for this same-release data migration to see permissions for
    # a model (like SocialLink) whose own migration just ran moments ago.
    # Create them explicitly here first so `group.permissions.set(...)`
    # below actually includes every current catalog/content model.
    for app_config in global_apps.get_app_configs():
        if app_config.label in APP_LABELS:
            create_contenttypes(app_config, verbosity=0)
            create_permissions(app_config, verbosity=0)

    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    permissions = Permission.objects.filter(content_type__app_label__in=APP_LABELS)
    group.permissions.set(permissions)


def remove_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0005_fabricimage"),
        ("content", "0002_sociallink"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_group, remove_group),
    ]
