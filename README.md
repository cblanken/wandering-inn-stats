# The Wandering Inn Scraper
A simple python script that parses [The Wandering Inn]() Table of Contents for the links to all the chapters and subsequently downloads them. All chapters are saved to `./chapters/all/`.

The script accepts two arguments
1. An offset or starting chapter id
2. A maximum or last chapter id

## Usage
```console
$ python get.py         # download all chapters
$ python get.py 0 200   # download the first 200 chapters
$ python get.py 200 500 # download chapters 200 to 500
```
