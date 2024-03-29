# Generated by Django 4.2.8 on 2024-01-15 22:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stats", "0029_alter_reftype_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reftype",
            name="name",
            field=models.CharField(max_length=300),
        ),
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
                    ("SG", "System General"),
                    ("IN", "Undecided"),
                ],
                max_length=2,
                null=True,
            ),
        ),
    ]
