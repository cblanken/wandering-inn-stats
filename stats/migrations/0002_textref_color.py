# Generated by Django 4.2 on 2023-05-17 15:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="textref",
            name="color",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, to="stats.color"
            ),
        ),
    ]
