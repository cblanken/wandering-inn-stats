import abc
from itertools import chain
from pprint import pprint
import regex as re
import pywikibot as pwb
import mwparserfromhell as mwp
import wikitextparser as wtp
from pywikibot.textlib import extract_templates_and_params
from collections import OrderedDict
from stats.models import Chapter, Character
from bs4 import BeautifulSoup


def params_to_dict(params: list[str]) -> dict[str, str]:
    return {x[0]: "".join(x[1:]) for x in [p.split("=") for p in params]}


def parse_into_list(text: str) -> list[str]:
    # Split line breaks <br> and <br/> or newlines '\n'
    items = re.split(r"(?:linebreak|<[\s]*br[\s]*/?>)|(?:newline|[\s]*\n[\s]*)", text)
    items = [mwp.parse(x).strip_code() for x in items if x.strip() != ""]

    return items


class WikiTemplateParser:
    def __init__(self, template_params: list[str]):
        self.params = params_to_dict(template_params)

    @abc.abstractmethod
    def parse(self) -> dict:
        """Parse template-specific data from target wiki template"""
        pass


class CharInfoBoxParser(WikiTemplateParser):
    def parse(self) -> dict | None:
        # Parse first appearance href
        first_href = self.params.get("first appearance") or None
        if first_href is not None:
            first_href_templates = extract_templates_and_params(first_href)
            if first_href_templates:
                first_href_templates[0][1].get("1")
                # TODO wikibot: resolve chapter link template into URL for existing Chapters in DB
            else:
                # No templates found => check for manual links
                first_href_matches = list(
                    re.finditer(r"\[(.*)\]", self.params["first appearance"])
                )
                if first_href_matches:
                    first_href = first_href_matches[0].group(1).split()[0]

        # Parse aliases
        aliases = self.params.get("aliases") or None
        if aliases is not None:
            aliases = parse_into_list(aliases)
        else:
            aliases = []

        # Parse status
        status = self.params.get("status") or None
        if status is not None:
            status_templates = extract_templates_and_params(self.params.get("status"))
            if len(status_templates) > 0:
                status = re.sub(
                    r"<[\s]*br[\s]*/?>", " ", status_templates[0][1].get("1")
                ).strip()
            else:
                soup = BeautifulSoup(self.params.get("status"), "html.parser")
                status = soup.text.strip()

        # Parse species
        species = self.params.get("species") or None
        if species is not None:
            species = mwp.parse(self.params["species"]).strip_code()

        parsed_data = {
            "aliases": aliases,
            "first_href": first_href,
            "species": species,
            "status": status,
        }

        pprint(parsed_data)
        return parsed_data
