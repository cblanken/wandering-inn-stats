import abc
from itertools import chain
from typing import Any
import regex as re
from pywikibot.textlib import extract_templates_and_params
from pywikibot.site import APISite
import mwparserfromhell as mwp
import wikitextparser as wtp
from bs4 import BeautifulSoup


class ParseError(RuntimeError):
    """A Wikibot parsing error occurred"""


RE_LINEBREAK = re.compile(r"(?:linebreak|<[\s]*br[\s]*/?>)|(?:newline|[\s]*\n[\s]*)")
RE_PARENS_CATEGORY_MATCH_START = re.compile(r".*(\(.*\))\s*\]?$")
RE_PARENS_CATEGORY_MATCH_END = re.compile(r"^\[?[\s]*(\(.*\)).*")
RE_PARENS_AND_PUNCT_REPLACE = re.compile(r"[\s[:punct:]]*[(].*[)][\s[:punct:]]*")
RE_ALL_WRAPPED_PARENS = re.compile(r"^\s*[(].*[)]\s*$")


def params_to_dict(params: list[str]) -> dict[str, str]:
    return {x[0]: "".join(x[1:]) for x in [p.split("=") for p in params]}


def parse_list(text: str) -> list[str]:
    # Split line breaks <br> and <br/> or newlines '\n'
    lines = re.split(RE_LINEBREAK, text)
    lines = [parse_name_field(x) for x in lines if x.strip() != ""]
    return [line["name"] for line in lines]


def slash_split(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"\s?/\s?", text)]


def remove_list_delimiters(s: str) -> str:
    return s.replace("/", "").strip()


def strip_ref_tags(text: str) -> str:
    ref_tags = [t for t in wtp.parse(text).get_tags() if t.name == "ref"]

    # Remove <ref> tags
    for t in ref_tags:
        text = text.replace(str(t), "")

    return text


def replace_br_with_space(text: str) -> str:
    return re.sub(re.compile(r"<br[ ]?/>"), " ", text)


def parse_name_field(text: str, wrap_brackets: bool = False) -> dict[str, str]:
    """
    Parse name field from tables and lists. Parse out aliases, categories and citations.
    Returns data in the form of:
    ```
    {
        name: "Name",
        aliases: ["Alias1", "Alias2", ...],
        category: "Category",
        citations: ["Chapter A", "Chapter B", ...],
    }
    ```
    """
    data = {}
    data.setdefault("citations", [])
    data.setdefault("categories", [])
    parsed_text = text
    try:
        # Parse citations
        tags = wtp.parse(parsed_text).get_tags()
        for tag in tags:
            if tag.name == "ref":
                data["citations"].append(tag.plain_text())
                parsed_text = parsed_text.replace(str(tag), "")

        # Split line breaks <br> and <br/> or newlines '\n'
        lines = re.split(RE_LINEBREAK, parsed_text)

        # Strip tags
        lines = [mwp.parse(line).strip_code() for line in lines]

        # Remove any leftover delimiters
        lines = [remove_list_delimiters(x) if "/" in x[:2] else x for x in lines]

        # Chain together names
        names = list(chain.from_iterable([slash_split(line) for line in lines]))

        not_alias_indexes = []
        for i, n in enumerate(names):
            # Detect any text wrapped in parens '()' which indicates a category or some other
            # context and is not part of the actual name
            if RE_ALL_WRAPPED_PARENS.match(n):
                data["categories"].append(wtp.remove_markup(n[1:-1]))
                not_alias_indexes.insert(0, i)
            else:
                re_category = RE_PARENS_CATEGORY_MATCH_END.match(n)
                if re_category is None:
                    re_category = RE_PARENS_CATEGORY_MATCH_START.match(n)
                if re_category and (category := re_category.group(1)[1:-1]):
                    data["categories"].append(wtp.remove_markup(category))
                    names[i] = RE_PARENS_AND_PUNCT_REPLACE.sub("", n)

        # Delete any invalid aliases (e.g. categories split by linebreaks)
        for i in not_alias_indexes:
            del names[i]

        # Remove wiki code including [[Links]] and empty names
        names = [wtp.remove_markup(mwp.parse(n).strip_code()) for n in names if len(n) > 0]

        # Process brackets to catch inconsistent bracket splitting
        # Remove brackets
        names = [n.replace("[", "").replace("]", "") for n in names]
        # Wrap names in brackets if needed
        if wrap_brackets:
            names = [f"[{n}]" for n in names]

        # Normalize apostrophes (') to \u2019
        names = [n.replace("'", "\u2019") for n in names]

        try:
            name = names[0].strip()
            data["name"] = name
            if len(names) > 0:
                data["aliases"] = [n for n in names[1:] if n != name]
        except IndexError:
            print(f'No name found for row field: "{parsed_text}"')

        return data

    except IndexError as e:
        raise ParseError(f'Names and/or aliases could not be parsed from "{text}"') from e


class WikiTemplateParser:
    def __init__(self, template_params: list[str], site: APISite) -> None:
        self.params = params_to_dict(template_params)
        self.site = site

    @abc.abstractmethod
    def parse(self) -> dict:
        """Parse template-specific data from target wiki template"""


