# Generated by Django 4.2.8 on 2024-01-21 06:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stats", "0032_rename_reftypechapters_reftypechapter"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="reftype",
            index=models.Index(fields=["id", "name"], name="stats_refty_id_ecda81_idx"),
        ),
    ]