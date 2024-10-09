import json
from pathlib import Path
import regex as re
from pprint import pprint
from django.core.management.base import BaseCommand, CommandError
import pywikibot as pwb
from stats.models import RefType
from stats.wikibot import bot

from IPython.core.debugger import set_trace

DATA_DIR = Path("data")


def save_as_json(data: dict[str, list], path: Path):
    path = Path(DATA_DIR, path)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2)


# Command setup
class Command(BaseCommand):
    """Wiki scraper bot command"""

    help = """
    Command for handling TWI Wiki data extraction.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "data_path",
            type=str,
            help="Path in the file system where any scraped data is saved to disk. \
                This includes category data, Characters, Classes, Skills, Spells etc.",
        )
        parser.add_argument(
            "-a", "--all", action="store_true", help="Scrape all categories"
        )
        parser.add_argument(
            f"--{RefType.CHARACTER}",
            f"--{RefType.CHARACTER}".lower(),
            action="store_true",
            help="Scrape all Characters",
        )
        parser.add_argument(
            f"--{RefType.SKILL}",
            f"--{RefType.SKILL}".lower(),
            action="store_true",
            help="Scrape all [Skills]",
        )
        parser.add_argument(
            f"--{RefType.CLASS}",
            f"--{RefType.CLASS}".lower(),
            action="store_true",
            help="Scrape all [Classes]",
        )
        parser.add_argument(
            f"--{RefType.SPELL}",
            f"--{RefType.SPELL}".lower(),
            action="store_true",
            help="Scrape all [Spells]",
        )
        parser.add_argument(
            f"--{RefType.LOCATION}",
            f"--{RefType.LOCATION}".lower(),
            action="store_true",
            help="Scrape all Locations",
        )
        parser.add_argument(
            f"--{RefType.ITEM}",
            f"--{RefType.ITEM}".lower(),
            action="store_true",
            help="Scrape all Items and [Artifacts]",
        )

    def handle(self, *args, **options):
        """
        Collect wiki pages by category (Characters, Skills, Classes etc.)
        """
        if options.get("all"):
            options[RefType.CHARACTER] = True
            options[RefType.SKILL] = True
            options[RefType.CLASS] = True
            options[RefType.SPELL] = True
            options[RefType.LOCATION] = True
            options[RefType.ITEM] = True

        for k, v in options.items():
            if v:
                match k:
                    case RefType.CHARACTER:
                        chars = pwb.Category(bot.site, "Characters").articles()
                        data = {}
                        for page in chars:
                            char = bot.treat_character(page)
                            if char is not None:
                                data |= char
                        save_as_json(data, Path("characters.json"))
                    case RefType.CLASS:
                        class_list_pages = [
                            page
                            for page in pwb.Category(bot.site, "Classes").articles()
                            if re.match(r"List of Classes[/]", page.title().lstrip())
                        ]
                        data = {}
                        for page in class_list_pages:
                            classes = bot.treat_classes(page)
                            if classes:
                                data |= classes
                        save_as_json(data, Path("classes.json"))
                    case RefType.SKILL:
                        skill_list_pages = [
                            a
                            for a in pwb.Category(bot.site, "Skills").articles()
                            if re.match(r"Skills Effect[/]", a.title().lstrip())
                        ]
                        data = {}
                        for page in skill_list_pages:
                            data |= bot.treat_skills(page)
                        save_as_json(data, Path("skills.json"))
                    case RefType.SPELL:
                        spells_page = pwb.Page(bot.site, "Spells")
                        data = bot.treat_spells(spells_page)
                        save_as_json(data, Path("spells.json"))
                    case RefType.LOCATION:
                        locs = [
                            a
                            for a in pwb.Category(bot.site, "Locations").articles()
                            if not re.match(r".*[/].*", a.title())
                        ]
                        data = {}
                        for page in locs:
                            data |= bot.treat_location(page)
                        save_as_json(data, Path("locations.json"))
                    case RefType.ITEM:
                        artifacts_page = pwb.Page(bot.site, "Artifacts#Artifacts List")
                        data = bot.treat_artifacts(artifacts_page)
                        save_as_json(data, Path("items.json"))
                    case _:
                        pass

        ## TODO: Add integrity check - confirm new items match existing models in the database
        ## otherwise prompt for comparison check
