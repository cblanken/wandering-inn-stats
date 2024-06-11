from pprint import pprint
import regex as re
import pywikibot as pwb
from pywikibot.bot import SingleSiteBot
from .parse import CharInfoBoxParser


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
    def treat_character(self, page: pwb.Page):
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
            print(params)
            name = page.title()
            parser = CharInfoBoxParser(params)

            data = parser.parse()
            if data:
                data["wiki_href"] = page.full_url()
                data["name"] = page.title()
            else:
                print(f"NO DATA FOUND FOR template: {template}, with params: {params}")

        else:
            # TODO
            print("NO CHARACTER INFOBOX FOUND")

    def treat_location(self, page: pwb.Page):
        self.current_page = page

    # RefTypes that don't maintain separate pages for each type and instead
    # provide lists on one or several pages
    def treat_classes(self, page: pwb.Page):
        self.current_page = page
        content = pwb.textlib.extract_sections(page.text, self.site)
        alpha_class_sections = [
            (s.title, s.content[:20])
            for s in list(
                filter(
                    lambda s: re.match(r"^===\s*[#A-Z]\s*===$", s.title.strip()),
                    content.sections,
                )
            )
        ]
        pprint(alpha_class_sections)

    def treat_skills(self, page: pwb.Page):
        self.current_page = page
        content = pwb.textlib.extract_sections(page.text, self.site)
        alpha_skill_sections = [
            (s.title, s.content[:20])
            for s in list(
                filter(
                    lambda s: re.match(r"^===\s*[#A-Z]\s*===$", s.title.strip()),
                    content.sections,
                )
            )
        ]
        pprint(alpha_skill_sections)

    def treat_spells(self, page: pwb.Page):
        self.current_page = page
        content = pwb.textlib.extract_sections(
            pwb.Page(self.site, "Spells#List of Spells").text, self.site
        )
        spell_list = list(
            filter(
                lambda s: re.match(
                    r"[=]+[\s]*List[\s]+[Oo]f[\s]+Spells[\s]*[=]+",
                    s.title.replace("\xa0", " "),
                ),
                content.sections,
            )
        )

        if spell_list:
            pprint(spell_list[0].title)
        else:
            print("> No Spell list found.")

    def treat_items(self, page: pwb.Page):
        self.current_page = page
        content = pwb.textlib.extract_sections(page.text, self.site)
        item_sections = [
            (s.title, s.content[:20])
            for s in filter(
                lambda s: re.match(r"^===\s*[#A-Z]\s*===$", s.title.strip()),
                content.sections,
            )
        ]
        pprint(item_sections)


# TODO: add handlers to watch for particular page updates
# TODO: Add option to compile changes since last update and only check the changed pages

TWISite = pwb.Site(code="en", fam="twi")
bot = TwiBot(TWISite)
