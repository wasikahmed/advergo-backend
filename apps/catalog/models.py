from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class Category(TimeStampedModel):
    """Product category (football, cricket, corporate wear, etc.), kept as data,
    not an enum, so new categories can be added from the admin without a deploy."""

    slug = models.SlugField(unique=True, max_length=40)
    name = models.CharField(max_length=80)
    icon = models.CharField(max_length=8, blank=True, help_text="Emoji shown in the UI.")
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Fabric(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=120)
    grade = models.CharField(max_length=80, blank=True)
    best_for = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="advergo/fabrics/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class SizeChartRow(TimeStampedModel):
    """One row (one size label) of the size guide shown on the quote form.
    `category=None` means a general row that applies across all categories;
    set it to give a category its own chart (e.g. corporate polo vs. jersey fit)."""

    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="size_chart_rows",
        help_text="Leave blank for a general chart shown regardless of category.",
    )
    size_label = models.CharField(max_length=10, help_text="e.g. S, M, L, XL, XXL")
    chest_in = models.DecimalField(
        "chest (in)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    length_in = models.DecimalField(
        "length (in)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    shoulder_in = models.DecimalField(
        "shoulder (in)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    sleeve_in = models.DecimalField(
        "sleeve (in)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["category_id", "order"]

    def __str__(self):
        scope = self.category.name if self.category_id else "General"
        return f"{scope} · {self.size_label}"


class Product(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    price_range = models.CharField(max_length=60, blank=True)
    fabric = models.CharField(
        max_length=150, blank=True, help_text="Free-text fabric label shown on the card."
    )
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    review_count = models.PositiveIntegerField(default=0)
    accent_color = models.CharField(
        max_length=7, default="#eb2127", help_text="Hex color, e.g. #eb2127."
    )
    image = models.ImageField(upload_to="advergo/products/", blank=True, null=True)

    is_featured = models.BooleanField(
        default=False, help_text="Shown in the homepage featured-products section."
    )
    is_active = models.BooleanField(default=True, help_text="Unpublish without deleting.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class CategoryFilterOption(TimeStampedModel):
    """
    One selectable filter pill for a category's design catalog (e.g. Polo's
    "Full Sleeve" / "Half Sleeve", or Winter Collection's "Jacket" /
    "Tracksuit" / "Trouser"). A category with no options has no filter bar --
    kept as data (like Category itself) so a new category's whole filter set
    can be defined from the admin with no deploy.
    """

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="filter_options")
    value = models.SlugField(
        max_length=40, help_text="Stable key used in the API/URL, e.g. 'jacket'."
    )
    label = models.CharField(max_length=60, help_text="Shown in the UI, e.g. 'Jacket'.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["category_id", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "value"], name="unique_category_filter_value"
            )
        ]

    def __str__(self):
        return f"{self.category.name} · {self.label}"


def design_upload_path(instance, filename):
    category_slug = instance.category.slug if instance.category_id else "uncategorized"
    filter_value = instance.filter_option.value if instance.filter_option_id else "all"
    return f"advergo/designs/{category_slug}/{filter_value}/{filename}"


class Design(TimeStampedModel, SoftDeleteModel):
    """
    A single browsable design in the design collection (as opposed to
    `Product`, which is a category tile/portfolio entry). Customers pick a
    Design and it carries through to their quote/order -- this is the
    replacement for the Google Drive design folder.
    """

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="designs")
    filter_option = models.ForeignKey(
        CategoryFilterOption,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="designs",
        help_text="Leave blank if the category has no filter options.",
    )
    name = models.CharField(max_length=150, blank=True)
    code = models.CharField(
        max_length=40, blank=True, help_text="Internal reference code shown to staff/customers."
    )
    image = models.ImageField(upload_to=design_upload_path)
    is_active = models.BooleanField(default=True, help_text="Unpublish without deleting.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or self.code or f"Design {self.pk}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.filter_option_id and self.filter_option.category_id != self.category_id:
            raise ValidationError("filter_option must belong to the same category.")
