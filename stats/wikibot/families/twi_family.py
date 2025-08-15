from pywikibot import family
from typing import Literal


class Family(family.Family):
    name = "twi"
    langs = {
        "en": "wiki.wanderinginn.com",
    }
    domain = "wiki.wanderinginn.com"

    # Note: these methods must take `code` as a 2nd argument
    # Using `_code` or something else breaks something in the pywikibot auth
    def scriptpath(self, code: str) -> Literal[""]:  # noqa: ARG002
        return ""

    def protocol(self, code: str) -> Literal["HTTPS"]:  # noqa: ARG002
        return "HTTPS"

    def version(self, code: str) -> Literal["1.39.7"]:  # noqa: ARG002
        return "1.39.7"
