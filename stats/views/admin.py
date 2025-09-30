from django.db.utils import IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import requires_csrf_token
from stats.forms import SelectRefType
from stats.models import RefType, Alias, TextRef, RefTypeChapter


def merge_reftypes(old_rt_ids: list[int], target_rt: RefType, *, make_alias: bool) -> None:
    for rt_id in old_rt_ids:
        orig_rt = RefType.objects.get(pk=rt_id)

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


@requires_csrf_token
def select_reftype(request: HttpRequest) -> HttpResponse:
    original_rt_ids = list(map(int, request.GET.get("ids").split(",")))
    rt_choices = RefType.objects.exclude(pk__in=original_rt_ids).values_list("pk", "name")
    if request.method == "POST":
        form = SelectRefType(request.POST, rt_choices=rt_choices)
        if form.is_valid():
            target_reftype = RefType.objects.get(pk=form.cleaned_data["target_reftype"])
            if request.GET.get("no_alias"):
                merge_reftypes(original_rt_ids, target_reftype, make_alias=False)
            else:
                merge_reftypes(original_rt_ids, target_reftype, make_alias=True)

            return HttpResponseRedirect("/admin/stats/reftype/")
    else:
        form = SelectRefType(rt_choices=rt_choices)

    return render(request, "select_reftype.html", context={"form": form, "ids": original_rt_ids})
