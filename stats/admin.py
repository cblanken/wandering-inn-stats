from django.contrib import admin
from .models import *

# Admin model settings
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["title", "number", "word_count", "post_date", "is_interlude"]
    list_filter = ["is_interlude", "book__volume__title", "book__title"]


class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "number", "volume"]


class VolumeAdmin(admin.ModelAdmin):
    list_display = ["title", "number"]


class AliasAdmin(admin.ModelAdmin):
    list_display = ["name", "ref_type"]
    list_filter = ["ref_type__type"]
    search_fields = ["name"]


class ChapterLineAdmin(admin.ModelAdmin):
    list_display = ["chapter", "line_number", "text"]


class CharacterAdmin(admin.ModelAdmin):
    list_display = ["ref_type", "species", "first_chapter_ref", "wiki_uri"]
    list_filter = ["status", "species"]
    search_fields = ["ref_type__name"]


class ColorAdmin(admin.ModelAdmin):
    list_display = ["category", "rgb"]


class ColorCategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]


class RefTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "description"]
    search_fields = ["name"]


class TextRefAdmin(admin.ModelAdmin):
    list_display = ["type", "color", "start_column", "end_column", "chapter_line"]
    list_filter = ["color__category__name", "chapter_line__chapter__title"]
    search_fields = ["type__name"]


# Model registrations
# Organizational data
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Volume, VolumeAdmin)

# Text reference data
admin.site.register(Alias, AliasAdmin)
admin.site.register(ChapterLine, ChapterLineAdmin)
admin.site.register(Character, CharacterAdmin)
admin.site.register(Color, ColorAdmin)
admin.site.register(ColorCategory, ColorCategoryAdmin)
admin.site.register(RefType, RefTypeAdmin)
admin.site.register(TextRef, TextRefAdmin)
