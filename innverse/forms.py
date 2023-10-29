from django import forms
from stats.models import RefType


class SearchForm(forms.Form):
    type = forms.ChoiceField(label="Type", choices=RefType.TYPES)
    query = forms.CharField(label="Query", max_length=100)
