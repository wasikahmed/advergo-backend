from django.db import models

from apps.catalog.models import Category, Fabric
from apps.core.models import TimeStampedModel


class FabricPriceRule(TimeStampedModel):
    """Base per-piece price for a given fabric -- takes priority over a category rule."""

    fabric = models.OneToOneField(Fabric, on_delete=models.CASCADE, related_name="price_rule")
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.fabric.name} -> {self.price_per_unit}/pc"


class CategoryPriceRule(TimeStampedModel):
    """Fallback base per-piece price used when a quote doesn't specify a fabric."""

    category = models.OneToOneField(Category, on_delete=models.CASCADE, related_name="price_rule")
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.category.name} -> {self.price_per_unit}/pc"


class QuantityDiscountTier(TimeStampedModel):
    """Bulk discount applied once quantity reaches `min_quantity`. Highest matching tier wins."""

    min_quantity = models.PositiveIntegerField(unique=True)
    discount_percent = models.DecimalField(max_digits=4, decimal_places=1)

    class Meta:
        ordering = ["-min_quantity"]

    def __str__(self):
        return f"{self.min_quantity}+ pcs -> {self.discount_percent}% off"
