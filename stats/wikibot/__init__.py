from pprint import pprint
import regex as re
import pywikibot as pwb
import wikitextparser as wtp
from pywikibot.bot import SingleSiteBot
from .parse import (
    ArtifactListParser,
    CharInfoBoxParser,
    ClassesTableParser,
    SkillTableParser,
    SpellTableParser,
)
from pywikibot.textlib import Section


def get_aliases(page: pwb.Page) -> list[str] | None:
    """Parse aliases from page"""
    pass


class TwiBot(SingleSiteBot):
    available_options = {
        "always": True,
        "save": None,
        "text": "This is a test text",
        "summary": "A bot for scraping the TWI wiki for statistical analysis",
    }

    def treat(self, page):
        """Placeholder [treat] method"""
        self.current_page = page
        print(self.current_page.text)

    # RefTypes maintain separate pages for each type
    def treat_character(self, page: pwb.Page) -> dict | None:
        self.current_page = page

        # Find character infobox
        infoboxes = list(
            filter(
                lambda t: re.match(
                    r"^Template:Infobox[\s_]character$", t[0].title().strip()
                ),
                page.templatesWithParams(),
            )
        )
        if infoboxes:
            template, params = infoboxes[0]
            parser = CharInfoBoxParser(params, site=self.site)

            data = parser.parse()
            if data:
                data["page_url"] = page.title(as_url=True)
                return {page.title(): data}
            else:
                print(f"NO DATA FOUND FOR template: {template}, with params: {params}")

        else:
            # TODO
            print("NO CHARACTER INFOBOX FOUND")

    def treat_location(self, page: pwb.Page) -> dict | None:
        self.current_page = page
        return {
            page.title(): {
                "url": page.full_url(),
            }
        }

    # Treat methods for RefTypes that don't maintain separate pages for each entity and instead
    # provide lists or tables on one or several pages. These `treat_*` methods should
    # be plural to indicate that data is returned for multiple entities
    def treat_classes(self, page: pwb.Page) -> dict | None:
        """
        Treat class pages in the format of "List of Classes/XXX" where XXX represents the first
        letter of the classes. These pages should have classes listed in a consistent table format
        """
        self.current_page = page
        try:
            parser = ClassesTableParser(wtp.parse(page.get()).sections[1].tables[0])
            data = parser.parse()
            return data
        except IndexError as e:
            print("Missing sections or table on [Class] list page")
            raise e

    def treat_skills(self, page: pwb.Page):
        """
        Treat skill pages in the format of "Skills Effect/XXX" where XXX represents the first
        letter of the skills. These pages should have skills listed in a consistent table format
        """
        self.current_page = page
        try:
            parser = SkillTableParser(wtp.parse(page.get()).sections[1].tables[0])
            data = parser.parse()
            return data
        except IndexError as e:
            print("Missing sections or table on [Skills] list page")
            raise e

    def treat_spells(self, page: pwb.Page) -> dict | None:
        self.current_page = page
        content = pwb.textlib.extract_sections(
            pwb.Page(self.site, "Spells#List of Spells").text, self.site
        )
        spell_lists: list[Section] = list(
            filter(
                lambda s: re.match(
                    r"[=]+[\s]*List[\s]+[Oo]f[\s]+Spells[\s]*[=]+",
                    s.title.replace("\xa0", " "),
                ),
                content.sections,
            )
        )

        if spell_lists:
            data = {}
            for section in spell_lists:
                try:
                    table = wtp.parse(section.content).tables[0]
                    data |= SpellTableParser(table).parse()
                except IndexError as e:
                    print("Missing table for [Spell] list")
                    raise e

            return data
        else:
            print("No Spell list found.")
            return

    def treat_artifacts(self, page: pwb.Page) -> dict | None:
        self.current_page = page
        content = pwb.textlib.extract_sections(page.text, self.site)
        artifact_sections = filter(
            lambda s: re.match(r"^===\s*[#A-Z]\s*===$", s.title.strip()),
            content.sections,
        )
        data = {}
        try:
            for s in artifact_sections:
                data |= ArtifactListParser(wtp.parse(s.content).get_lists()[0]).parse()
        except IndexError as e:
            print("An Artifact section doesn't have an item list")
            raise e

        return data


# TODO: add handlers to watch for particular page updates
# TODO: Add option to compile changes since last update and only check the changed pages

TWISite = pwb.Site(code="en", fam="twi")
bot = TwiBot(TWISite)