class WikiTableParser:
    def __init__(self, table: wtp.Table) -> None:
        self.table = table

    def parse(self) -> None:
        """Parse a wikitable"""

    @staticmethod
    def parse_row(row: list[str]) -> None:
        """Parse single wikitable row"""


class WikiListParser:
    def __init__(self, wikilist: wtp.WikiList) -> None:
        self.wikilist = wikilist

    def parse(self) -> None:
        """Parse a wikilist"""


class CharInfoBoxParser(WikiTemplateParser):
    def parse(self) -> dict:
        # Parse first appearance hyperlinks
        if first_hrefs := self.params.get("first appearance"):
            wikitext = wtp.parse(self.site.expand_text(first_hrefs))
            if ext_links := wikitext.external_links:
                first_hrefs = [link.url for link in ext_links]
        else:
            first_hrefs = None

        # Parse aliases
        aliases = self.params.get("aliases") or None
        aliases = parse_list(aliases) if aliases is not None else []

        # Parse status
        status = self.params.get("status") or None
        if status is not None:
            status_templates = extract_templates_and_params(self.params.get("status"))
            if len(status_templates) > 0:
                status = re.sub(r"<[\s]*br[\s]*/?>", " ", status_templates[0][1].get("1")).strip()
            else:
                soup = BeautifulSoup(self.params.get("status"), "html.parser")
                status = soup.text.strip()

        # Parse species
        species = self.params.get("species") or None
        if species is not None:
            species = mwp.parse(self.params["species"]).strip_code()

        parsed_data = {}

        if aliases:
            parsed_data["aliases"] = aliases

        if first_hrefs:
            parsed_data["first_hrefs"] = first_hrefs

        if species:
            parsed_data["species"] = species

        if status:
            parsed_data["status"] = status

        return parsed_data


class ClassesTableParser(WikiTableParser):
    def __init__(self, table: wtp.Table) -> None:
        super().__init__(table)

    @staticmethod
    def parse_row(row: list[str]) -> dict[str] | None:
        parsed_name = parse_name_field(row[0], wrap_brackets=True)
        parsed_row = {"type": row[2], "details": wtp.remove_markup(row[3])}

        if aliases := parsed_name.get("aliases"):
            parsed_row["aliases"] = aliases

        if re.search(r"\s*\.\.\.\s*\]?\s*$", parsed_name.get("name")):
            parsed_row["is_prefix"] = True

        links = [wl.title for wl in chain.from_iterable([wtp.parse(col).wikilinks for col in row])]

        if links:
            parsed_row["links_to"] = links

        return parsed_row

    def parse(self) -> dict[str, Any]:
        parsed_data = {}
        for row in self.table.data()[1:]:
            parsed_row = self.parse_row(row)
            name = parse_name_field(row[0], wrap_brackets=True)["name"]
            parsed_data[name] = parsed_row
        return parsed_data


class SkillTableParser(WikiTableParser):
    def __init__(self, table: wtp.Table) -> None:
        super().__init__(table)

    @staticmethod
    def parse_row(row: list[str]) -> dict[str, Any] | None:
        parsed_name = parse_name_field(row[0], wrap_brackets=True)
        parsed_row = {}
        if aliases := parsed_name.get("aliases"):
            parsed_row["aliases"] = aliases
        if categories := parsed_name.get("categories"):
            # parsed_row["categories"] = replace_br_with_space(categories)
            parsed_row["categories"] = categories
        if effect := strip_ref_tags(row[1].strip()):
            parsed_row["effect"] = replace_br_with_space(effect)

        return parsed_row

    def parse(self) -> dict | None:
        parsed_data = {}
        for row in self.table.data()[1:]:
            name = parse_name_field(row[0], wrap_brackets=True)["name"]
            parsed_data[name] = self.parse_row(row)
        return parsed_data


class SpellTableParser(WikiTableParser):
    def __init__(self, table: wtp.Table) -> None:
        super().__init__(table)

    @staticmethod
    def parse_row(row: list[str]) -> dict[str, str | list[str]]:
        parsed_name = parse_name_field(row[0], wrap_brackets=True)
        parsed_row: dict[str, str | list[str]] = {"tier": strip_ref_tags(replace_br_with_space(row[1].strip()))}
        if aliases := parsed_name.get("aliases"):
            parsed_row["aliases"] = aliases
        if categories := parsed_name.get("categories"):
            parsed_row["categories"] = categories
        if effect := strip_ref_tags(row[2].strip()):
            parsed_row["effect"] = replace_br_with_space(effect)

        return parsed_row

    def parse(self) -> dict | None:
        parsed_data = {}
        for row in self.table.data()[1:]:
            name = parse_name_field(row[0], wrap_brackets=True)["name"]
            parsed_data[name] = self.parse_row(row)
        return parsed_data


class ArtifactListParser(WikiListParser):
    def parse(self) -> dict:
        parsed_data = {}
        for item in self.wikilist.items:
            parsed_name = parse_name_field(item)
            name = parsed_name.get("name")
            parsed_data[name] = {}

            if aliases := parsed_name.get("aliases"):
                parsed_data[name]["aliases"] = aliases

            if citations := parsed_name.get("citations"):
                parsed_data[name]["citations"] = citations

            # TODO wikibot: expand links for more data on artifacts with their own pages
        return parsed_data
