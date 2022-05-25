#!/usr/bin/python
# Download every chapter from the links in the Wandering Inn Table of Contents
from sys import argv, exit
from requests import get
from bs4 import BeautifulSoup
from os import path, sep, getcwd
from time import sleep

BASE_PATH = "chapters/all"
# TODO create BASE_PATH dir if it doesn't exist
def getChapterLinks():
    url = "https://wanderinginn.com/table-of-contents/"
    table_of_contents = get(url)
    if table_of_contents.status_code != 200:
        print(f"Cannot access {url}. Check your network connection.")
        exit(0)

    soup = BeautifulSoup(table_of_contents.content, 'html.parser')
    chapter_link_elements = soup.select(
            '#content div.entry-content > p > a[href^="https://wanderinginn.com"]')
    chapter_links = list(filter(None, [link.get('href') for link in chapter_link_elements]))
    return chapter_links

def getChapterText(link):
    page = get(link)
    soup = BeautifulSoup(page.content, 'html.parser')
    header_text = [element.get_text() for element in soup.select(
        '#content > article > header.entry-header')]
    content_text = [element.get_text() for element in soup.select(
        '#content > article > div.entry-content > *')]
    return "".join(header_text) + "\n\n".join(content_text)

def saveChapter(filename, content):
    with open(filename, "w") as f:
        f.write(content)

if __name__ == "__main__":
    chapter_links = getChapterLinks()
    max_chapter = len(chapter_links)
    if len(argv) == 1:
        offset = 0
    elif len(argv) == 2:
        try:
            # Max offset of 1000
            offset = min(int(argv[1]), 1000)
        except TypeError:
            print("Invalid offset argument. Enter a number between 1 and 1000.")
            exit(0)
    elif len(argv) > 2:
        try:
            # Max offset of 1000
            offset = min(int(argv[1]), 1000)
            max_chapter = min(int(argv[2]), max_chapter)
        except TypeError:
            print("Invalid offset argument. Enter a number between 1 and 1000.")
            exit(0)
    else:
        offset = 0

    # TODO handle keyboard interrupt
    for i, link in enumerate(chapter_links[offset:max_chapter]): 
        file_prefix = f"{offset + i}-" 

        # remove trailing '/' from URL
        file_suffix = str(link[8:-1]) if link[-1] == "/" else str(link[8:])

        filename = file_prefix + file_suffix.replace(sep, '-')
        filepath = sep.join([getcwd(), BASE_PATH, filename])
        if not path.exists(filepath) and link != None:
            print("Downloading {} to {}".format(link, filepath))
            saveChapter(filepath, getChapterText(link))
            sleep(0.25)
        else:
            print("Skipping {}, {} already exists".format(link, filename))
