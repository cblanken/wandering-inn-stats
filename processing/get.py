"""Module to download every chapter from the links in the Wandering Inn Table of Contents"""
from collections import OrderedDict
from sys import stderr
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import requests.exceptions

BASE_URL: str = "https://wanderinginn.com"

def get_chapter(chapter_link: str) -> requests.Response:
    """Get requests Response for chapter link
    """
    try:
        return requests.get(chapter_link, timeout=10)
    except requests.HTTPError:
        print(f"Unable to retrieve chapter from {chapter_link}", file=stderr)
        return
    except requests.Timeout:
        print(f"Unable to retrieve chapter from {chapter_link}", file=stderr)
        return

def get_chapter_html(response: requests.Response) -> str:
    """Scrape chapter html from Response object
    """
    soup: BeautifulSoup = BeautifulSoup(response.content, 'html.parser')
    result = soup.select('.entry-content')
    if len(result) == 0:
        return None

    return str(result[0])

def get_chapter_text(response: requests.Response) -> str:
    """Scrape chapter text from Response object
    """
    soup: BeautifulSoup = BeautifulSoup(response.content, 'html.parser')
    header_text: str = [element.get_text() for element in soup.select(
        '#content > article .entry-title')]
    content_text: str = [element.get_text() for element in soup.select(
        '#content > article > div.entry-content')]
    return "\n".join([header_text[0], content_text[0]])

def save_file(filepath: Path, text: str):
    """Write chapter text content to file
    """
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(text)

class TableOfContents:
    """Object to scrape the Table of Contents and methods to query for any needed info
    """
    def __init__(self):
        self.url: str = "https://wanderinginn.com/table-of-contents"
        self.response = requests.get(self.url, timeout=10)
        if self.response.status_code != requests.codes['ok']:
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
        
        return [self.url + link.get("href") for link in self.soup.select(".chapters a")]

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
                        volumes[volume_title][book_title][link.text] = f"{self.url}{link['href']}"

        return volumes

    def get_book_titles(self, is_released: bool = False):
        """Get a list of Book titles from TableOfContents
        """
        if is_released:
            return [x.text.strip() for x in self.soup.select(".book:not(.unreleased)")]
        else:
            return [x.text.strip() for x in self.soup.select(".book")]