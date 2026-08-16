from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


def category_image_upload_path(instance, filename):
    return f"advergo/categories/{instance.slug}/{filename}"


class Category(TimeStampedModel):
    """
    Product category (football, cricket, corporate wear, etc.), kept as data,
    not an enum, so new categories can be added from the admin without a
    deploy. Self-referential: a category with children (e.g. Polo -> Full
    Sleeve / Half Sleeve) is a browsable parent whose children are real
    subcategories -- own slug, own image, own page -- not just a filter
    pill. A category with no children is a leaf on its own.
    """

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        help_text="Leave blank for a top-level category.",
    )
    slug = models.SlugField(unique=True, max_length=40)
    name = models.CharField(max_length=80)
    image = models.ImageField(upload_to=category_image_upload_path, blank=True, null=True)
    description = models.CharField(max_length=200, blank=True)
    is_featured = models.BooleanField(
        default=False,
        help_text="Shown on the homepage. Every category is listed on /categories regardless.",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.parent.name} · {self.name}" if self.parent_id else self.name


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


def design_upload_path(instance, filename):
    category_slug = instance.category.slug if instance.category_id else "uncategorized"
    return f"advergo/designs/{category_slug}/{filename}"


class Design(TimeStampedModel, SoftDeleteModel):
    """
    A single browsable design in the design collection (as opposed to
    `Product`, which is a category tile/portfolio entry). Customers pick a
    Design and it carries through to their quote/order -- this is the
    replacement for the Google Drive design folder. `category` points at
    whichever node the design actually belongs to -- the subcategory leaf
    (e.g. Polo -> Full Sleeve) when one exists, otherwise the top-level
    category itself.
    """

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="designs")
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
