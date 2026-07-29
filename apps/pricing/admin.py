from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import CategoryPriceRule, FabricPriceRule, QuantityDiscountTier


@admin.register(FabricPriceRule)
class FabricPriceRuleAdmin(ModelAdmin):
    list_display = ["fabric", "price_per_unit"]
    autocomplete_fields = ["fabric"]


@admin.register(CategoryPriceRule)
class CategoryPriceRuleAdmin(ModelAdmin):
    list_display = ["category", "price_per_unit"]
    autocomplete_fields = ["category"]


@admin.register(QuantityDiscountTier)
class QuantityDiscountTierAdmin(ModelAdmin):
    list_display = ["min_quantity", "discount_percent"]
    ordering = ["-min_quantity"]
