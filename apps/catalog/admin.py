from django.contrib import admin, messages
from django.db.models import Count
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from apps.core.utils import admin_action_redirect

from .models import (
    Category,
    Design,
    Fabric,
    FabricImage,
    Product,
    ProductType,
    ReadyProduct,
    ShowcaseProduct,
    SizeChartRow,
)


class SubcategoryInline(TabularInline):
    model = Category
    fk_name = "parent"
    extra = 1
    fields = ["name", "slug", "image", "is_featured", "order"]
    ordering = ["order"]


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    """
    The changelist defaults to main categories only (`parent` is unset) so
    staff aren't scrolling through every subcategory mixed in at once --
    click "View subcategories" (or the Parent filter) to drill into one.
    Passing a Parent filter explicitly (including "-" for "no parent") shows
    exactly what was asked for instead.
    """

    list_display = ["name", "slug", "parent", "is_featured", "order", "subcategory_count"]
    list_filter = ["is_featured", "parent"]
    ordering = ["order", "name"]
    search_fields = ["name", "slug"]
    autocomplete_fields = ["parent"]
    inlines = [SubcategoryInline]
    actions_row = ["view_subcategories_row"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request).annotate(_subcategory_count=Count("children"))
        # The site-wide autocomplete endpoint (used by every
        # `autocomplete_fields = ["category"]` elsewhere -- Product, Design,
        # SizeChartRow) calls THIS get_queryset as its base queryset, with
        # no parent filter param of its own. Applying the changelist's
        # "main categories only" default there would make every subcategory
        # (e.g. "Polo Shirt -> Half Sleeve") permanently unselectable
        # anywhere else in the admin, so it's explicitly excluded here.
        is_autocomplete = request.path.endswith("/autocomplete/")
        if (
            not is_autocomplete
            and "parent__id__exact" not in request.GET
            and "parent__isnull" not in request.GET
        ):
            queryset = queryset.filter(parent__isnull=True)
        return queryset

    @admin.display(description="Subcategories")
    def subcategory_count(self, obj):
        return obj._subcategory_count

    @action(description="View subcategories", icon="subdirectory_arrow_right")
    def view_subcategories_row(self, request, object_id):
        category = self.get_object(request, object_id)
        if category is None:
            self.message_user(request, "Category not found.", level=messages.ERROR)
            return admin_action_redirect(request, reverse("admin:catalog_category_changelist"))
        if category._subcategory_count == 0:
            self.message_user(
                request, f"{category.name} has no subcategories.", level=messages.INFO
            )
            return admin_action_redirect(request, reverse("admin:catalog_category_changelist"))
        url = f"{reverse('admin:catalog_category_changelist')}?parent__id__exact={category.pk}"
        return admin_action_redirect(request, url)


class FabricImageInline(TabularInline):
    model = FabricImage
    extra = 1
    fields = ["image", "order"]
    ordering = ["order", "id"]


@admin.register(Fabric)
class FabricAdmin(ModelAdmin):
    list_display = ["name", "grade", "best_for", "order"]
    list_filter = ["grade"]
    search_fields = ["name", "grade", "best_for"]
    ordering = ["order", "name"]
    inlines = [FabricImageInline]


class BaseProductAdmin(ModelAdmin):
    """Shared behavior for the Product admin and its two upload-focused
    proxies (Ready Products / Showcase Products) -- category scoping,
    ordering, and the leaf-category-only autocomplete restriction all
    apply identically regardless of which screen staff are using."""

    list_filter = ["is_featured", "is_active", "category__parent"]
    search_fields = ["name", "fabric"]
    # Grouped by main category then subcategory, so products naturally
    # cluster together on the page instead of one flat alphabetical pile.
    ordering = [
        "category__parent__order",
        "category__parent__name",
        "category__order",
        "order",
        "name",
    ]
    autocomplete_fields = ["category"]

    @admin.display(description="Section")
    def category_section(self, obj):
        return obj.category.section if obj.category_id else "-"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category", "category__parent")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "category":
            # A leaf category is any product bucket, whether it's nested
            # under a parent (Polo Shirt -> Half Sleeve) or stands on its
            # own (Marathon, Cricket, ...). A category with children is
            # always a grouping node, never itself a product bucket.
            field.queryset = field.queryset.filter(children__isnull=True)
        return field


@admin.register(Product)
class ProductAdmin(BaseProductAdmin):
    """Full, unfiltered view across every product -- for search/cleanup
    only. Day-to-day uploads happen on the Ready Products / Showcase
    Products screens below, which force the right `product_type`
    automatically instead of staff having to set it by hand."""

    list_display = [
        "name",
        "category",
        "category_section",
        "product_type",
        "age_group",
        "price_range",
        "is_featured",
        "is_active",
        "order",
    ]
    list_filter = [*BaseProductAdmin.list_filter, "product_type"]
    fields = [
        "name",
        "category",
        "product_type",
        "age_group",
        "price_range",
        "list_price",
        "sale_price",
        "discount_percent",
        "fabric",
        "rating",
        "review_count",
        "accent_color",
        "image",
        "is_featured",
        "is_active",
        "order",
    ]


@admin.register(ReadyProduct)
class ReadyProductAdmin(BaseProductAdmin):
    """Upload screen for priced, in-stock products (club/tournament
    jerseys, etc.) -- shown on the storefront with Add to Cart."""

    list_display = [
        "name",
        "category",
        "category_section",
        "age_group",
        "price_range",
        "list_price",
        "sale_price",
        "discount_percent",
        "is_featured",
        "is_active",
        "order",
    ]
    fields = [
        "name",
        "category",
        "age_group",
        "price_range",
        "list_price",
        "sale_price",
        "discount_percent",
        "fabric",
        "rating",
        "review_count",
        "accent_color",
        "image",
        "is_featured",
        "is_active",
        "order",
    ]

    def save_model(self, request, obj, form, change):
        obj.product_type = ProductType.READY
        super().save_model(request, obj, form, change)


@admin.register(ShowcaseProduct)
class ShowcaseProductAdmin(BaseProductAdmin):
    """Upload screen for made-to-order examples -- no price fields at
    all, per spec: these are inspiration, customers order via a quote."""

    list_display = [
        "name",
        "category",
        "category_section",
        "is_featured",
        "is_active",
        "order",
    ]
    fields = [
        "name",
        "category",
        "fabric",
        "rating",
        "review_count",
        "accent_color",
        "image",
        "is_featured",
        "is_active",
        "order",
    ]

    def save_model(self, request, obj, form, change):
        obj.product_type = ProductType.SHOWCASE
        super().save_model(request, obj, form, change)


@admin.register(SizeChartRow)
class SizeChartRowAdmin(ModelAdmin):
    list_display = [
        "size_label",
        "category",
        "age_group",
        "chest_in",
        "length_in",
        "order",
    ]
    list_filter = ["age_group", "category"]
    ordering = ["category", "age_group", "order"]
    autocomplete_fields = ["category"]


@admin.register(Design)
class DesignAdmin(ModelAdmin):
    list_display = ["__str__", "category", "is_active", "order", "created_at"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "code"]
    ordering = ["-created_at"]
    autocomplete_fields = ["category"]
