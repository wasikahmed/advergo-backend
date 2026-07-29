from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Review, ReviewStatus


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ["name", "organization", "rating", "status", "created_at"]
    list_filter = ["status", "rating"]
    search_fields = ["name", "organization", "text"]
    actions = ["approve_reviews", "reject_reviews"]

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        queryset.update(status=ReviewStatus.APPROVED)

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        queryset.update(status=ReviewStatus.REJECTED)
