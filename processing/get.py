"""Module to download every chapter from the links in the Wandering Inn Table of Contents"""
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
import hashlib
import re
import string
import time
from bs4 import BeautifulSoup
import requests
import requests.exceptions
from stem import Signal
from stem.control import Controller
from fake_useragent import UserAgent

BASE_URL: str = "https://wanderinginn.com"
WIKI_URL: str = "https://thewanderinginn.fandom.com"

# TODO allow redirects 
# This https://wanderinginn.com/table-of-contents/interlude-satar-revised redirects to
# -> https://wanderinginn.com/2022/02/20/interlude-satar/ and doesn't get followed by a
# default requests.get( )
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

    def get_character_by_alpha(self, alpha_char: str) -> dict[str:str]:
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
        resp = requests.get(f"{char_endpoint}?from={alpha_char}", timeout=5)

        soup = BeautifulSoup(resp.text, "html.parser")
        return {
            x["title"]:WIKI_URL + x["href"] for x in soup.select(".category-page__member-link") \
                if "Category" not in x["title"]
        }

    def get_all_characters_by_alpha(self) -> dict[dict[str:str]]:
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
        return { c:self.get_character_by_alpha(c) for c in string.ascii_uppercase }

    def get_locations_by_alpha(self, alpha_char: str) -> dict[str]:
        """Get single location name and link to the wiki

        Returns:
            Dictionary of the form:
            {
                location name : url to wiki page,
                ...
            }
        """
        alpha_char = alpha_char.upper()
        if len(alpha_char) != 1 or alpha_char not in string.ascii_uppercase:
            raise ValueError("Invalid alphabetic character")

        char_endpoint = f"{WIKI_URL}/Category:Locations"
        resp = requests.get(f"{char_endpoint}?from={alpha_char}", timeout=5)
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
                    ...
                },
                ...
            }
        """
        return { c:self.get_locations_by_alpha(c) for c in string.ascii_uppercase }

def parse_chapter(response: requests.Response) -> dict[str]:
    """Parse data from chapter

    Args:
        response: Requests response object holding data from chapter download
    
    Returns:

    """
    # Parse chapter content html from Response object
    chapter = {}

    soup: BeautifulSoup = BeautifulSoup(response.content, 'html.parser')
    result = soup.select('.entry-content')
    if len(result) != 0:
        chapter["html"] = result[0].text

    # Parse chapter text from Response object
    soup: BeautifulSoup = BeautifulSoup(response.content, 'html.parser')
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
            assert(isinstance(session, TorSession))
            self.response = session.get(self.url)
        else:
            self.response = requests.get(self.url, timeout=10)

        if self.response is None:
            self.soup = self.chapter_links = self.volume_data = None
            return

        self.soup = BeautifulSoup(self.response.content, 'html.parser')
        self.chapter_links = self.__get_chapter_links()
        self.volume_data: dict[dict[dict[str]]] = self.__get_volume_data()

    def __get_chapter_links(self) -> list[str]:
        """Scrape table of contents for an list of chapter links
        """
        if self.soup is None:
            return []
        
        return [f"https://{self.domain}" + link.get("href") for link in self.soup.select(".chapters a")]

    def __get_volume_data(self):
        """Return dictionary containing tuples (volume_title, chapter_indexes) by volume ID
        """
        if self.soup is None:
            return []
        
        contents_elements = self.soup.select(".volume, .book, .chapters")

        volumes = OrderedDict()
        volume_title = ""
        book_title = ""
        for ele in contents_elements:
            match ele.name:
                case "h2":
                    volume_title = ele.text.strip()
                    volumes[volume_title] = OrderedDict()
                case "h3":
                    book_title = ele.text.strip()
                    volumes[volume_title][book_title] = OrderedDict()
                case "p":
                    for link in ele.select("a"):
                        volumes[volume_title][book_title][link.text] = f"https://{self.domain}{link['href']}"

        return volumes

    def get_book_titles(self, is_released: bool = False):
        """Get a list of Book titles from TableOfContents
        """
        if is_released:
            return [x.text.strip() for x in self.soup.select(".book:not(.unreleased)")]
        else:
            return [x.text.strip() for x in self.soup.select(".book")]