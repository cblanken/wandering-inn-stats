"""Models for Wandering Inn volume and chapter data
"""

from __future__ import annotations
from enum import Enum
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://wanderinginn.com"
DEFAULT_CONTEXT_LEN = 50

class Color(Enum):
    """
    Enum to specify colored text in the book
    """
    # TODO: replace values with RGB / HEX
    GREY = "grey"
    GREEN = "green"
    RED = "red"
    LIGHT_BLUE = "light blue"
    BLUE = "blue"
    GOLD = "gold"

class Class:
    """
    Model for [Class]es in the book

    Attributes:
        name (str): name of the [Class]
        desc (str): short description of the [Class]
    """
    def __init__(self, name: str, desc: str):
        self.name = name
        self.desc = desc

class Skill:
    """
    Model for [Skill]es in the book

    Attributes:
        name (str): name of the [Skill]
        desc (str): short description of the [Skill]
    """
    def __init__(self, name: str, desc: str, color: Color = Color.GREY):
        self.name = name
        self.desc = desc
        self.color = color

class Spell:
    """
    Model for [Spell]s in the book

    Attributes:
        name (str): name of the [Spell]
        desc (str): short description of the [Spell]
    """
    def __init__(self, name: str, desc: str):
        self.name = name
        self.desc = desc

class TextRef:
    """
    A Text Reference to a specified keyword in a given text

    Attributes:
        phrase (str): Keyphrase found
        line (int): Line number in the text
        start_column (int): Column number of first letter in (phrase) found in the text
        end_col (int): Column number of last letter in (phrase) found in the text
        context (str): Contextual text surrounding (phrase)
    """
    def __init__(self, text: str, line_text: str, line_id: int, start_column: int,
        end_column: int, context_offset: int = DEFAULT_CONTEXT_LEN) -> TextRef:
        self.text = text.strip()
        self.line_id = line_id
        self.start_column = start_column
        self.end_column = end_column
        self.context_offset = context_offset

        # Construct surrounding context string
        start = max(start_column - context_offset, 0)
        end = min(end_column + context_offset, len(line_text))
        self.context = line_text[start:end].strip()

    def __str__(self):
        return f"line: {self.line_id:<6}start: {self.start_column:<5}end: {self.end_column:<5}text: {self.text:.<50}context: {self.context}"

class Chapter:
    """
    Model for chapter objects

    Attributes:
        id (int): id indicating n for range [1, n] for all book chapters
        volume_chapter_id (int): volume specific id number where the origin is based on the first
            chapter of the volume
        title (str): title of the chapter
        is_interlude (bool): whether or not the chapter is an Interlude chapter
            These chapters usually follow side-characters, often specified with the letters of the
            the characters' first names
        url (str): link to chapter web page
    """
    def __init__(self, id: int, title: str, is_interlude: bool, url: str,
        post_date: str) -> Chapter:
        self.id = id
        self.title = title
        self.is_interlude = is_interlude
        self.url = url
        self.post_date = post_date

    def __str__(self):
        return f"id: {self.id}\t{self.title}\t{self.url}"

class Volume:
    """
    Model for Volume objects

    Attributes:
        id (int): Database ID for volume, should correspond to the sequence of volumes
        title (str): Title of the volume, typically Volume X where X matches the ID
        summary (str): Short summary of the volume
    """
    def __init__(self, id: int, title: str, chapter_range: tuple[int, int], summary: str = ""):
        self.id = id
        self.title = title
        self.chapter_range = chapter_range
        self.summary = summary

    def __str__(self):
        return f"id: {self.id:<4}title: {self.title:<12}summary: {self.summary}"

class TableOfContents:
    """Object to scrape the Table of Contents and methods to query for any needed info
    """
    def __init__(self):
        self.url = "https://wanderinginn.com/table-of-contents/"
        table_of_contents = requests.get(self.url)
        if table_of_contents.status_code != 200:
            print(f"Cannot access {self.url}. Check your network connection.")
            return None
        self.soup = BeautifulSoup(table_of_contents.content, 'html.parser')
        self.chapter_links = self.get_chapter_links()
        self.volume_data = self.get_volume_data()

    def get_chapter_links(self):
        """Scrape table of contents for chapter links
        """
        chapter_link_elements = self.soup.select(
                f'#content div > p > a[href^="{BASE_URL}"]')
        return list(filter(None, [link.get('href') for link in chapter_link_elements]))

    def get_volume_data(self):
        """Return dictionary containg tuples (volume_title, chapter_indexes) by volume ID
        """
        volume_titles = self.soup.select('#content div > p:nth-of-type(2n+1) strong')
        chapter_lists = [
            x.find_all('a') for x in self.soup.select('#content div p:nth-of-type(2n)')
        ]

        volume_data = zip(volume_titles, chapter_lists)

        volumes = {}
        volume_id = 1
        chapter_index = 1
        for volume in volume_data:
            title = volume[0].get_text().strip()
            chapter_elements = volume[1]

            start = chapter_index
            end = start + len(chapter_elements) - 1

            volumes[volume_id] = (title, (start, end))
            chapter_index = end + 1
            volume_id += 1

        return volumes
