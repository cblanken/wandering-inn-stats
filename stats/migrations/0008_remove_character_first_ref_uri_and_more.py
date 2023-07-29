# Generated by Django 4.2.2 on 2023-06-14 02:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0007_alter_alias_options_alter_book_title_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="character",
            name="first_ref_uri",
        ),
        migrations.AddField(
            model_name="character",
            name="first_chapter_ref",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="stats.chapter",
            ),
        ),
        migrations.AlterField(
            model_name="character",
            name="species",
            field=models.CharField(
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
                    ("HE", "HalfElf-"),
                    ("HR", "Harpy"),
                    ("HT", "HalfTroll-"),
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
                null=True,
            ),
        ),
    ]
