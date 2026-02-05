from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

from masterdata.models import Debtor
from masterdata.forms.debitorForm import DebtorForm  # create this (below)
from core.context_processors import base_context  # adjust import if needed

from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

def _add_query_param(url: str, key: str, value: str) -> str:
    """Return url with ?key=value added/replaced (works with existing querystring)."""
    parts = urlparse(url)
    qs = dict(parse_qsl(parts.query, keep_blank_values=True))
    qs[key] = str(value)
    new_query = urlencode(qs)
    return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))


@login_required
def debtor_detail(request, pk):
    entity = request.user.profile.entity
    debtor = get_object_or_404(Debtor, pk=pk, entity=entity)
    return render(request, "masterdata/debtor_detail.html", {"debtor": debtor, **base_context(request)})


@login_required
def debtor_list(request):
    entity = request.user.profile.entity
    next_url = request.POST.get("next") or request.GET.get("next")  # <-- keep both

    if request.method == "POST":
        form = DebtorForm(request.POST, entity=entity)
        if form.is_valid():
            debtor = form.save(commit=False)
            debtor.entity = entity
            debtor.save()

            messages.success(request, f"Debtor created: {debtor.number}")

            if next_url:
                # 👇 append debtor_id so sales form can preselect it
                return redirect(_add_query_param(next_url, "debtor_id", debtor.pk))

            return redirect("masterdata:debtor-list")
    else:
        form = DebtorForm(entity=entity)

    debtors = (
        Debtor.objects
        .filter(entity=entity)
        .select_related("group")
        .order_by("number")
    )

    return render(request, "masterdata/debtor_list.html", {
        "form": form,
        "debtors": debtors,
        "next": next_url,
    })


@login_required
def debtor_delete(request, pk):
    if request.method != "POST":
        return redirect("masterdata:debtor-list")

    entity = request.user.profile.entity
    debtor = get_object_or_404(Debtor, pk=pk, entity=entity)
    debtor_number = debtor.number
    debtor.delete()

    messages.success(request, f"Debtor deleted: {debtor_number}")
    return redirect("masterdata:debtor-list")
