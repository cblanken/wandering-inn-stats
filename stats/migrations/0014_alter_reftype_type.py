# Generated by Django 4.1.9 on 2023-07-04 23:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0013_alter_alias_name_alter_color_rgb"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reftype",
            name="type",
            field=models.CharField(
                choices=[
                    ("CH", "Character"),
                    ("CL", "Class"),
                    ("CO", "Class Obtained"),
                    ("IT", "Item"),
                    ("LO", "Location"),
                    ("MI", "Miracle"),
                    ("SK", "Skill"),
                    ("SO", "Skill Obtained"),
                    ("SP", "Spell"),
                    ("SB", "Spell Obtained"),
                ],
                max_length=2,
                null=True,
            ),
        ),
    ]
