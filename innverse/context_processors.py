from django.conf import settings
from typing import Any


def analytics() -> dict[str, Any]:
    return {"ANALYTICS_ID": settings.ANALYTICS_ID}
