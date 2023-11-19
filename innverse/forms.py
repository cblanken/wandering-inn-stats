from django import forms
from stats.models import RefType, Chapter

MAX_CHAPTER_NUM = int(Chapter.objects.all().order_by("-number")[0].number)


def get_chapters():
    yield (0, "--- First Chapter ---")
    for tup in ((c.number, c.title) for c in Chapter.objects.all().order_by("number")):
        yield tup
    yield (MAX_CHAPTER_NUM + 1, "--- Last Chapter ---")


select_input_tailwind_classes = "bg-bg-primary text-text-primary border-none"


class SearchForm(forms.Form):
    type = forms.ChoiceField(
        label="Type",
        choices=RefType.TYPES,
        required=False,
        widget=forms.Select(attrs={"class": select_input_tailwind_classes}),
    )
    type_query = forms.CharField(label="Type Query", max_length=50, required=False)
    text_query = forms.CharField(label="Text Query", max_length=100, required=False)
    first_chapter = forms.TypedChoiceField(
        label="First Chapter",
        choices=get_chapters,
        empty_value=8,
        required=False,
        initial=0,
        widget=forms.Select(attrs={"class": select_input_tailwind_classes}),
    )
    last_chapter = forms.TypedChoiceField(
        label="Last Chapter",
        choices=get_chapters,
        empty_value=MAX_CHAPTER_NUM,
        required=False,
        initial=MAX_CHAPTER_NUM + 1,
        widget=forms.Select(attrs={"class": select_input_tailwind_classes}),
    )
