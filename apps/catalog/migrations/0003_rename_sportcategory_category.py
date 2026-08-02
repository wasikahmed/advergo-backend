from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_sizechartrow"),
        # Force the rename to apply *after* every other app has already created
        # its FK to catalog.sportcategory, so a fresh database (where ordering
        # between unrelated apps isn't otherwise constrained) can't try to
        # create a FK against a table name that's already been renamed away.
        ("quotes", "0002_alter_quoterequest_design_file"),
        ("orders", "0002_alter_order_customer"),
        ("pricing", "0001_initial"),
    ]

    operations = [
        migrations.RenameModel(old_name="SportCategory", new_name="Category"),
        migrations.AlterModelOptions(
            name="category",
            options={"ordering": ["order", "name"], "verbose_name_plural": "categories"},
        ),
    ]
