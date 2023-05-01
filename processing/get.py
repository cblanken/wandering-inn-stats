"""Module to download every chapter from the links in the Wandering Inn Table of Contents"""
from sys import argv, stderr
from pathlib import Path
from time import sleep
from bs4 import BeautifulSoup
import requests
import requests.exceptions

REQUEST_THROTTLE_S = 1.0
BASE_URL = "https://wanderinginn.com"

def get_chapter(chapter_link):
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

def get_chapter_text(response):
    """Scrape chapter text from Response object
    """
    soup = BeautifulSoup(response.content, 'html.parser')
    header_text = [element.get_text() for element in soup.select(
        '#content > article > header.entry-header')]
    content_text = [element.get_text() for element in soup.select(
        '#content > article > div.entry-content > *')]
    return "".join(header_text) + "\n\n".join(content_text)

def save_file(filepath, content):
    """Write chapter text content to file
    """
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(content)

class TableOfContents:
    """Object to scrape the Table of Contents and methods to query for any needed info
    """
    def __init__(self):
        self.url = "https://wanderinginn.com/table-of-contents/"
        table_of_contents = requests.get(self.url, timeout=10)
        if table_of_contents.status_code != requests.codes['ok']:
            print(f"Cannot access {self.url}. Check your network connection.")
            self.soup = self.chapter_links = self.volume_data = None
            return
        self.soup = BeautifulSoup(table_of_contents.content, 'html.parser')
        self.chapter_links = self.get_chapter_links()
        self.volume_data = self.get_volume_data()

    def get_chapter_links(self):
        """Scrape table of contents for an unordered list of chapter links
        """
        if self.soup is None:
            return []
        chapter_link_elements = self.soup.select(
                f'#content div > p > a[href^="{BASE_URL}"]')
        return list(filter(None, [link.get('href') for link in chapter_link_elements]))

    def get_volume_data(self):
        """Return dictionary containing tuples (volume_title, chapter_indexes) by volume ID
        """
        if self.soup is None:
            return []
        volume_titles = [x.text.strip() for x in self.soup.select('#content div > p:nth-of-type(2n)')]
        chapter_link_elements = [
            x.find_all('a') for x in self.soup.select('#content div p:nth-of-type(2n+1)')
        ]

        chapter_link_elements.pop(0) # remove link to archives added to ToC after Volume 1 rewrite

        return list(zip(volume_titles, chapter_link_elements))
