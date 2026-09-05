from django.contrib import admin, messages
from django.db.models import Count
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from apps.core.utils import admin_action_redirect

from .models import Category, Design, Fabric, FabricImage, Product, SizeChartRow


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
        if "parent__id__exact" not in request.GET and "parent__isnull" not in request.GET:
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


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = [
        "name",
        "category",
        "category_section",
        "price_range",
        "list_price",
        "sale_price",
        "discount_percent",
        "is_featured",
        "is_active",
        "order",
    ]
    # "category__parent" here is the *main* category (a product's own
    # `category` is always a leaf -- see formfield_for_foreignkey below) --
    # picking one in the sidebar scopes the list to just that main category.
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
    fields = [
        "name",
        "category",
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
            # own (Marathon, Cricket, ...). The old `parent__isnull=False`
            # clause here wrongly excluded every standalone top-level
            # category too -- which is where this store's entire real
            # catalog actually lives, making them impossible to pick when
            # adding a new product.
            field.queryset = field.queryset.filter(children__isnull=True)
        return field


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
