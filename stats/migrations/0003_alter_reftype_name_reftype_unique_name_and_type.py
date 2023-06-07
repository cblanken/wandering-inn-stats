# Generated by Django 4.2.2 on 2023-06-07 00:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0002_textref_color'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reftype',
            name='name',
            field=models.CharField(max_length=120),
        ),
        migrations.AddConstraint(
            model_name='reftype',
            constraint=models.UniqueConstraint(fields=('name', 'type'), name='unique_name_and_type'),
        ),
    ]