from collections.abc import Callable
from enum import Enum
from pathlib import Path

import plotly.io as pio
from django.conf import settings
from django.utils.text import slugify
from plotly.graph_objects import Figure

pio.templates.default = "plotly_dark"


class Filetype(Enum):
    SVG = "svg"
    PNG = "png"
    JPG = "jpg"
    HTML = "html"


def get_chart_path(filename: str, filetype: Filetype, extra_path: Path = "") -> Path:
    return Path(
        "charts",
        filetype.value,
        extra_path,
        f"{filename}.{filetype.value}",
    )


def get_local_static_chart_path(filename: str, filetype: Filetype, extra_path: Path = "") -> Path:
    return Path("stats", "static", get_chart_path(filename, filetype, extra_path))


class ChartGalleryItem:
    def __init__(
        self,
        title: str,
        caption: str,
        filetype: Filetype,
        get_fig: Callable[[], Figure | None],
        subdir: Path = Path(),
        popup_info: str | None = None,
        has_chapter_filter: bool = True,
    ) -> None:
        self.title = title
        self.title_slug = slugify(title)
        self.caption = caption
        self.filetype = filetype
        self.get_fig: Callable[[], Figure | None] = get_fig
        self.popup_info: str | None = popup_info
        self.has_chapter_filter = has_chapter_filter

        # Paths and URLs
        self.template_url = str(Path(subdir, f"{self.title_slug}.{Filetype.HTML.value}"))
        self.thumbnail_url = f"{settings.STATIC_URL}{get_chart_path(self.title_slug, filetype, subdir)}"
        self.local_thumbnail_path = get_local_static_chart_path(self.title_slug, filetype, subdir)
        self.html_url = str(Path(f"{settings.STATIC_URL}", f"{get_chart_path(self.title_slug, Filetype.HTML, subdir)}"))
        self.local_html_path = get_local_static_chart_path(self.title_slug, Filetype.HTML, subdir)
