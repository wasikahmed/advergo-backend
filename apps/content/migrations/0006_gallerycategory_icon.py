from django.db import migrations, models


def seed_icons(apps, schema_editor):
    GalleryCategory = apps.get_model("content", "GalleryCategory")
    icons = {"factory": "🏭", "clients": "🤝"}
    for slug, icon in icons.items():
        GalleryCategory.objects.filter(slug=slug).update(icon=icon)


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0005_galleryitem_category_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="gallerycategory",
            name="icon",
            field=models.CharField(blank=True, help_text="Emoji shown in the UI.", max_length=8),
        ),
        migrations.RunPython(seed_icons, migrations.RunPython.noop),
    ]
