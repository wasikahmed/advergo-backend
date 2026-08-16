from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Category, Design, Fabric, Product, SizeChartRow


class SubcategoryInline(TabularInline):
    model = Category
    fk_name = "parent"
    extra = 1
    fields = ["name", "slug", "image", "is_featured", "order"]
    ordering = ["order"]


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "parent", "is_featured", "order"]
    list_filter = ["is_featured", "parent"]
    ordering = ["order", "name"]
    search_fields = ["name", "slug"]
    autocomplete_fields = ["parent"]
    inlines = [SubcategoryInline]


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


@admin.register(Design)
class DesignAdmin(ModelAdmin):
    list_display = ["__str__", "category", "is_active", "order", "created_at"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "code"]
    ordering = ["-created_at"]
    autocomplete_fields = ["category"]
