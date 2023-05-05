# Generated by Django 4.2 on 2023-05-05 21:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveBigIntegerField()),
                ('title', models.CharField(max_length=50, unique=True)),
                ('summary', models.TextField(default='')),
            ],
        ),
        migrations.CreateModel(
            name='Chapter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveBigIntegerField()),
                ('title', models.CharField(max_length=50)),
                ('is_interlude', models.BooleanField()),
                ('source_url', models.URLField()),
                ('post_date', models.DateField(auto_now=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.book')),
            ],
        ),
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Color',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rgb', models.CharField()),
            ],
        ),
        migrations.CreateModel(
            name='ColorCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Volume',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveIntegerField(unique=True)),
                ('title', models.CharField(max_length=50, unique=True)),
                ('summary', models.TextField(default='')),
            ],
        ),
        migrations.CreateModel(
            name='TextRef',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('line_number', models.PositiveIntegerField()),
                ('start_column', models.PositiveIntegerField()),
                ('end_column', models.PositiveIntegerField()),
                ('context_offset', models.PositiveBigIntegerField(default=50)),
                ('chapter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.chapter')),
            ],
        ),
        migrations.CreateModel(
            name='LevelingToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.CharField(max_length=500)),
                ('faith_based', models.BooleanField(default=False)),
                ('type', models.CharField(choices=[('cl', 'Class'), ('sk', 'Skill'), ('sp', 'Spell'), ('mi', 'Miracle'), ('ob', 'Something Obtained')], max_length=2)),
                ('color', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.color')),
            ],
        ),
        migrations.AddField(
            model_name='color',
            name='color',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.colorcategory'),
        ),
        migrations.AddField(
            model_name='book',
            name='volume',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.volume'),
        ),
    ]
