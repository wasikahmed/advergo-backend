from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Category, CategoryFilterOption, Design, Fabric, Product, SizeChartRow


class CategoryFilterOptionInline(TabularInline):
    model = CategoryFilterOption
    extra = 1
    ordering = ["order"]


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "icon", "order"]
    ordering = ["order", "name"]
    search_fields = ["name", "slug"]
    inlines = [CategoryFilterOptionInline]


@admin.register(Fabric)
class FabricAdmin(ModelAdmin):
    list_display = ["name", "grade", "best_for", "order"]
    list_filter = ["grade"]
    search_fields = ["name", "grade", "best_for"]
    ordering = ["order", "name"]


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ["name", "category", "price_range", "is_featured", "is_active", "order"]
    list_filter = ["category", "is_featured", "is_active"]
    search_fields = ["name", "fabric"]
    ordering = ["order", "name"]
    autocomplete_fields = ["category"]


@admin.register(SizeChartRow)
class SizeChartRowAdmin(ModelAdmin):
    list_display = [
        "size_label",
        "category",
        "chest_in",
        "length_in",
        "shoulder_in",
        "sleeve_in",
        "order",
    ]
    list_filter = ["category"]
    ordering = ["category", "order"]
    autocomplete_fields = ["category"]


@admin.register(CategoryFilterOption)
class CategoryFilterOptionAdmin(ModelAdmin):
    list_display = ["label", "value", "category", "order"]
    list_filter = ["category"]
    search_fields = ["label", "value"]
    ordering = ["category", "order"]
    autocomplete_fields = ["category"]


@admin.register(Design)
class DesignAdmin(ModelAdmin):
    list_display = ["__str__", "category", "filter_option", "is_active", "order", "created_at"]
    list_filter = ["category", "filter_option", "is_active"]
    search_fields = ["name", "code"]
    ordering = ["-created_at"]
    autocomplete_fields = ["category", "filter_option"]
