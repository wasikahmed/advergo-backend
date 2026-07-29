from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class SportCategory(TimeStampedModel):
    """Fixed-ish set (football, cricket, cycling, marathon, corporate...) but kept as
    data, not an enum, so new categories can be added from the admin without a deploy."""

    slug = models.SlugField(primary_key=True, max_length=40)
    name = models.CharField(max_length=80)
    icon = models.CharField(max_length=8, blank=True, help_text="Emoji shown in the UI.")
    description = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "sport categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Fabric(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=120)
    grade = models.CharField(max_length=80, blank=True)
    best_for = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="fabrics/", blank=True, null=True)
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
        SportCategory,
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
    category = models.ForeignKey(SportCategory, on_delete=models.PROTECT, related_name="products")
    price_range = models.CharField(max_length=60, blank=True)
    fabric = models.CharField(
        max_length=150, blank=True, help_text="Free-text fabric label shown on the card."
    )
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    review_count = models.PositiveIntegerField(default=0)
    accent_color = models.CharField(
        max_length=7, default="#eb2127", help_text="Hex color, e.g. #eb2127."
    )
    image = models.ImageField(upload_to="products/", blank=True, null=True)

    is_featured = models.BooleanField(
        default=False, help_text="Shown in the homepage featured-products section."
    )
    is_active = models.BooleanField(default=True, help_text="Unpublish without deleting.")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name
