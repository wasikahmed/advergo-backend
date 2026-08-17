from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"

    def ready(self):
        from django.contrib import admin

        from .autocomplete import AvatarAutocompleteJsonView

        admin.site.autocomplete_view = AvatarAutocompleteJsonView.as_view(admin_site=admin.site)
