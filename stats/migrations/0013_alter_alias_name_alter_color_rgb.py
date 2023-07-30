# Generated by Django 4.1.9 on 2023-06-27 20:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0012_remove_textref_key_textref_key"),
    ]

    operations = [
        migrations.AlterField(
            model_name="alias",
            name="name",
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name="color",
            name="rgb",
            field=models.CharField(max_length=8),
        ),
    ]
