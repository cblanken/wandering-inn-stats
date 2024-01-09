# Generated by Django 4.2.8 on 2024-01-09 20:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stats", "0020_alter_character_species"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="reftype",
            name="is_divine",
        ),
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
                    ("UK", "Doesn't fit an existing category"),
                ],
                max_length=2,
                null=True,
            ),
        ),
    ]
