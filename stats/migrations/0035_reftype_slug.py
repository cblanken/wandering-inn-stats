# Generated by Django 4.2.8 on 2024-02-08 19:10

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stats", "0034_chapter_is_canon_chapter_is_status_update"),
    ]

    operations = [
        migrations.AddField(
            model_name="reftype",
            name="slug",
            field=models.TextField(default=""),
        ),
    ]
