from django import template
from django.http import HttpRequest

register = template.Library()


@register.filter(name="absolute_uri")
def absolute_uri(req: HttpRequest, path: str) -> str:
    """Builds the absolute URI of the given path argument"""
    try:
        return req.build_absolute_uri(path)
    except AttributeError:
        """Invalid req object provided return initial input path"""
        return path
