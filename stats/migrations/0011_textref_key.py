# Generated by Django 4.2.2 on 2023-06-25 22:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0010_chapter_authors_note_word_count_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='textref',
            constraint=models.UniqueConstraint(fields=('text', 'chapter', 'type', 'line_number', 'start_column', 'end_column'), name='key'),
        ),
    ]
