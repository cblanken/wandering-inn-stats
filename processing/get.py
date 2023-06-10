"""Module to download every chapter from the links in the Wandering Inn Table of Contents"""
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from itertools import chain
import hashlib
import re
import string
import time
from bs4 import BeautifulSoup, ResultSet, Tag
import requests
import requests.exceptions
from stem import Signal
from stem.control import Controller
from fake_useragent import UserAgent

BASE_URL: str = "https://wanderinginn.com"
WIKI_URL: str = "https://thewanderinginn.fandom.com"

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
    def __init__(self, proxy_ip: str = "127.0.0.1", proxy_port: int = 9050, max_tries: int = 10):
        self.__session = requests.session()
        self.__proxy_port = proxy_port
        self.set_tor_proxy(proxy_ip)
        self.__tries = 0 # resets after a sucessful chapter download
        self.__max_tries = max_tries

    def get(self, url) -> requests.Response:
        resp = None
        while self.__tries < self.__max_tries:
            resp = self.__session.get(url=url,
                                      headers= { "User-Agent": UserAgent().random },
                                      allow_redirects=True,
                                      timeout=10)
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
        with Controller.from_port(port=control_port) as conn:
            if conn.is_newnym_available():
                conn.authenticate()
                conn.signal(Signal.NEWNYM)
                time.sleep(0.25)
            else:
                print("! New Tor circuit not available - must wait for Tor to accept NEWNYM signal")
                breakpoint()
                #while(True):
                #    print("> Switching Tor circuit...")
                #    start_ip: str = self.session.get("https://api.ipify.org").text.strip()
                #    start_time: float = time.time()

                #    # Wait for new IP
                #    current_ip = start_ip
                #    while(time.time() - start_time < 3):
                #        current_ip = self.session.get("https://api.ipify.org").text.strip()
                #        if current_ip != start_ip:
                #            print(f"> Switched Tor circuit from {start_ip} to {current_ip}")
                #            return current_ip
                #        time.sleep(0.5)

                #    reply = input("Try new Tor circuit? (y/n): ")
                #    breakpoint()
                #    if reply.lower() != "y":
                #        break

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
            x["title"]:WIKI_URL + x["href"] for x in soup.select(".category-page__member-link") \
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
        return { c:self.__get_character_by_alpha(c) for c in string.ascii_uppercase }

    def get_all_character_data(self) -> dict[str:dict]:
        print(f"> Getting links to all character wiki pages...")
        chars_by_alpha = self.__get_all_characters_by_alpha()
        data = {}
        for chars in chars_by_alpha.values():
            for char, url in chars.items():
                data[char] = { "wiki_href": url }
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
                                str(alias_ele[0].select('.pi-data-value')[0]).replace("<br/>", "\n").replace("<br>", "\n"),
                                "html.parser")
                                
                            aliases = [
                                remove_bracketed_ref_number(x) for x in alias_soup.text.strip().split("\n")]
                        data[char]["aliases"] = aliases
                    
                    first_appearance_ele = soup.select('.pi-data[data-source="first appearance"] a')
                    if len(first_appearance_ele) > 0:
                        data[char]["first_href"] = first_appearance_ele[0]["href"]

                    status_ele = soup.select('.pi-data[data-source="status"]')
                    if len(status_ele) > 0:
                        data[char]["status"] = status_ele[0].select(".pi-data-value")[0].text

                    species_ele = soup.select('.pi-data[data-source="species"]')
                    if len(species_ele) > 0:
                        data[char]["species"] = species_ele[0].select(".pi-data-value")[0].text

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
            x["title"]:WIKI_URL + x["href"] for x in soup.select(".category-page__member-link") \
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
        return { c:self.get_locations_by_alpha(c) for c in string.ascii_uppercase }

    def get_class_list(self) -> list[str]:
        list_hrefs = [
            "https://thewanderinginn.fandom.com/wiki/List_of_Classes/A-L",
            "https://thewanderinginn.fandom.com/wiki/List_of_Classes/M-Z",
        ]
        soups = [BeautifulSoup(self.get(href).text, "html.parser") for href in list_hrefs]

        classes = [
            [x.text.strip().replace("[", "").replace("]", "") for x in soup.select(
                "table.article-table tr > td:first-of-type") if "..." not in x.text.strip()
            ] for soup in soups
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
        soup = BeautifulSoup(self.get("https://thewanderinginn.fandom.com/wiki/Spells").text, "html.parser")
        spell_elements: ResultSet[Tag] = soup.select("table.article-table tr > td:first-of-type")

        # Split multiple spells/aliases joined by "/"
        spells = []
        pattern = re.compile(r"\[(.*?)\]")
        for i, spell in enumerate(spell_elements):
            spell_parts = list(filter(lambda x: not x.isnumeric(), pattern.findall(spell.text)))

            if len(spell_parts) == 0:
                spells.append(spell.text.strip())
            else:
                #spell_parts = spell.stripped_strings
                spells.append("|".join(spell_parts))

        return set(sorted(spells))

    

def parse_chapter(response: requests.Response) -> dict[str]:
    """Parse data from chapter

    Args:
        response: Requests response object holding data from chapter download
    
    Returns:

    """
    chapter = {}

    soup: BeautifulSoup = BeautifulSoup(response.content, 'html.parser')

    # Parse chapter content html from Response object
    result = soup.select_one('.entry-content')
    if result is not None:
        chapter["html"] = str(result)

    # Parse chapter text from Response object
    header_text: str = [element.get_text() for element in soup.select(".entry-title")]
    content_text: str = [element.get_text() for element in soup.select(".entry-content")]
    if len(header_text) != 0 and len(content_text) != 0:
        chapter["text"] = "\n".join([header_text[0], content_text[0]])

    # Parse chapter metadata from Response object
    soup: BeautifulSoup = BeautifulSoup(response.content, 'html.parser')
    try:
        title: str = soup.select(".entry-title")[0].get_text()
        pub_time: str = soup.select("meta[property='article:published_time']")[0].get("content")
        mod_time: str = soup.select("meta[property='article:modified_time']")[0].get("content")
        word_count: str = len(re.split(r'\W+', soup.text))
        dl_time: str = str(datetime.now().astimezone())
        digest: str = hashlib.sha256(chapter["text"].encode("utf-8")).hexdigest()
        chapter["metadata"] = {
            "title": title,
            "pub_time": pub_time,
            "mod_time": mod_time,
            "dl_time": dl_time,
            "url": response.url,
            "word_count": word_count,
            "digest": digest,
        }
    except IndexError as exc:
        print(f"! Couldn't find metadata at {response.url}. Exception: {exc}")

    return chapter

def save_file(filepath: Path, text: str, clobber: bool = False):
    """Write chapter text content to file
    """
    if filepath.exists() and not clobber:
        return False

    with open(filepath, "w", encoding="utf-8") as file:
        file.write(text)
        return True

class TableOfContents:
    """Object to scrape the Table of Contents and methods to query for any needed info
    """
    def __init__(self, session: TorSession=None):
        self.domain: str = "www.wanderinginn.com"
        self.url: str = f"https://{self.domain}/table-of-contents"
        if session:
            assert isinstance(session, TorSession)
            self.response = session.get(self.url)
        else:
            self.response = requests.get(self.url, timeout=10)

        if self.response is None:
            self.soup = self.chapter_links = self.volume_data = None
            return

        # TODO: add check to not download chapter with password prompt / protected status
        self.soup = BeautifulSoup(self.response.content, 'html.parser')
        self.chapter_links = self.__get_chapter_links()
        self.volume_data: OrderedDict[str:OrderedDict[str:str]] = self.__get_volume_data()

    def __get_chapter_links(self) -> list[str]:
        """Scrape table of contents for an list of chapter links
        """
        if self.soup is None:
            return []
        
        return [f"https://{self.domain}" + link.get("href") for link in self.soup.select(".chapters a")]

    def __get_volume_data(self) -> OrderedDict[str:OrderedDict[str:str]]:
        """Return dictionary containing tuples (volume_title, chapter_indexes) by volume ID
        """

        volumes = OrderedDict()
        if self.soup is None:
            return volumes

        vol_elements = self.soup.select(".volume-table")

        def get_next_name_and_href_from_a(element: Tag):
            """Return tuple of text and href from <a> tag

            Args:
                element: an <a> Tag element
            """
            chapter_a = element.find_next("a")
            chapter_name = chapter_a.text
            chapter_href = chapter_a.get("href")
            return (chapter_name, chapter_href)


        volumes = OrderedDict()
        for vol_ele in vol_elements:
            vol_name = vol_ele.previous_sibling.text.strip()
            volumes[vol_name] = OrderedDict()
            # Search for books
            last_chapter_row = None
            book_headings = vol_ele.select(".head-book-title")
            if len(book_headings) > 0:
                for heading in book_headings:
                    book_name = heading.text
                    volumes[vol_name][book_name] = OrderedDict()
                    chapters = []
                    # Walk up tree to table head
                    table_head = heading.parent.parent
                    for sibling in table_head.next_siblings:
                        row_classes = sibling.get("class")
                        if "table-head" in row_classes:
                            # Found a new Book heading, continue to next Book
                            break
                        
                        last_chapter_row = sibling

                        # Populate chapter for each book by book title if they exist
                        chapter_name, chapter_href = get_next_name_and_href_from_a(sibling)
                        volumes[vol_name][book_name][chapter_name] = chapter_href
            
            # Lump any REMAINING chapters in Volume under "Unreleased" Book
            if last_chapter_row is None:
                # No Books found -> lump ALL chapters into "Unreleased"
                volumes[vol_name]["Unreleased"] = OrderedDict()
                for chapter in vol_ele.select(".chapter-entry"):
                    chapter_name, chapter_href = get_next_name_and_href_from_a(chapter)
                    volumes[vol_name]["Unreleased"][chapter_name] = chapter_href
            else:
                # Start from last visited Chapter row
                remaining_chapters = list(last_chapter_row.next_siblings)
                if len(remaining_chapters) == 0:
                    # No remeining chapters to populate "Unreleased"
                    continue

                volumes[vol_name]["Unreleased"] = OrderedDict()
                for sibling in remaining_chapters:
                    chapter_name, chapter_href = get_next_name_and_href_from_a(sibling)
                    volumes[vol_name]["Unreleased"][chapter_name] = chapter_href
            
        return volumes

    def get_book_titles(self, is_released: bool = False):
        """Get a list of Book titles from TableOfContents
        """
        if is_released:
            return [x.text.strip() for x in self.soup.select(".book:not(.unreleased)")]
        else:
            return [x.text.strip() for x in self.soup.select(".book")]