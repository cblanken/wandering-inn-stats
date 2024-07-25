import abc
from itertools import chain
from functools import reduce
from pprint import pprint
import regex as re
import pywikibot as pwb
from pywikibot.textlib import extract_templates_and_params, replace_links
from pywikibot.site import APISite
import mwparserfromhell as mwp
import wikitextparser as wtp
from bs4 import BeautifulSoup


RE_LINEBREAK = re.compile(r"(?:linebreak|<[\s]*br[\s]*/?>)|(?:newline|[\s]*\n[\s]*)")
RE_PARENS_MATCH = re.compile(r".*(\(.*\)).*")
RE_PARENS_AND_PUNCT_REPLACE = re.compile(r"[\s:]*[(].*[)][\s]*")


def params_to_dict(params: list[str]) -> dict[str, str]:
    return {x[0]: "".join(x[1:]) for x in [p.split("=") for p in params]}


def parse_list(text: str) -> list[str]:
    # Split line breaks <br> and <br/> or newlines '\n'
    lines = re.split(RE_LINEBREAK, text)
    lines = [mwp.parse(x).strip_code() for x in lines if x.strip() != ""]
    return lines


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


def parse_name_field(text: str, wrap_brackets=False) -> dict[str, str] | None:
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
        # Detect any text wrapped in parens '()' which indicates a category or some other
        # context and is not part of the actual name
        if res := RE_PARENS_MATCH.match(text):
            if category := res.group(1)[1:-1]:
                data["category"] = wtp.remove_markup(category)
                # text = re.sub(RE_PARENS_MATCH, "", text)
                # text = text.replace("(" + category + ")", "")
                text = RE_PARENS_AND_PUNCT_REPLACE.sub("", text)

        # Split line breaks <br> and <br/> or newlines '\n'
        lines = re.split(RE_LINEBREAK, text)

        # Strip tags
        lines = [mwp.parse(l).strip_code() for l in lines]

        # Remove any leftover delimiters
        lines = [remove_list_delimiters(x) if "/" in x[:2] else x for x in lines]

        # Chain together names
        names = list(chain.from_iterable([slash_split(l) for l in lines]))

        # Remove wiki code including [[Links]] and empty names
        names = [
            wtp.remove_markup(mwp.parse(n).strip_code()) for n in names if len(n) > 0
        ]

        # Remove brackets
        names = [n.replace("[", "").replace("]", "") for n in names]

        # Wrap names in brackets if needed
        if wrap_brackets:
            names = [f"[{n}]" for n in names]

        try:
            name = names[0]
            data["name"] = name
            if len(names) > 0:
                data["aliases"] = [n for n in names[1:] if n != name]
        except IndexError:
            print(f'No name found for row field: "{text}"')

        return data

    except IndexError:
        print(f'Could not completely parse name or aliases from: "{text}"')


class WikiTemplateParser:
    def __init__(self, template_params: list[str], site: APISite):
        self.params = params_to_dict(template_params)
        self.site = site

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
        # Parse first appearance hyperlinks
        if first_hrefs := self.params.get("first appearance"):
            wikitext = wtp.parse(self.site.expand_text(first_hrefs))
            if ext_links := wikitext.external_links:
                first_hrefs = [l.url for l in ext_links]
        else:
            first_hrefs = None

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
    def __init__(self, table: wtp.Table):
        super().__init__(table)

    @staticmethod
    def parse_row(row: list[str]) -> dict[str] | None:
        parsed_name = parse_name_field(row[0], wrap_brackets=True)
        parsed_row = {"type": row[2], "details": wtp.remove_markup(row[3])}

        if aliases := parsed_name.get("aliases"):
            parsed_row["aliases"] = aliases

        if re.search(r"\s*\.\.\.\s*\]?\s*$", parsed_name.get("name")):
            parsed_row["is_prefix"] = True

        links = [
            wl.title
            for wl in chain.from_iterable([wtp.parse(col).wikilinks for col in row])
        ]

        if links:
            parsed_row["links_to"] = links

        return parsed_row

    def parse(self):
        parsed_data = {}
        for row in self.table.data()[1:]:
            parsed_row = self.parse_row(row)
            name = parse_name_field(row[0], wrap_brackets=True)["name"]
            parsed_data[name] = parsed_row
        return parsed_data


class SkillTableParser(WikiTableParser):
    def __init__(self, table: wtp.Table):
        super().__init__(table)

    @staticmethod
    def parse_row(row: list[str]) -> dict[str] | None:
        parsed_name = parse_name_field(row[0], wrap_brackets=True)
        parsed_row = {}
        if aliases := parsed_name.get("aliases"):
            parsed_row["aliases"] = aliases
        if category := parsed_name.get("category"):
            parsed_row["category"] = replace_br_with_space(category)
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
    def __init__(self, table: wtp.Table):
        super().__init__(table)

    @staticmethod
    def parse_row(row: list[str]) -> dict[str] | None:
        parsed_name = parse_name_field(row[0], wrap_brackets=True)
        parsed_row = {"tier": strip_ref_tags(replace_br_with_space(row[1].strip()))}
        if aliases := parsed_name.get("aliases"):
            parsed_row["aliases"] = aliases
        if category := parsed_name.get("category"):
            parsed_row["category"] = replace_br_with_space(category)
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

        data = {"name": name}
        if aliases:
            data["aliases"] = aliases

        return data

    def parse(self) -> dict | None:
        parsed_data = {}
        for item in self.wikilist.items:
            parsed_row = parse_name_field(item)

            name = parsed_row.get("name")
            parsed_data[name] = {}

            if aliases := parsed_row.get("aliases"):
                parsed_data[name]["aliases"] = aliases

            # TODO wikibot: expand links for more data on artifacts with their own pages
        return parsed_data
