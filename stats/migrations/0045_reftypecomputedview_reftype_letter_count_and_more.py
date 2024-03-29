# Generated by Django 5.0.2 on 2024-03-19 21:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stats", "0044_alter_chapter_number_alter_chapter_title"),
    ]

    operations = [
        migrations.CreateModel(
            name="RefTypeComputedView",
            fields=[
                (
                    "ref_type",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        to="stats.reftype",
                    ),
                ),
                ("mentions", models.PositiveIntegerField()),
            ],
            options={
                "db_table": "reftype_computed_view",
                "managed": False,
            },
        ),
        migrations.RunSQL(
            """
            CREATE MATERIALIZED VIEW reftype_computed_view AS
                SELECT type_id AS ref_type, COUNT(*) as mentions
                FROM stats_textref
                GROUP BY type_id;

            """,
            "DROP VIEW reftype_computed_view;",
        ),
        migrations.AddField(
            model_name="reftype",
            name="letter_count",
            field=models.GeneratedField(
                db_persist=True,
                expression=models.Func(
                    "name",
                    arity=1,
                    function="length",
                    output_field=models.IntegerField(),
                ),
                output_field=models.IntegerField(),
            ),
        ),
        migrations.AddField(
            model_name="reftype",
            name="word_count",
            field=models.GeneratedField(
                db_persist=True,
                expression=models.Func(
                    models.Func(
                        models.F("name"),
                        models.Value("\\s+"),
                        function="regexp_split_to_array",
                    ),
                    1,
                    function="array_length",
                ),
                output_field=models.IntegerField(),
            ),
        ),
    ]
