import json

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AutocompleteMixin, AutocompleteSelect
from django.db.models import Model, QuerySet
from django.urls import reverse


class CustomAutocompleteMixin(AutocompleteMixin):
    def __init__(self, model: type[Model], field, admin_site, *args, **kwargs) -> None:  # noqa
        super().__init__(field, admin_site, *args, **kwargs)
        self.model = model

    def get_url(self) -> str:
        return reverse(
            self.url_name % self.admin_site.name,
            query={
                "app_label": self.model._meta.app_label,
                "model_name": self.model._meta.model_name,
                # TODO: use first available field since the default Django admin autocomplete requires
                # an existing field be specified, but this won't work.
                "field_name": list(self.model._meta.fields_map.keys())[0],
            },
        )

    def build_attrs(self, base_attrs, extra_attrs=None):  # noqa
        """
        Set select2's AJAX attributes.

        Attributes can be set using the html5 data attribute.
        Nested attributes require a double dash as per
        https://select2.org/configuration/data-attributes#nested-subkey-options
        """
        # attrs = super().build_attrs(base_attrs, extra_attrs=extra_attrs)
        attrs = base_attrs or {}
        if extra_attrs is not None:
            attrs |= extra_attrs
        attrs.setdefault("class", "")
        attrs.update(
            {
                "data-ajax--cache": "true",
                "data-ajax--delay": 250,
                "data-ajax--type": "GET",
                "data-ajax--url": self.get_url(),
                # "data-app-label": self.field.model._meta.app_label,
                # "data-model-name": self.field.model._meta.model_name,
                # "data-field-name": self.field.name,
                "data-theme": "admin-autocomplete",
                "data-allow-clear": json.dumps(not self.is_required),
                "data-placeholder": "",  # Allows clearing of the input.
                "lang": self.i18n_name,
                "class": attrs["class"] + (" " if attrs["class"] else "") + "admin-autocomplete",
            }
        )
        return attrs

    def optgroups(self, name, value, attr=None):  # noqa
        """Return selected options based on the ModelChoiceIterator."""
        default = (None, [], 0)
        groups = [default]
        has_selected = False
        selected_choices = {str(v) for v in value if str(v) not in self.choices.field.empty_values}
        if not self.is_required and not self.allow_multiple_selected:
            default[1].append(self.create_option(name, "", "", False, 0))
        # remote_model_opts = self.field.remote_field.model._meta
        # to_field_name = getattr(
        #     self.field.remote_field, "field_name", remote_model_opts.pk.attname
        # )
        # to_field_name = remote_model_opts.get_field(to_field_name).attname
        choices = ((obj, str(obj)) for obj in self.model.objects.all())
        # choices = self.model.objects.all().values_list("pk", "title")
        # choices = ((obj.pk, obj) for obj in self.choices.queryset.using(self.db).filter(f"pk__in={selected_choices}"))
        for option_value, option_label in choices:
            selected = str(option_value) in value and (has_selected is False or self.allow_multiple_selected)
            has_selected |= selected
            index = len(default[1])
            subgroup = default[1]
            subgroup.append(self.create_option(name, option_value, option_label, selected_choices, index))
        return groups


class CustomAutocompleteSelect(CustomAutocompleteMixin, forms.Select):
    """Custom autocomlete Model selection widget"""


class CustomModelChoiceField(forms.ModelChoiceField):
    def __init__(self, model: type[Model], queryset: QuerySet | None = None, widget=None, **kwargs) -> None:  # noqa
        if queryset is None:
            queryset = model.objects.all()
        if widget is None:
            widget = CustomAutocompleteSelect(model, None, admin.site)
        super().__init__(queryset=queryset, widget=widget, **kwargs)


class SelectModelForm(forms.Form):
    def __init__(self, select_model: type[Model], *args, **kwargs) -> None:  # noqa
        super().__init__(*args, **kwargs)

        self.model = select_model

        self.fields["model_id"] = CustomModelChoiceField(
            model=self.model, widget=CustomAutocompleteSelect(select_model, None, admin.site), required=True
        )


class SelectForeignModelForm(forms.Form):
    def __init__(self, src_model: type[Model], fk_field: str, *args, **kwargs) -> None:  # noqa
        super().__init__(*args, **kwargs)

        if fk_field not in [f.name for f in src_model._meta.fields]:
            msg = f"The foreign key field must match an existing field in the {src_model.__name__} Model"
            raise ValueError(msg)

        self.model = src_model

        self.fields["model_id"] = forms.ModelChoiceField(
            queryset=src_model.objects.all(),
            widget=AutocompleteSelect(
                src_model._meta.get_field(fk_field),
                admin.site,
            ),
            required=True,
        )
