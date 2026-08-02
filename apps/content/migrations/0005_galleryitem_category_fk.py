import django.db.models.deletion
from django.db import migrations, models


def copy_category_to_fk(apps, schema_editor):
    GalleryItem = apps.get_model("content", "GalleryItem")
    for item in GalleryItem.objects.all():
        item.category_fk_id = item.category
        item.save(update_fields=["category_fk"])


def copy_fk_to_category(apps, schema_editor):
    GalleryItem = apps.get_model("content", "GalleryItem")
    for item in GalleryItem.objects.all():
        item.category = item.category_fk_id
        item.save(update_fields=["category"])


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0004_gallerycategory"),
    ]

    operations = [
        migrations.AddField(
            model_name="galleryitem",
            name="category_fk",
            field=models.ForeignKey(
                to="content.gallerycategory",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="gallery_items",
                null=True,
            ),
        ),
        migrations.RunPython(copy_category_to_fk, copy_fk_to_category),
        migrations.RemoveField(model_name="galleryitem", name="category"),
        migrations.RenameField(model_name="galleryitem", old_name="category_fk", new_name="category"),
        migrations.AlterField(
            model_name="galleryitem",
            name="category",
            field=models.ForeignKey(
                to="content.gallerycategory",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="gallery_items",
            ),
        ),
    ]
