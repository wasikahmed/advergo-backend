from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import ProductReview, Review, ReviewStatus


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


@admin.register(ProductReview)
class ProductReviewAdmin(ModelAdmin):
    list_display = ["product", "user", "rating", "status", "created_at"]
    list_filter = ["status", "rating"]
    search_fields = ["product__name", "user__email", "user__full_name", "text"]
    autocomplete_fields = ["product", "user"]
    actions = ["approve_reviews", "reject_reviews"]

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        queryset.update(status=ReviewStatus.APPROVED)

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        queryset.update(status=ReviewStatus.REJECTED)
