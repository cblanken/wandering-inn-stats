# Generated by Django 4.1.12 on 2023-11-14 16:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0018_alter_chapter_options_alter_textref_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Spell",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("wiki_uri", models.URLField(null=True)),
                (
                    "first_chapter_ref",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="stats.chapter",
                    ),
                ),
                (
                    "ref_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="stats.reftype"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Skill",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("wiki_uri", models.URLField(null=True)),
                (
                    "first_chapter_ref",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="stats.chapter",
                    ),
                ),
                (
                    "ref_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="stats.reftype"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Location",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("wiki_uri", models.URLField(null=True)),
                (
                    "first_chapter_ref",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="stats.chapter",
                    ),
                ),
                (
                    "ref_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="stats.reftype"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Item",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("wiki_uri", models.URLField(null=True)),
                (
                    "first_chapter_ref",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="stats.chapter",
                    ),
                ),
                (
                    "ref_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="stats.reftype"
                    ),
                ),
            ],
        ),
    ]
