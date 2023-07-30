# Generated by Django 4.2.2 on 2023-06-08 02:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0003_alter_reftype_name_reftype_unique_name_and_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="Character",
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
                ("first_ref_uri", models.URLField()),
                ("wiki_uri", models.URLField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("AL", "Alive"),
                            ("DE", "Deceased"),
                            ("UD", "Undead"),
                            ("UN", "Unknown"),
                        ],
                        max_length=2,
                    ),
                ),
                (
                    "species",
                    models.CharField(
                        choices=[
                            ("AG", "Agelum"),
                            ("AN", "Antinium"),
                            ("BK", "Beastkin"),
                            ("CT", "Centaur"),
                            ("CY", "Cyclops"),
                            ("DE", "Demon"),
                            ("DG", "Dragon"),
                            ("DP", "Drowned People"),
                            ("DR", "Drake"),
                            ("DU", "Dullahan"),
                            ("DY", "Dryad"),
                            ("EL", "Elf"),
                            ("FA", "Fae"),
                            ("FR", "Fraerling"),
                            ("GA", "Gazer"),
                            ("GB", "Goblin"),
                            ("GM", "Golem"),
                            ("GO", "God"),
                            ("GR", "Garuda"),
                            ("HA", "Halfling"),
                            ("HE", "Half-Elf"),
                            ("HR", "Harpy"),
                            ("HT", "Half-Troll"),
                            ("HU", "Human"),
                            ("KE", "Kelpies"),
                            ("KI", "Kitsune"),
                            ("LF", "Lizardfolk"),
                            ("LG", "Lizardfolk - Gorgon"),
                            ("LI", "Lizardfolk - Indishei"),
                            ("LL", "Lizardfolk - Lamia"),
                            ("LM", "Lizardfolk - Medusa"),
                            ("LN", "Lizardfolk - Naga"),
                            ("LQ", "Lizardfolk - Quexal"),
                            ("LS", "Lizardfolk - Scylla"),
                            ("LS", "Lizardfolk - Star Lamia"),
                            ("LT", "Lizardfolk - Tasgiel"),
                            ("LU", "Lucifen"),
                            ("ME", "Merfolk"),
                            ("MI", "Minotaur"),
                            ("OG", "Ogre"),
                            ("PH", "Phoenix"),
                            ("SE", "Selphid"),
                            ("SF", "Spiderfolk"),
                            ("SL", "Sariant Lamb"),
                            ("SP", "String People"),
                            ("TI", "Titan"),
                            ("TL", "Troll"),
                            ("TR", "Treant"),
                            ("UD", "Undead"),
                            ("UN", "Unicorn"),
                            ("VA", "Vampire"),
                            ("WV", "Wyvern"),
                            ("WY", "Wyrm"),
                        ],
                        max_length=2,
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
