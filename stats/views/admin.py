from django.db.utils import IntegrityError
from django.db.models import Model, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView
from stats.forms import SelectForeignModelForm
from stats.models import RefType, Alias, TextRef, RefTypeChapter, Book, Chapter
from stats.enums import AdminActionTypes


def merge_reftypes(qs: QuerySet[RefType], target_rt: RefType, *, make_alias: bool) -> None:
    # TODO: error handling
    # - Detect different RefType categories
    for orig_rt in qs:
        aliases = Alias.objects.filter(ref_type=orig_rt)
        for a in aliases:
            try:
                a.ref_type = target_rt
                a.save()
                print(f"Moved Alias {a.name} from {orig_rt.name} RefType to {target_rt.name}")
            except IntegrityError:
                print(f"Alias {a} for RefType {target_rt.name} already exists. Skipping making this alias.")

        textrefs = TextRef.objects.filter(type=orig_rt)
        for tr in textrefs:
            tr.type = target_rt
            tr.save()
            print(f"Moved TextRef {tr.chapter_line.text} from {orig_rt.name} RefType to {target_rt.name}")

        reftype_chapters = RefTypeChapter.objects.filter(type=orig_rt)
        for rt_ch in reftype_chapters:
            try:
                rt_ch.type = target_rt
                rt_ch.save()
                print(f"Moved RefTypeChapter {rt_ch} from {orig_rt.name} RefType to {target_rt.name}")
            except IntegrityError:
                print(f"RefTypeChapter already exists for {target_rt}")

        name = orig_rt.name
        orig_rt.delete()

        if make_alias:
            try:
                Alias.objects.create(name=name, ref_type=target_rt)
                print(f"RefType {name} converted to Alias of {target_rt.name}")
            except IntegrityError:
                print(f"Alias of {name} for RefType {target_rt.name} already exists so not created")

        print(f"RefType {name} merged with {target_rt.name}")


def move_chapters_to_book(chapters: QuerySet[Chapter], book: Book) -> None:
    for c in chapters:
        c.book = book
        c.save()
        print(f"Moved chapter {c} to Book {book}")


class SelectForeignModelView(TemplateView):
    """
    admin: needed for admin site context
    base_model: the model used for selecting items in the admin dashboard
    field: the foreign key field (of `base_model`) required for the built-in AutocompleteSelect widget
    select_model: the model to populate the selection items of the widget
    qs_model: the queryset type selected from in the admin dashboard

    Ideally this view is used when selecting a foreign key attribute and doing some operation
    to update the `base_model` items, but it can also be used with an arbitrary `base_model`
    if a specific set of `select_model` records needs to be selected from. Just provided the correct
    `qs_model` per the actual selection made in the admin dashboard.
    """

    admin = {}
    template_name = "custom_admin/select_book.html"
    base_model: type[Model] | None = None
    field: str | None = None
    select_model: type[Model] | None = None
    qs_model: type[Model] | None = None

    def post(self, request: HttpRequest):  # noqa: ANN201
        if self.base_model is None or self.select_model is None or self.field is None:
            msg = "The qs_model, select_model, and field for the SelectForeignModelView must all be specified"
            raise ValueError(msg)

        if self.qs_model is None:
            self.qs_model = self.base_model

        ids = request.GET.get("ids")
        try:
            if ids:
                queryset_ids = list(map(int, ids.split(",")))
                queryset = self.qs_model.objects.filter(pk__in=queryset_ids)
        except ValueError as e:
            msg = "Invalid Chapter ID in {qs_param}"
            raise ValueError(msg) from e

        form = SelectForeignModelForm(self.base_model, self.field, request.POST)  # type: ignore
        action = request.GET.get("action")
        return_url = request.GET.get("return_url", "")

        if form.data.get("confirm") == "yes":
            selected_model_id = int(form.data.get("model_id"))

            match (action, self.select_model, self.base_model):
                case (AdminActionTypes.MOVE_CHAPTERS.value, Book._meta.model, Chapter._meta.model):
                    book = Book.objects.get(pk=selected_model_id)
                    move_chapters_to_book(queryset, book)
                    return HttpResponseRedirect(return_url)
                case (AdminActionTypes.MERGE_REFTYPES_WITH_ALIAS.value, RefType._meta.model, *_):
                    merge_reftypes(queryset, RefType.objects.get(pk=selected_model_id), make_alias=True)
                    return HttpResponseRedirect(return_url)
                case (AdminActionTypes.MERGE_REFTYPES_NO_ALIAS.value, RefType._meta.model, *_):
                    merge_reftypes(queryset, RefType.objects.get(pk=selected_model_id), make_alias=False)
                    return HttpResponseRedirect(return_url)
                case _:
                    return HttpResponse("nothing to see here")

        ctx = {
            "qs": queryset,
            "form": form,
            "action": action,
            "return_url": return_url,
        }

        ctx |= self.admin.each_context(request)

        return render(request, self.template_name, ctx)
