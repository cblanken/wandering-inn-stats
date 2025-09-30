from django.contrib import admin
from django.http import HttpRequest, HttpResponseRedirect
from django.db.models import QuerySet
from .models import (
    Chapter,
    Book,
    Volume,
    Alias,
    ChapterLine,
    Color,
    ColorCategory,
    RefType,
    RefTypeComputedView,
    TextRef,
    RefTypeChapter,
    Location,
    Character,
)


# Admin model settings
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["title", "number", "word_count", "post_date", "is_canon", "is_interlude"]
    list_filter = ["is_canon", "is_interlude", "book__volume__title", "book__title"]
    search_fields = ["title", "source_url"]


class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "number", "volume"]


class VolumeAdmin(admin.ModelAdmin):
    list_display = ["title", "number"]


class AliasAdmin(admin.ModelAdmin):
    list_display = ["name", "ref_type"]
    list_filter = ["ref_type__type"]
    search_fields = ["name"]
    autocomplete_fields = ["ref_type"]


class ChapterLineAdmin(admin.ModelAdmin):
    list_display = ["chapter", "line_number", "text"]
    list_filter = ["chapter__title"]
    ordering = ["line_number"]
    search_fields = ["text"]


class CharacterAdmin(admin.ModelAdmin):
    list_display = ["ref_type", "species", "first_chapter_appearance", "wiki_uri"]
    list_filter = ["status", "species"]
    search_fields = ["ref_type__name"]
    autocomplete_fields = ["ref_type", "first_chapter_appearance"]
    ordering = ["ref_type__name"]


class ColorAdmin(admin.ModelAdmin):
    list_display = ["category", "rgb"]
    ordering = ["category__name"]


class ColorCategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]


class RefTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "word_count", "letter_count"]
    list_filter = ["type"]
    search_fields = ["name"]
    radio_fields = {"type": admin.VERTICAL}

    @admin.action(
        description="Merge (no alias) selected RefTypes into RefTypeB (does NOT create alias of RefTypeA.name)"
    )
    def merge_reftypes(self, _request: HttpRequest, queryset: QuerySet) -> HttpResponseRedirect | None:
        selected = queryset.values_list("pk", flat=True)
        return HttpResponseRedirect(
            f"/stats/select_reftype/?no_alias=1&ids={','.join(str(pk) for pk in selected)}", preserve_request=True
        )

    @admin.action(description="Merge (with alias) selected RefTypes into RefTypeB (creates alias of RefTypeA.name)")
    def merge_reftypes_with_alias(self, _request: HttpRequest, queryset: QuerySet) -> HttpResponseRedirect | None:
        selected = queryset.values_list("pk", flat=True)
        return HttpResponseRedirect(
            f"/stats/select_reftype/?ids={','.join(str(pk) for pk in selected)}", preserve_request=True
        )

    actions = [merge_reftypes.__name__, merge_reftypes_with_alias.__name__]


class LocationAdmin(admin.ModelAdmin):
    list_display = ["ref_type", "wiki_uri", "first_chapter_ref"]
    search_fields = ["ref_type__name"]


class TextRefAdmin(admin.ModelAdmin):
    list_display = ["type", "color", "start_column", "end_column", "chapter_line"]
    list_filter = ["color__category__name", "chapter_line__chapter__title"]
    search_fields = ["type__name"]
    raw_id_fields = ["chapter_line"]
    autocomplete_fields = ["type"]


class RefTypeChapterAdmin(admin.ModelAdmin):
    list_display = ["type", "chapter"]
    list_filter = ["chapter__title"]
    search_fields = ["type__name", "chapter__title"]
    autocomplete_fields = ["type"]


class RefTypeComputedViewAdmin(admin.ModelAdmin):
    list_display = ["mentions", "ref_type"]
    list_filter = ["ref_type__type"]
    ordering = ["mentions"]
    search_fields = ["ref_type__name"]


# Organizational data
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Volume, VolumeAdmin)

# Text reference data
admin.site.register(Alias, AliasAdmin)
admin.site.register(ChapterLine, ChapterLineAdmin)
admin.site.register(Color, ColorAdmin)
admin.site.register(ColorCategory, ColorCategoryAdmin)
admin.site.register(RefType, RefTypeAdmin)
admin.site.register(RefTypeComputedView, RefTypeComputedViewAdmin)
admin.site.register(TextRef, TextRefAdmin)
admin.site.register(RefTypeChapter, RefTypeChapterAdmin)

# Wiki data objects
admin.site.register(Character, CharacterAdmin)
admin.site.register(Location, LocationAdmin)
