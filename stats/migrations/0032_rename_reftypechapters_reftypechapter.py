# Generated by Django 4.2.8 on 2024-01-19 16:13

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("stats", "0031_reftypechapters_remove_textref_key_and_more"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="RefTypeChapters",
            new_name="RefTypeChapter",
        ),
    ]