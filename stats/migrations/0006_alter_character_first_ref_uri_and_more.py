# Generated by Django 4.2.2 on 2023-06-08 14:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0005_alter_character_species_alter_character_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='character',
            name='first_ref_uri',
            field=models.URLField(null=True),
        ),
        migrations.AlterField(
            model_name='character',
            name='wiki_uri',
            field=models.URLField(null=True),
        ),
    ]
