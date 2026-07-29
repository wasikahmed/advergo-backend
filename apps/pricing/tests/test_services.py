from decimal import Decimal

import pytest

from apps.catalog.models import Fabric, SportCategory
from apps.pricing.models import CategoryPriceRule, FabricPriceRule, QuantityDiscountTier
from apps.pricing.services import DEFAULT_BASE_PRICE, estimate_price

pytestmark = pytest.mark.django_db


def test_falls_back_to_default_price_when_no_rules_exist():
    estimate = estimate_price(fabric=None, category=None, quantity=10)
    expected_low = (DEFAULT_BASE_PRICE * Decimal("0.90")).quantize(Decimal("0.01"))
    assert estimate.unit_price_low == expected_low


def test_fabric_rule_takes_priority_over_category_rule():
    category = SportCategory.objects.create(slug="football", name="Football")
    fabric = Fabric.objects.create(name="Pin Mesh")
    CategoryPriceRule.objects.create(category=category, price_per_unit=Decimal("500.00"))
    FabricPriceRule.objects.create(fabric=fabric, price_per_unit=Decimal("700.00"))

    estimate = estimate_price(fabric=fabric, category=category, quantity=10)
    # unit_price_low = 700 * 0.90 = 630.00
    assert estimate.unit_price_low == Decimal("630.00")


def test_category_rule_used_when_no_fabric_given():
    category = SportCategory.objects.create(slug="cricket", name="Cricket")
    CategoryPriceRule.objects.create(category=category, price_per_unit=Decimal("600.00"))

    estimate = estimate_price(fabric=None, category=category, quantity=10)
    assert estimate.unit_price_low == Decimal("540.00")  # 600 * 0.90


def test_quantity_discount_reduces_unit_price():
    category = SportCategory.objects.create(slug="corporate", name="Corporate")
    CategoryPriceRule.objects.create(category=category, price_per_unit=Decimal("1000.00"))
    QuantityDiscountTier.objects.create(min_quantity=100, discount_percent=Decimal("10.0"))

    small_order = estimate_price(fabric=None, category=category, quantity=10)
    bulk_order = estimate_price(fabric=None, category=category, quantity=150)

    assert bulk_order.discount_percent == Decimal("10.0")
    assert small_order.discount_percent == Decimal("0")
    assert bulk_order.unit_price_low < small_order.unit_price_low


def test_totals_scale_with_quantity():
    estimate = estimate_price(fabric=None, category=None, quantity=20)
    assert estimate.total_low == estimate.unit_price_low * 20
    assert estimate.total_high == estimate.unit_price_high * 20
