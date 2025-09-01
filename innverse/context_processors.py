from django.conf import settings
from django.http import HttpRequest
from typing import Any


def analytics(_req: HttpRequest) -> dict[str, Any]:
    return {"ANALYTICS_ID": settings.ANALYTICS_ID}
