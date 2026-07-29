from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import UserChangeForm, UserCreationForm

from .models import User


@admin.register(User)
class UserAdmin(ModelAdmin, DjangoUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    model = User
    ordering = ["-created_at"]
    list_display = ["email", "phone", "full_name", "is_staff", "is_active", "created_at"]
    list_filter = ["is_staff", "is_active", "groups"]
    search_fields = ["email", "phone", "full_name"]

    fieldsets = (
        (None, {"fields": ("email", "phone", "password")}),
        ("Personal info", {"fields": ("full_name",)}),
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
