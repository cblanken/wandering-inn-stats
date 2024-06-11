from django.core.management.base import BaseCommand, CommandError
import pywikibot as pwb
from stats.models import RefType
from stats.wikibot import bot

# import IPython; IPython.embed()


# Command setup
class Command(BaseCommand):
    """Wiki scraper bot command"""

    help = "Update database from chapter source HTML and other metadata files"

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
        # Collect wiki pages by category (Characters, Skills, Classes etc.)
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
                        for page in chars:
                            bot.treat_character(page)
                    case RefType.CLASS:
                        classes = pwb.Category(bot.site, "Classes").articles()
                        for page in classes:
                            bot.treat_class(page)
                    case RefType.SKILL:
                        skills_page = pwb.Page(
                            bot.site, "Skills#List of Skills - Alphabetical Order"
                        )
                        bot.treat_skills(skills_page)
                    case RefType.SPELL:
                        spells_page = pwb.Page(bot.site, "Spells")
                        bot.treat_spells(spells_page)
                    case RefType.LOCATION:
                        locs = pwb.Category(bot.site, "Locations").articles()
                        for page in locs:
                            bot.treat_location(page)
                    case RefType.ITEM:
                        artifacts_page = pwb.Page(bot.site, "Artifacts#Artifacts List")
                        bot.treat_items(artifacts_page)
                    case _:
                        pass

        ## Download individual pages as needed
        ## Parse downloaded data
        ## Process into structured data (JSON)
        ## Export data to another module or process into DB directly

        ## TODO: Add integrity check - confirm new items match existing models in the database
        ## otherwise prompt for comparison check
