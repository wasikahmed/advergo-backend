from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import ActivityLog, LoginEvent


class StaffOrCustomerFilter(admin.SimpleListFilter):
    title = "account type"
    parameter_name = "account_type"

    def lookups(self, request, model_admin):
        return [("staff", "Staff"), ("customer", "Customer")]

    def queryset(self, request, queryset):
        if self.value() == "staff":
            return queryset.filter(**{f"{self.user_field}__is_staff": True})
        if self.value() == "customer":
            return queryset.filter(**{f"{self.user_field}__is_staff": False})
        return queryset


class LoginAccountTypeFilter(StaffOrCustomerFilter):
    user_field = "user"


class ActivityAccountTypeFilter(StaffOrCustomerFilter):
    user_field = "actor"


class ReadOnlyAdminMixin:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LoginEvent)
class LoginEventAdmin(ReadOnlyAdminMixin, ModelAdmin):
    list_display = ["created_at", "user", "identifier", "channel", "success", "ip_address"]
    list_filter = ["success", "channel", LoginAccountTypeFilter]
    search_fields = ["identifier", "user__email", "user__phone", "user__full_name", "ip_address"]
    autocomplete_fields = ["user"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "user",
        "identifier",
        "channel",
        "success",
        "ip_address",
        "user_agent",
        "created_at",
    ]


@admin.register(ActivityLog)
class ActivityLogAdmin(ReadOnlyAdminMixin, ModelAdmin):
    list_display = ["created_at", "actor", "verb", "content_type", "object_repr"]
    list_filter = ["verb", "content_type", ActivityAccountTypeFilter]
    search_fields = ["actor__email", "actor__full_name", "object_repr", "description"]
    autocomplete_fields = ["actor"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "actor",
        "verb",
        "content_type",
        "object_id",
        "object_repr",
        "description",
        "ip_address",
        "created_at",
    ]
