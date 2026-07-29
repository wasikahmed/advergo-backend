from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .models import CategoryPriceRule, FabricPriceRule, QuantityDiscountTier

# Used only when neither the fabric nor the category has a configured rule yet,
# so the estimator never hard-fails while the admin is still filling in real rates.
DEFAULT_BASE_PRICE = Decimal("450.00")

# The estimate is deliberately a range, not a fixed number: final pricing depends
# on design complexity, print type, etc. that only a human review can pin down.
# This matches the spec -- an indicative price up front, confirmed by staff after.
LOW_VARIANCE = Decimal("0.90")
HIGH_VARIANCE = Decimal("1.15")

TWO_PLACES = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def get_base_unit_price(*, fabric=None, category=None) -> Decimal:
    if fabric is not None:
        rule = FabricPriceRule.objects.filter(fabric=fabric).first()
        if rule:
            return rule.price_per_unit
    if category is not None:
        rule = CategoryPriceRule.objects.filter(category=category).first()
        if rule:
            return rule.price_per_unit
    return DEFAULT_BASE_PRICE


def get_quantity_discount_percent(quantity: int) -> Decimal:
    tier = QuantityDiscountTier.objects.filter(min_quantity__lte=quantity).first()
    return tier.discount_percent if tier else Decimal("0")


@dataclass
class PriceEstimate:
    unit_price_low: Decimal
    unit_price_high: Decimal
    total_low: Decimal
    total_high: Decimal
    discount_percent: Decimal


def estimate_price(*, fabric=None, category=None, quantity: int) -> PriceEstimate:
    base = get_base_unit_price(fabric=fabric, category=category)
    discount = get_quantity_discount_percent(quantity)
    unit_price = base * (Decimal("1") - discount / Decimal("100"))

    unit_low = _round(unit_price * LOW_VARIANCE)
    unit_high = _round(unit_price * HIGH_VARIANCE)

    return PriceEstimate(
        unit_price_low=unit_low,
        unit_price_high=unit_high,
        total_low=_round(unit_low * quantity),
        total_high=_round(unit_high * quantity),
        discount_percent=discount,
    )
