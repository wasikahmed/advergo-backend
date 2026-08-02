from django.db import migrations, models


def seed_gallery_categories(apps, schema_editor):
    GalleryCategory = apps.get_model("content", "GalleryCategory")
    GalleryCategory.objects.get_or_create(
        slug="factory", defaults={"name": "Factory", "order": 0}
    )
    GalleryCategory.objects.get_or_create(
        slug="clients", defaults={"name": "Clients", "order": 1}
    )


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0003_bankaccount_mobilebankingagent_officialdocument_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="GalleryCategory",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.SlugField(max_length=40, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=80)),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name_plural": "gallery categories",
                "ordering": ["order", "name"],
            },
        ),
        migrations.RunPython(seed_gallery_categories, migrations.RunPython.noop),
    ]
