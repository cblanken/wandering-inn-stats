# Generated by Django 4.1.9 on 2023-07-09 00:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0014_alter_reftype_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chapter",
            name="word_count",
            field=models.PositiveBigIntegerField(default=0),
        ),
    ]
