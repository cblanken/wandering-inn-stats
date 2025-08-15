from pywikibot import family
from typing import Literal


class Family(family.Family):
    name = "twi"
    langs = {
        "en": "wiki.wanderinginn.com",
    }
    domain = "wiki.wanderinginn.com"

    def scriptpath(self, code: str) -> Literal[""]:
        return ""

    def protocol(self, code: str) -> Literal["HTTPS"]:
        return "HTTPS"

    def version(self, code: str) -> Literal["1.39.7"]:
        return "1.39.7"
