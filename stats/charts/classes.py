from stats.models import Chapter, RefType

from .gallery import ChartGalleryItem
from .reftype_types import get_reftype_type_gallery


def get_class_charts(
    first_chapter: Chapter | None = None, last_chapter: Chapter | None = None
) -> list[ChartGalleryItem]:
    default_chart_gallery: list[ChartGalleryItem] = get_reftype_type_gallery(
        RefType.Type.CLASS, first_chapter, last_chapter
    )
    return (
        default_chart_gallery
        + [
            # Custom gallery charts
        ]
    )
