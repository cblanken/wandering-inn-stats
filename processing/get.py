"""Module to download every chapter from the links in the Wandering Inn Table of Contents"""
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from itertools import chain
import hashlib
from sys import stderr
import re
import string
import time
from bs4 import BeautifulSoup, ResultSet, Tag
import requests
import requests.exceptions
from stem import Signal
from stem.control import Controller
from fake_useragent import UserAgent

BASE_URL: str = "https://www.wanderinginn.com"
WIKI_URL: str = "https://thewanderinginn.fandom.com"
# WIKI_URL: str = "https://wiki.wanderinginn.com"


def remove_bracketed_ref_number(s: str) -> str:
    """Remove a square bracketed reference number from a string"""
    splits = [x.split("]") for x in s.split("[")]

    # Filter out reference numbers
    if len(splits) > 1:
        return "".join(list(filter(lambda x: not x.isnumeric(), list(chain(*splits)))))
    else:
        return s


class TorSession:
    """Session object to download webpages via requests
    Also handles cycling Tor connections to prevent IP bans
    """

    def __init__(
        self, proxy_ip: str = "127.0.0.1", proxy_port: int = 9050, max_tries: int = 10
    ):
        print("> Connecting to Tor session...")
        self.__session = requests.session()
        self.__proxy_port = proxy_port
        self.set_tor_proxy(proxy_ip)
        self.__tries = 0  # resets after a sucessful chapter download
        self.__max_tries = max_tries

    def get(self, url, timeout=10) -> requests.Response:
        resp = None
        while self.__tries < self.__max_tries:
            resp = self.__session.get(
                url=url,
                headers={"User-Agent": UserAgent().random},
                allow_redirects=True,
                timeout=timeout,
            )
            if resp.status_code >= 400 and resp.status_code <= 499:
                self.__tries += 1
                self.get_new_tor_circuit()
            else:
                self.__tries = 0
                return resp

        print("Cannot re-attempt download. Too many retries. Must reset to continue.")

    def reset_tries(self):
        self.__tries = 0

    def set_tor_proxy(self, ip: str):
        self.__session.proxies = {
            "http": f"socks5://{ip}:{self.__proxy_port}",
            "https": f"socks5://{ip}:{self.__proxy_port}",
        }

    def get_new_tor_circuit(self, control_port: int = 9051) -> str:
        with Controller.from_port(port=control_port) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            time.sleep(controller.get_newnym_wait())

    def __get_character_by_alpha(self, alpha_char: str) -> dict[str:str]:
        """Get single character name and link to the wiki

        Returns:
            Dictionary of the form:
            {
                character name : url to wiki page,
                ...
            }
        """
        alpha_char = alpha_char.upper()
        if len(alpha_char) != 1 or alpha_char not in string.ascii_uppercase:
            raise ValueError("Invalid alphabetic character")

        char_endpoint = f"{WIKI_URL}/Category:Characters"
        resp = self.get(f"{char_endpoint}?from={alpha_char}")

        soup = BeautifulSoup(resp.text, "html.parser")
        return {
            x["title"]: WIKI_URL + x["href"]
            for x in soup.select(".category-page__member-link")
            if "Category" not in x["title"]
        }

    def __get_all_characters_by_alpha(self) -> dict[dict[str:str]]:
        """Get all characters names and links to the wiki

        Returns:
            Dictionary of the form:
            {
                alphabetic character : {
                    character name : url to wiki page,
                    ...
                },
                ...
            }
        """
        return {c: self.__get_character_by_alpha(c) for c in string.ascii_uppercase}

    def get_all_character_data(self) -> dict[str:dict]:
        print(f"> Getting links to all character wiki pages...")
        chars_by_alpha = self.__get_all_characters_by_alpha()
        data = {}
        for chars in chars_by_alpha.values():
            for char, url in chars.items():
                data[char] = {"wiki_href": url}
                try:
                    print(f"> Downloading character metadata for {char}")
                    wiki_page = self.get(url)
                    soup = BeautifulSoup(wiki_page.text, "html.parser")

                    # TODO: strip out addendums in parentheses of the form: (...)
                    alias_ele = soup.select('.pi-data[data-source="aliases"]')
                    if len(alias_ele) > 0:
                        # Conditional parsing depending on whether <li> tags or <br> are used
                        # to create newlines between aliases
                        alias_lis = alias_ele[0].find_all("li")
                        if len(alias_lis) > 0:
                            aliases = [li.text.strip() for li in alias_lis]
                        else:
                            alias_soup = BeautifulSoup(
                                str(alias_ele[0].select(".pi-data-value")[0])
                                .replace("<br/>", "\n")
                                .replace("<br>", "\n"),
                                "html.parser",
                            )

                            aliases = [
                                remove_bracketed_ref_number(x)
                                for x in alias_soup.text.strip().split("\n")
                            ]
                        data[char]["aliases"] = aliases

                    first_appearance_ele = soup.select(
                        '.pi-data[data-source="first appearance"] a'
                    )
                    if len(first_appearance_ele) > 0:
                        data[char]["first_href"] = first_appearance_ele[0]["href"]

                    status_ele = soup.select('.pi-data[data-source="status"]')
                    if len(status_ele) > 0:
                        data[char]["status"] = (
                            status_ele[0].select(".pi-data-value")[0].text
                        )

                    species_ele = soup.select('.pi-data[data-source="species"]')
                    if len(species_ele) > 0:
                        data[char]["species"] = (
                            species_ele[0].select(".pi-data-value")[0].text
                        )

                except requests.Timeout:
                    print(f"!!! - Unable to download character wiki page: {url}")
                    continue

        return data

    def get_locations_by_alpha(self, alpha_char: str) -> dict[str]:
        """Get single location name and link to the wiki

        Returns:
            Dictionary of the form:
            {
                location name : url to wiki page,
            }
        """
        alpha_char = alpha_char.upper()
        if len(alpha_char) != 1 or alpha_char not in string.ascii_uppercase:
            raise ValueError("Invalid alphabetic character")

        char_endpoint = f"{WIKI_URL}/Category:Locations"
        resp = self.get(f"{char_endpoint}?from={alpha_char}", timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        return {
            x["title"]: WIKI_URL + x["href"]
            for x in soup.select(".category-page__member-link")
            if "Category" not in x["title"]
        }

    def get_all_locations_by_alpha(self) -> dict[dict[str:str]]:
        """Get all location names and links to the wiki

        Returns:
            Dictionary of the form:
            {
                alphabetic character : {
                    location name : url to wiki page,
                },
                ...
            }
        """
        return {c: self.get_locations_by_alpha(c) for c in string.ascii_uppercase}

    def get_class_list(self) -> list[str]:
        list_hrefs = [
            f"{WIKI_URL}/wiki/List_of_Classes/A-L",
            f"{WIKI_URL}/wiki/List_of_Classes/M-Z",
        ]
        soups = [
            BeautifulSoup(self.get(href).text, "html.parser") for href in list_hrefs
        ]

        classes = [
            [
                x.text.strip().replace("[", "").replace("]", "")
                for x in soup.select("table.article-table tr > td:first-of-type")
                if "..." not in x.text.strip()
            ]
            for soup in soups
        ]
        classes = list(chain(*classes))

        for i, c in enumerate(classes):
            if "/" in c:
                split = [x.strip() for x in c.split("/")]
                classes[i] = split[0]
                for extra in split[1:]:
                    classes.append(extra)

        return sorted(classes)

    def get_spell_list(self) -> list[str]:
        # TODO: fix parsing of spell names with nested brackets
        soup = BeautifulSoup(
            self.get(f"{WIKI_URL}/wiki/Spells").text,
            "html.parser",
        )
        spell_elements: ResultSet[Tag] = soup.select(
            "table.article-table tr > td:first-of-type"
        )

        # Split multiple spells/aliases joined by "/"
        spells = []
        pattern = re.compile(r"\[(.*?)\]")
        for i, spell in enumerate(spell_elements):
            spell_parts = list(
                filter(lambda x: not x.isnumeric(), pattern.findall(spell.text))
            )

            if len(spell_parts) == 0:
                spells.append(spell.text.strip())
            else:
                # spell_parts = spell.stripped_strings
                spells.append("|".join(spell_parts))

        return set(sorted(spells))

    def get_skill_list(self) -> list[str]:
        soup = BeautifulSoup(
            self.get(f"{WIKI_URL}/wiki/Skills").text,
            "html.parser",
        )
        skill_elements: ResultSet[Tag] = chain(
            # Parse main list of skills
            soup.select_one("#List_of_Skills_-_Alphabetical_Order").find_all_next(
                "li", recursive=False
            ),
            # Parse colored and fake/imaginary skills
            soup.select(".wikitable tr td:first-of-type"),
        )

        skills = [
            x.text.split("\n")[0].replace("[", "").replace("]", "")
            for x in skill_elements
            if x.text.find("[") != -1
        ]
        for i, skill in enumerate(skills):
            skill_parts = [x.strip() for x in skill.split("/") if x.find("*") == -1]
            if len(skill_parts) > 1:
                skills[i] = "|".join(skill_parts)
            else:
                skills[i] = skill.strip()

        return sorted(set(sorted(skills)))

    def get_miracle_list(self) -> list[str]:
        pass


def parse_chapter(response: requests.Response) -> dict[str]:
    """Parse data from chapter

    Args:
        response: Requests response object holding data from chapter download

    Returns:

    """
    chapter = {}

    soup: BeautifulSoup = BeautifulSoup(response.content, "html.parser")

    # Parse chapter content html from Response object
    result = soup.select_one(".entry-content")
    if result is not None:
        chapter["html"] = str(result)

    # Parse chapter text from Response object
    # Exclude last two lines which usually include (previous and next chapter links)
    content_lines: list[str] = "\n".join(
        [element.get_text() for element in soup.select(".entry-content")]
    ).split("\n")[:-2]

    # Parse chapter plaintext and Author's Note if it exists
    authors_note_re = re.compile(r"Author['|’]s [N|n]ote.*")

    # Determine line index from the end for start of Author's note
    chapter_lines = []
    authors_note_lines = []
    i = 0
    while i < len(content_lines):
        if authors_note_re.match(content_lines[i].strip()):
            # Found start of Author's Note
            empty_line_cnt = 0
            for j, authors_note_line in enumerate(content_lines[i:]):
                if len(authors_note_line.strip()):  # if line is just whitespace
                    empty_line_cnt += 1
                    continue
                if empty_line_cnt > 1:
                    authors_note_lines = content_lines[i : i + j + 2]
                    i += j + 1
                    break

            continue

        chapter_lines.append(content_lines[i])

        i += 1

    # chapter_lines = content_lines[:-authors_note_start_index-1]
    # authors_note_lines = content_lines[-authors_note_start_index-1:]

    chapter["text"] = "\n".join(chapter_lines).strip()
    chapter["authors_note"] = "\n".join(authors_note_lines).strip()

    # Parse chapter metadata from Response object
    soup: BeautifulSoup = BeautifulSoup(response.content, "html.parser")
    try:
        title: str = soup.select(".entry-title")[0].get_text()
        pub_time: str = soup.select("meta[property='article:published_time']")[0].get(
            "content"
        )
        mod_time: str = soup.select("meta[property='article:modified_time']")[0].get(
            "content"
        )
        word_count: str = len(chapter["text"].split())
        authors_note_word_count: str = len(chapter["authors_note"].split())
        dl_time: str = str(datetime.now().astimezone())
        digest: str = hashlib.sha256(chapter["text"].encode("utf-8")).hexdigest()
        chapter["metadata"] = {
            "title": title,
            "pub_time": pub_time,
            "mod_time": mod_time,
            "dl_time": dl_time,
            "url": response.url,
            "word_count": word_count,
            "authors_note_word_count": authors_note_word_count,
            "digest": digest,
        }
    except IndexError as exc:
        print(f"! Couldn't find metadata at {response.url}. Exception: {exc}")

    return chapter


def save_file(filepath: Path, text: str, clobber: bool = False):
    """Write chapter text content to file"""
    if filepath.exists() and not clobber:
        return False

    with open(filepath, "w", encoding="utf-8") as file:
        file.write(text)
        return True


class TableOfContents:
    """Table of Contents scraper to query for any needed info"""

    def __init__(self, session: TorSession | None = None):
        self.domain: str = "www.wanderinginn.com"
        self.url: str = f"https://{self.domain}/table-of-contents"
        if session:
            assert isinstance(session, TorSession)
            self.response = session.get(self.url)
        else:
            self.response = requests.get(self.url, timeout=10)
            print("Request for Table of Contents timed out!", file=stderr)

        self.volume_data: OrderedDict[str, OrderedDict[str, str]]

        if self.response is None:
            self.soup = self.chapter_links = None
            self.volume_data = OrderedDict()
            print(
                "Table of Contents could not be reached! ToC `volume_data` will be `None`",
                file=stderr,
            )
            return

        # TODO: add check to not download chapter with password prompt
        self.soup = BeautifulSoup(self.response.content, "html.parser")
        self.chapter_links = self.__get_chapter_links()
        self.volume_data = self.__get_volume_data()

    def __get_chapter_links(self) -> list[str]:
        """Scrape table of contents for a list of chapter links"""
        if self.soup is None:
            return []

        return [
            f"https://{self.domain}" + link.get("href")
            for link in self.soup.select(".chapter-entry a")
        ]

    def __get_volume_data(self) -> OrderedDict[str, OrderedDict[str, str]]:
        """Return dictionary containing tuples (volume_title, chapter_indexes)
        by volume ID"""

        def get_title_and_href_from_a_tag(element: Tag):
            """Return tuple of text and href from <a> tag

            Args:
                element: an <a> Tag element
            """
            # chapter_a = element.find_next("a")
            chapter_name = element.text
            chapter_href = element.get("href")
            return (chapter_name, chapter_href)

        volumes: OrderedDict[str, OrderedDict[str, str]] = OrderedDict()
        if self.soup is None:
            return volumes

        vol_elements = self.soup.select(".volume-wrapper")

        volumes = OrderedDict()
        for vol_ele in vol_elements:
            vol_name = vol_ele.select_one(".volume-header").text.strip()
            volumes[vol_name] = OrderedDict()

            # Search for books
            book_sections = vol_ele.select(".book-wrapper")
            for section in book_sections:
                # Check for book heading
                heading_div = section.select_one(".book-header .head-book-title")

                # Use book title or default to "Unreleased" for sections without a released audiobook
                book_name = heading_div.text if heading_div else "Unreleased"

                volumes[vol_name][book_name] = OrderedDict()

                chapters = section.select(".book-body a")

                # Populate chapters for each book by title
                for chapter in chapters:
                    chapter_name, chapter_href = get_title_and_href_from_a_tag(chapter)
                    volumes[vol_name][book_name][chapter_name] = chapter_href

        return volumes

    def get_book_titles(self, is_released: bool = False):
        """Get a list of Book titles from TableOfContents"""
        if is_released:
            return [x.text.strip() for x in self.soup.select(".book:not(.unreleased)")]
        else:
            return [x.text.strip() for x in self.soup.select(".book")]
