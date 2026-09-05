from django.db import migrations


def backfill_product_type(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    # Mirrors the heuristic the frontend used before this field existed:
    # no sale price and no price_range text means it was being displayed
    # as a made-to-order showcase example, not a priced ready product.
    Product.objects.filter(sale_price__isnull=True, price_range="").update(
        product_type="showcase"
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_readyproduct_showcaseproduct_product_age_group_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_product_type, noop_reverse),
    ]
