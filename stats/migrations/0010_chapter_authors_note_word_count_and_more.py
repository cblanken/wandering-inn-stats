# Generated by Django 4.2.2 on 2023-06-23 12:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0009_alter_character_species_alter_character_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="chapter",
            name="authors_note_word_count",
            field=models.PositiveBigIntegerField(default=0),
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
                    ("HE", "Half-Elf"),
                    ("HG", "Half-Gazer"),
                    ("HT", "Half-Troll"),
                    ("HR", "Harpy"),
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
                    ("UC", "Unicorn"),
                    ("VA", "Vampire"),
                    ("WV", "Wyvern"),
                    ("WY", "Wyrm"),
                    ("UK", "Unknown"),
                ],
                max_length=2,
                null=True,
            ),
        ),
    ]
