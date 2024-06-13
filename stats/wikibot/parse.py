import abc
from itertools import chain
from pprint import pprint
import regex as re
import pywikibot as pwb
import mwparserfromhell as mwp
import wikitextparser as wtp
from pywikibot.textlib import extract_templates_and_params
from bs4 import BeautifulSoup
from IPython.core.debugger import set_trace


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


class WikiTableParser:
    def __init__(self, table: wtp.Table):
        self.table = table

    def parse(self):
        """Parse a wikitable"""
        pass


class WikiListParser:
    def __init__(self, wikilist: wtp.WikiList):
        self.wikilist = wikilist

    def parse(self):
        """Parse a wikilist"""
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

        return parsed_data


class ClassesTableParser(WikiTableParser):
    def __init__(self, table: wtp.Table):
        super().__init__(table)
        self.name_alias_splitter_pattern = re.compile(r"[\s]*[/][\s]*")

    def parse(self):
        parsed_data = {}
        for row in self.table.data()[1:]:
            names = re.split(self.name_alias_splitter_pattern, row[0])
            aliases = names[1:] if len(names) > 1 else None

            primary_name = names[0]
            parsed_data[primary_name] = {
                "aliases": aliases,
                "type": row[2].strip(),
            }
        return parsed_data


class SkillTableParser(WikiTableParser):
    def __init__(self, table: wtp.Table):
        super().__init__(table)
        self.name_alias_splitter_pattern = re.compile(r"[\s]*[/][\s]*")

    def parse(self) -> dict | None:
        parsed_data = {}
        for row in self.table.data()[1:]:
            names = re.split(self.name_alias_splitter_pattern, row[0])
            aliases = names[1:] if len(names) > 1 else None

            primary_name = names[0]
            parsed_data[primary_name] = {
                "aliases": aliases,
                "effect": row[1].strip(),
            }
        return parsed_data


class SpellTableParser(WikiTableParser):
    def __init__(self, table: wtp.Table):
        super().__init__(table)
        self.name_alias_splitter_pattern = re.compile(r"[\s]*[/][\s]*")

    def parse(self) -> dict | None:
        parsed_data = {}
        for row in self.table.data()[1:]:
            # names = re.split(self.name_alias_splitter_pattern, row[0])
            names = parse_into_list(row[0])
            aliases = names[1:] if len(names) > 1 else None

            primary_name = names[0]
            parsed_data[primary_name] = {
                "aliases": aliases,
                "tier": row[1].strip(),
                "effect": row[2].strip(),
            }
        return parsed_data


class ArtifactListParser(WikiListParser):
    def parse(self) -> dict | None:
        parsed_data = {}
        for item in self.wikilist.items:
            parsed_data[item] = {
                # TODO wikibot: expand links for more data on artifacts with their own pages
            }
        return parsed_data
