from django import forms
from stats.models import RefType, Chapter

MAX_CHAPTER_NUM = int(Chapter.objects.all().order_by("-number")[0].number)


def get_chapters():
    return ((c.number, c.title) for c in Chapter.objects.all().order_by("number"))


class SearchForm(forms.Form):
    type = forms.ChoiceField(label="Type", choices=RefType.TYPES, required=False)
    type_query = forms.CharField(label="Type Query", max_length=50, required=False)
    text_query = forms.CharField(label="Text Query", max_length=100, required=False)
    first_chapter = forms.TypedChoiceField(
        label="First Chapter",
        choices=get_chapters,
        empty_value=8,
        required=False,
        initial=0,
    )
    last_chapter = forms.TypedChoiceField(
        label="Last Chapter",
        choices=get_chapters,
        empty_value=MAX_CHAPTER_NUM,
        required=False,
        initial=MAX_CHAPTER_NUM,
    )
