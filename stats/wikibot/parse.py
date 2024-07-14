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


RE_LINEBREAK = re.compile(r"(?:linebreak|<[\s]*br[\s]*/?>)|(?:newline|[\s]*\n[\s]*)")
RE_PARENS_MATCH = re.compile(r".*(\(.*\)).*")


def params_to_dict(params: list[str]) -> dict[str, str]:
    return {x[0]: "".join(x[1:]) for x in [p.split("=") for p in params]}


def parse_list(text: str) -> list[str]:
    # Split line breaks <br> and <br/> or newlines '\n'
    lines = re.split(RE_LINEBREAK, text)
    lines = [mwp.parse(x).strip_code() for x in lines if x.strip() != ""]
    return lines


def slash_split(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"[\s]/[\s]", text)]


def remove_list_delimiters(s: str):
    return s.replace("/", "").strip()


def parse_name_field(text: str) -> dict[str, str] | None:
    """
    Parse name field from tables and split aliases and categories
    Returns data in the form of:
    ```
    {
        name: "name",
        aliases: ["alias1", "alias2", ...],
        category: "category",
    }
    ```
    """

    data = {}
    try:
        # Remove any items wrapped in parens '()' which indicate a category
        res = RE_PARENS_MATCH.match(text)
        data["category"] = res.group(1)[1:-1] if res else None

        # Split line breaks <br> and <br/> or newlines '\n'
        # lines = RE_LINEBREAK.split(r"(?:linebreak|<[\s]*br[\s]*/?>)|(?:newline|[\s]*\n[\s]*)", text)
        lines = re.split(RE_LINEBREAK, text)
        lines = [mwp.parse(x).strip_code() for x in lines if x.strip() != ""]
        data["name"] = lines[0]

        # Remove any delimiters
        lines = [remove_list_delimiters(x) if "/" in x[:2] else x for x in lines]

        # Remove any items wrapped in parens '()' which indicate a category
        data["aliases"] = []
        for line in lines[1:]:
            if not (line[0] == "(" and line[-1] == ")"):
                data["aliases"].append(line)

        return data

    except IndexError:
        print(f'Could not completely parse name or aliases from: "{text}"')


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

    @staticmethod
    def parse_row(row: list[str]):
        """Parse single wikitable row"""
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
            aliases = parse_list(aliases)
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

    @staticmethod
    def parse_row(row: list[str]) -> dict[str] | None:
        names = [x for x in slash_split(row[0]) if x.strip() != ""]
        return {
            "name": names[0],
            "aliases": names[1:] if len(names) > 1 else [],
        }

    def parse(self):
        parsed_data = {}
        for row in self.table.data()[1:]:
            parsed_row = self.parse_row(row)
            name = parsed_row.get("name")
            parsed_data[name] = parsed_row
        return parsed_data


class SkillTableParser(WikiTableParser):
    def __init__(self, table: wtp.Table):
        super().__init__(table)

    @staticmethod
    def parse_row(row: list[str]) -> dict[str] | None:
        parsed_name = parse_name_field(row[0])
        return {
            "name": parsed_name.get("name"),
            "aliases": parsed_name.get("aliases"),
            "category": parsed_name.get("category"),
            "effect": row[1].strip(),
        }

    def parse(self) -> dict | None:
        parsed_data = {}
        for row in self.table.data()[1:]:
            parsed_row = self.parse_row(row)
            name = parsed_row.get("name")
            parsed_data[name] = parsed_row
        return parsed_data


class SpellTableParser(WikiTableParser):
    def __init__(self, table: wtp.Table):
        super().__init__(table)

    @staticmethod
    def parse_row(row: list[str]) -> dict[str] | None:
        parsed_name = parse_name_field(row[0])
        return {
            "aliases": parsed_name.get("aliases"),
            "category": parsed_name.get("category"),
            "tier": row[1].strip(),
            "effect": row[2].strip(),
        }

    def parse(self) -> dict | None:
        parsed_data = {}
        for row in self.table.data()[1:]:
            primary_name = parse_name_field(row[0])[0]
            parsed_data[primary_name] = self.parse_row(row)
        return parsed_data


class ArtifactListParser(WikiListParser):
    @staticmethod
    def parse_row(row: list[str]) -> dict[str] | None:
        wl = wtp.parse(row[0]).wikilinks
        if wl:
            name = wl[0].title
        else:
            name = row[0]

        tags = wtp.parse(row[0]).get_tags("ref")
        if tags:
            ref_text = tags[0].plain_text()
            name = wtp.remove_markup(name)
            name = name.replace(ref_text, "")

        name, *aliases = slash_split(name)
        return {
            "name": name,
            "aliases": aliases,
        }

    def parse(self) -> dict | None:
        parsed_data = {}
        for item in self.wikilist.items:
            parsed_name = self.parse_row([item])
            parsed_data[parsed_name.get("name")] = {
                "aliases": parsed_name.get("aliases")
                # TODO wikibot: expand links for more data on artifacts with their own pages
            }
        return parsed_data
