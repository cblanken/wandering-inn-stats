from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import include, path
from django.urls.resolvers import URLResolver

from stats.enums import AdminActionTypes
from stats.views.admin import SelectForeignModelView

from .models import (
    Alias,
    Book,
    Chapter,
    ChapterLine,
    Character,
    Color,
    ColorCategory,
    Location,
    RefType,
    RefTypeChapter,
    RefTypeComputedView,
    TextRef,
    Volume,
)


class StatsAdminSite(admin.AdminSite):
    site_header = "Innverse Stats administration"

    def get_urls(self) -> list[URLResolver]:
        custom_urls = [
            path(
                "custom-actions/",
                include(
                    [
                        path(
                            "select-book/",
                            self.admin_view(
                                SelectForeignModelView.as_view(
                                    admin=self,
                                    base_model=Chapter,
                                    field="book",
                                    select_model=Book,
                                    template_name="custom_admin/select_book.html",
                                )
                            ),
                        ),
                        path(
                            "select-reftype/",
                            self.admin_view(
                                SelectForeignModelView.as_view(
                                    admin=self,
                                    base_model=Alias,
                                    field="ref_type",
                                    select_model=RefType,
                                    qs_model=RefType,
                                    template_name="custom_admin/select_reftype.html",
                                )
                            ),
                        ),
                    ]
                ),
            )
        ]
        admin_urls = super().get_urls()
        return custom_urls + admin_urls


site = StatsAdminSite(name="twi-admin")
admin.site = site


# Admin model settings
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["title", "number", "word_count", "post_date", "is_canon", "is_interlude"]
    list_filter = ["is_canon", "is_interlude", "book__volume__title", "book__title"]
    search_fields = ["title", "source_url"]
    autocomplete_fields = ["book"]

    @admin.action(description='Move chapter(s) to Book "X"', permissions=["change"])
    def move_chapters_to_book(self, _request: HttpRequest, queryset: QuerySet) -> HttpResponseRedirect | None:
        selected = queryset.values_list("pk", flat=True)
        return HttpResponseRedirect(
            f"/admin/custom-actions/select-book/?return_url=/admin/stats/chapter&action={AdminActionTypes.MOVE_CHAPTERS}&ids={','.join(str(pk) for pk in selected)}",
            preserve_request=True,
        )

    actions = [move_chapters_to_book.__name__]


class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "number", "volume"]
    search_fields = ["title"]

    def get_form(self, request, obj=None, **kwargs):  # noqa
        form = super().get_form(request, obj, **kwargs)
        if form:
            form.base_fields["summary"].required = False
        return form


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
            f"/admin/custom-actions/select-reftype/?return_url=/admin/stats/reftype&action={AdminActionTypes.MERGE_REFTYPES_NO_ALIAS}&ids={','.join(str(pk) for pk in selected)}",
            preserve_request=True,
        )

    @admin.action(description="Merge (with alias) selected RefTypes into RefTypeB (creates alias of RefTypeA.name)")
    def merge_reftypes_with_alias(self, _request: HttpRequest, queryset: QuerySet) -> HttpResponseRedirect | None:
        selected = queryset.values_list("pk", flat=True)
        return HttpResponseRedirect(
            f"/admin/custom-actions/select-reftype/?return_url=/admin/stats/reftype&action={AdminActionTypes.MERGE_REFTYPES_WITH_ALIAS}&ids={','.join(str(pk) for pk in selected)}",
            preserve_request=True,
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

    def get_form(self, request, obj=None, **kwargs):  # noqa
        form = super().get_form(request, obj, **kwargs)
        if form:
            form.base_fields["color"].required = False
        return form


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
site.register(Chapter, ChapterAdmin)
site.register(Book, BookAdmin)
site.register(Volume, VolumeAdmin)

# Text reference data
site.register(Alias, AliasAdmin)
site.register(ChapterLine, ChapterLineAdmin)
site.register(Color, ColorAdmin)
site.register(ColorCategory, ColorCategoryAdmin)
site.register(RefType, RefTypeAdmin)
site.register(RefTypeComputedView, RefTypeComputedViewAdmin)
site.register(TextRef, TextRefAdmin)
site.register(RefTypeChapter, RefTypeChapterAdmin)

# Wiki data objects
site.register(Character, CharacterAdmin)
site.register(Location, LocationAdmin)
