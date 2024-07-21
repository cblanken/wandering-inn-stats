from pywikibot import family


class Family(family.Family):
    name = "twi"
    langs = {
        "en": "wiki.wanderinginn.com",
    }
    domain = "wiki.wanderinginn.com"

    def scriptpath(self, code):
        return ""

    def protocol(self, code):
        return "HTTPS"

    def version(self, code):
        return "1.39.7"
