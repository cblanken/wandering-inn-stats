from django import forms


class SelectRefType(forms.Form):
    target_reftype = forms.TypedChoiceField(
        label="RefType", required=True, widget=forms.Select(attrs={"style": "max-width: 800px; height: 1.5rem"})
    )

    def __init__(self, *args, **kwargs):  # noqa
        rt_choices = kwargs.pop("rt_choices", ())
        super().__init__(*args, **kwargs)
        self.fields["target_reftype"].choices = rt_choices
