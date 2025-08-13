from django import forms
from django.core.cache import cache
from stats.models import RefType, Chapter

MAX_CHAPTER_NUM = (
    cache.get_or_set(
        "MAX_CHAPTER_NUM",
        int(Chapter.objects.values_list("number").order_by("-number")[0][0]),
        60 * 60 * 24,
    )
    or 0
)


def get_chapters():
    yield (0, "--- First Chapter ---")
    i = 0
    for tup in ((c["number"], c["title"]) for c in Chapter.objects.values("number", "title").order_by("number")):
        i += 1
        yield tup
    yield (i, "--- Last Chapter ---")


select_input_tailwind_classes = "bg-bg-primary text-text-primary border-none"
select_input_styles = "max-width: 15rem"
checkbox_tailwind_classes = "bg-bg-tertiary"
integer_input_tailwind_classes = "bg-bg-tertiary"


class ChapterFilterForm(forms.Form):
    chapter_choices = list(get_chapters())
    max_choice = len(chapter_choices) - 2

    first_chapter = forms.TypedChoiceField(
        label="First Chapter",
        choices=chapter_choices,
        required=False,
        initial=0,
        widget=forms.Select(attrs={"class": select_input_tailwind_classes, "style": select_input_styles}),
    )

    last_chapter = forms.TypedChoiceField(
        label="Last Chapter",
        choices=chapter_choices,
        required=False,
        initial=max_choice,
        widget=forms.Select(attrs={"class": select_input_tailwind_classes, "style": select_input_styles}),
    )


class SearchForm(forms.Form):
    type = forms.ChoiceField(
        label="Type",
        choices=RefType.TYPES,
        required=False,
        widget=forms.Select(attrs={"class": select_input_tailwind_classes}),
    )
    type_query = forms.CharField(label="Type Query", max_length=50, required=False)

    text_query = forms.CharField(label="Text Query", max_length=100, required=False)

    chapter_choices = list(get_chapters())
    max_choice = len(chapter_choices) - 2

    first_chapter = forms.TypedChoiceField(
        label="First Chapter",
        choices=chapter_choices,
        required=True,
        initial=0,
        widget=forms.Select(attrs={"class": select_input_tailwind_classes}),
    )

    last_chapter = forms.TypedChoiceField(
        label="Last Chapter",
        choices=chapter_choices,
        required=True,
        initial=max_choice,
        widget=forms.Select(attrs={"class": select_input_tailwind_classes}),
    )

    page_size = forms.IntegerField(
        label="Page size",
        required=False,
        initial=15,
        min_value=10,
        max_value=9999,
        widget=forms.NumberInput(attrs={"class": integer_input_tailwind_classes, "style": "width: 5rem"}),
    )

    only_colored_refs = forms.BooleanField(
        label="Only colored refs",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": checkbox_tailwind_classes}),
    )

    refs_by_chapter = forms.BooleanField(
        label="Refs by chapter",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": checkbox_tailwind_classes}),
    )

    strict_mode = forms.BooleanField(
        label="Strict mode",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": checkbox_tailwind_classes}),
    )
