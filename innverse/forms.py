from django import forms
from stats.models import RefType


class SearchForm(forms.Form):
    type = forms.ChoiceField(label="Type", choices=RefType.TYPES)
    type_query = forms.CharField(label="Type Query", max_length=50, required=False)
    text_query = forms.CharField(label="Text Query", max_length=100, required=False)
