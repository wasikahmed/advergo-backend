from django.db import migrations, models


def backfill_kind(apps, schema_editor):
    Achievement = apps.get_model("content", "Achievement")
    Achievement.objects.update(kind="document")


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0006_gallerycategory_icon"),
    ]

    operations = [
        migrations.AddField(
            model_name="achievement",
            name="kind",
            field=models.CharField(
                choices=[("document", "Legal document"), ("award", "Award")],
                default="document",
                max_length=10,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_kind, migrations.RunPython.noop),
        migrations.AddField(
            model_name="achievement",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="achievements/"),
        ),
        migrations.RemoveField(
            model_name="achievement",
            name="icon",
        ),
    ]
