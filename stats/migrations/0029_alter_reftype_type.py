# Generated by Django 4.2.8 on 2024-01-14 19:10

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stats", "0028_alter_reftype_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reftype",
            name="type",
            field=models.CharField(
                choices=[
                    ("CH", "Character"),
                    ("CL", "Class"),
                    ("CO", "Class Update"),
                    ("CN", "Condition Update"),
                    ("IT", "Items and Artifacts"),
                    ("LO", "Location"),
                    ("MI", "Miracle"),
                    ("MC", "Magical Chat"),
                    ("SK", "Skill"),
                    ("SO", "Skill Update"),
                    ("SP", "Spell"),
                    ("SB", "Spell Update"),
                    ("IN", "Undecided"),
                ],
                max_length=2,
                null=True,
            ),
        ),
    ]
