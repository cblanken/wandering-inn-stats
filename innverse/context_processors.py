from typing import Any

from django.conf import settings
from django.http import HttpRequest


def analytics(_req: HttpRequest) -> dict[str, Any]:
    return {"ANALYTICS_ID": settings.ANALYTICS_ID}


def prod(_req: HttpRequest) -> dict[str, Any]:
    return {"TWI_PROD": settings.TWI_PROD}
