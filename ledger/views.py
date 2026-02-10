from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from ledger.models.journal import Journal
from datetime import date as date_type
from django.db import models, transaction
from .forms import JournalForm, JournalLineFormSet
from ledger.models.journal_line import JournalLine


# views.py
@login_required
@require_http_methods(["GET", "POST"])
def journal_edit(request, pk: int):
    entity = request.user.profile.entity

    journal = get_object_or_404(
        Journal.objects.select_related("entity"),
        pk=pk,
        entity=entity,
    )

    if journal.state != Journal.State.DRAFT:
        messages.error(request, "Posted journals cannot be edited.")
        return redirect("ledger:journal-detail", pk=journal.pk)

    
    if request.method == "POST":
        form = JournalForm(request.POST, instance=journal, entity=entity)
        formset = JournalLineFormSet(request.POST, instance=journal)

        if form.is_valid() and formset.is_valid():
            journal = form.save()
            formset.instance = journal
            formset.save()


            return redirect("ledger:journal-detail", pk=journal.pk)
        else:
            messages.error(request, "Could not save. Please fix the errors shown in the form.")
    else:
        form = JournalForm(instance=journal, entity=entity)
        formset = JournalLineFormSet(instance=journal)

    return render(
        request,
        "ledger/journal_form.html",
        {
            "form": form,
            "formset": formset,
            "journal": journal,
            "mode": "edit",
        },
    )



@login_required
@require_http_methods(["GET"])
def journal_list(request):
    entity = request.user.profile.entity

    state = (request.GET.get("state") or "").strip().lower()  # draft|posted|all
    day_str = (request.GET.get("day") or "").strip()          # YYYY-MM-DD

    qs = (
        Journal.objects
        .filter(entity=entity)
        .select_related("posted_by")
        .order_by("-date", "-id")
    )

    if state in (Journal.State.DRAFT, Journal.State.POSTED):
        qs = qs.filter(state=state)

    if day_str:
        qs = qs.filter(date=day_str)

    # optional: show quick counts
    counts = (
        Journal.objects
        .filter(entity=entity)
        .values("state")
        .annotate(n=models.Count("id"))
    )
    count_map = {row["state"]: row["n"] for row in counts}

    return render(
        request,
        "ledger/journal_list.html",
        {
            "journals": qs,
            "state": state or "all",
            "day": day_str,
            "count_draft": count_map.get(Journal.State.DRAFT, 0),
            "count_posted": count_map.get(Journal.State.POSTED, 0),
        },
    )


@login_required
@require_http_methods(["POST"])
def journal_post_all_drafts_for_day(request):
    """
    Posts ALL draft journals for a specific day (YYYY-MM-DD) for the user's entity.
    Skips journals that fail (unbalanced, etc.) and reports summary.
    """
    entity = request.user.profile.entity
    day_str = (request.POST.get("day") or "").strip()

    if not day_str:
        messages.error(request, "Missing day (YYYY-MM-DD).")
        return redirect("ledger:journal-list")

    # Lock all candidates in a stable order to reduce deadlocks
    candidates = (
        Journal.objects
        .select_for_update()
        .filter(entity=entity, state=Journal.State.DRAFT, date=day_str)
        .order_by("id")
    )

    posted = 0
    failed = 0
    fail_msgs = []

    with transaction.atomic():
        for j in candidates:
            try:
                j.post(by_user=request.user)
                posted += 1
            except Exception as e:
                failed += 1
                # keep message short
                fail_msgs.append(f"{j.number or j.pk}: {e}")

    if posted:
        #messages.success(request, f"Posted {posted} draft journal(s) for {day_str}.")
        messages.success(
            request,
            f'Posted {posted} journals for {day_str}. '
            f'<a href="{reverse("ledger:journal-list")}?day={day_str}&state=posted">View posted journals</a>'
        )
    if failed:
        messages.warning(request, f"Failed to post {failed} journal(s): " + " | ".join(fail_msgs[:5]))

    return redirect(f"{redirect('ledger:journal-list').url}?day={day_str}&state=draft")


def _q2(x: Decimal) -> Decimal:
    return (x or Decimal("0.00")).quantize(Decimal("0.01"))


def entity_base_currency_id(entity) -> int | None:
    """
    Adjust this if your Entity model uses a different field name.
    Common options: entity.base_currency_id, entity.currency_id, entity.base_currency.code etc.
    """
    if hasattr(entity, "base_currency_id"):
        return entity.base_currency_id
    if hasattr(entity, "currency_id"):
        return entity.currency_id
    return None


@login_required
@require_http_methods(["GET", "POST"])
def journal_create(request):
    entity = request.user.profile.entity
    base_currency_id = entity_base_currency_id(entity)

    if request.method == "POST":
        form = JournalForm(request.POST, entity=entity)
        formset = JournalLineFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            auto_fill_base = form.cleaned_data.get("auto_fill_base", True)
            auto_balance = form.cleaned_data.get("auto_balance", False)
            balancing_account = form.cleaned_data.get("balancing_account")
            balancing_description = form.cleaned_data.get("balancing_description") or "Auto balance"

            with transaction.atomic():
                journal = form.save(commit=False)
                journal.entity = entity
                journal.save()

                # Build line instances but DO NOT save yet (so we can modify)
                instances = formset.save(commit=False)

                # Delete any removed lines
                for obj in formset.deleted_objects:
                    obj.delete()

                # 1) Auto-fill base from tx for base-currency lines
                if auto_fill_base:
                    for ln in instances:
                        # Treat blank currency as base
                        ln_cur_id = ln.currency_id
                        is_base = (ln_cur_id is None) or (base_currency_id is not None and ln_cur_id == base_currency_id)

                        if is_base:
                            # If base fields are zero but tx has value → copy
                            if _q2(ln.debit_base) == Decimal("0.00") and _q2(ln.debit_tx) != Decimal("0.00"):
                                ln.debit_base = _q2(ln.debit_tx)
                            if _q2(ln.credit_base) == Decimal("0.00") and _q2(ln.credit_tx) != Decimal("0.00"):
                                ln.credit_base = _q2(ln.credit_tx)

                            # Optionally also copy the other way if user typed base but not tx
                            if _q2(ln.debit_tx) == Decimal("0.00") and _q2(ln.debit_base) != Decimal("0.00"):
                                ln.debit_tx = _q2(ln.debit_base)
                            if _q2(ln.credit_tx) == Decimal("0.00") and _q2(ln.credit_base) != Decimal("0.00"):
                                ln.credit_tx = _q2(ln.credit_base)

                # Ensure FK set
                for ln in instances:
                    ln.journal = journal

                # Compute totals (base)
                debit_total = sum((_q2(l.debit_base) for l in instances), Decimal("0.00"))
                credit_total = sum((_q2(l.credit_base) for l in instances), Decimal("0.00"))
                diff = _q2(debit_total - credit_total)  # + => debit heavy, - => credit heavy

                # 2) Optional balancing line
                if diff != Decimal("0.00") and auto_balance:
                    if not balancing_account:
                        # No account chosen → fail cleanly
                        messages.error(request, "Journal is not balanced. Select a balancing account or uncheck auto-balance.")
                        transaction.set_rollback(True)
                        #return render(request, "ledger/journal_create.html", {"form": form, "formset": formset})
                        return render(request, "ledger/journal_form.html", {"form": form, "formset": formset, "mode": "create", "journal": None})
                    bal = JournalLine(
                        journal=journal,
                        account=balancing_account,
                        description=balancing_description,
                        currency_id=base_currency_id,  # base
                        fx_rate=None,
                        debit_tx=Decimal("0.00"),
                        credit_tx=Decimal("0.00"),
                        debit_base=Decimal("0.00"),
                        credit_base=Decimal("0.00"),
                    )

                    # If diff > 0: debit > credit → need extra CREDIT
                    # If diff < 0: credit > debit → need extra DEBIT
                    if diff > 0:
                        bal.credit_base = diff
                        bal.credit_tx = diff
                    else:
                        bal.debit_base = -diff
                        bal.debit_tx = -diff

                    instances.append(bal)

                # Save all lines
                for ln in instances:
                    ln.save()

                # Save any m2m if your formset had them (it doesn’t here, but harmless)
                formset.save_m2m()


            messages.success(
                request,
                f'Journal created. <a href="{reverse("ledger:journal-detail", args=[journal.pk])}">View journal</a>'
)
            return redirect("ledger:journal-detail", pk=journal.pk)
    else:
        form = JournalForm(entity=entity)
        formset = JournalLineFormSet()


    return render(
        request,
        "ledger/journal_form.html",
        {"form": form, "formset": formset, "mode": "create", "journal": None},
)

def apply_autofill_and_balance(*, request, journal, lines, form):
    entity = request.user.profile.entity
    base_currency_id = entity_base_currency_id(entity)

    auto_fill_base = form.cleaned_data.get("auto_fill_base", True)
    auto_balance = form.cleaned_data.get("auto_balance", False)
    balancing_account = form.cleaned_data.get("balancing_account")
    balancing_description = form.cleaned_data.get("balancing_description") or "Auto balance"

    # 1) auto-fill base for base-currency lines
    if auto_fill_base:
        for ln in lines:
            ln_cur_id = ln.currency_id
            is_base = (ln_cur_id is None) or (base_currency_id is not None and ln_cur_id == base_currency_id)
            if is_base:
                if _q2(ln.debit_base) == Decimal("0.00") and _q2(ln.debit_tx) != Decimal("0.00"):
                    ln.debit_base = _q2(ln.debit_tx)
                if _q2(ln.credit_base) == Decimal("0.00") and _q2(ln.credit_tx) != Decimal("0.00"):
                    ln.credit_base = _q2(ln.credit_tx)

                if _q2(ln.debit_tx) == Decimal("0.00") and _q2(ln.debit_base) != Decimal("0.00"):
                    ln.debit_tx = _q2(ln.debit_base)
                if _q2(ln.credit_tx) == Decimal("0.00") and _q2(ln.credit_base) != Decimal("0.00"):
                    ln.credit_tx = _q2(ln.credit_base)

    # 2) auto balance
    debit_total = sum((_q2(l.debit_base) for l in lines), Decimal("0.00"))
    credit_total = sum((_q2(l.credit_base) for l in lines), Decimal("0.00"))
    diff = _q2(debit_total - credit_total)

    if diff != Decimal("0.00") and auto_balance:
        if not balancing_account:
            raise ValueError("Auto-balance enabled, but no balancing account selected.")

        bal = JournalLine(
            journal=journal,
            account=balancing_account,
            description=balancing_description,
            currency_id=base_currency_id,
            fx_rate=None,
            debit_tx=Decimal("0.00"),
            credit_tx=Decimal("0.00"),
            debit_base=Decimal("0.00"),
            credit_base=Decimal("0.00"),
        )
        if diff > 0:
            bal.credit_base = diff
            bal.credit_tx = diff
        else:
            bal.debit_base = -diff
            bal.debit_tx = -diff

        lines.append(bal)

@login_required
@require_http_methods(["GET", "POST"])
def journal_detail(request, pk: int):
    """
    Shows a Journal with its lines.
    POST action: "post" -> calls journal.post(by_user=request.user)
    """
    entity = request.user.profile.entity  # adjust if your entity access differs

    journal = get_object_or_404(
        Journal.objects.select_related("entity", "posted_by"),
        pk=pk,
        entity=entity,
    )

    # prefetch lines + related fields to avoid N+1
    lines_qs = (
        journal.lines
        .select_related("account", "currency")
        .all()
    )

    # handy totals for UI (base)
    agg = lines_qs.aggregate(
        debit=models.Sum("debit_base"),
        credit=models.Sum("credit_base"),
    )
    debit_total = (agg["debit"] or Decimal("0.00")).quantize(Decimal("0.01"))
    credit_total = (agg["credit"] or Decimal("0.00")).quantize(Decimal("0.01"))
    is_balanced = (debit_total == credit_total)

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action != "post":
            raise Http404()

        if journal.state != Journal.State.DRAFT:
            messages.warning(request, "Journal is already posted (or not in draft).")
            return redirect("ledger:journal-detail", pk=journal.pk)

        try:
            with transaction.atomic():
                locked = (
                    Journal.objects
                    .select_for_update()
                    .get(pk=journal.pk, entity=entity)
                )

                # Recompute totals under lock
                agg2 = locked.lines.aggregate(
                    debit=models.Sum("debit_base"),
                    credit=models.Sum("credit_base"),
                )
                debit2 = (agg2["debit"] or Decimal("0.00")).quantize(Decimal("0.01"))
                credit2 = (agg2["credit"] or Decimal("0.00")).quantize(Decimal("0.01"))

                if debit2 != credit2:
                    raise ValueError(f"Journal not balanced (debit {debit2} / credit {credit2}).")

                locked.post(by_user=request.user)
                locked.save()  # <-- IMPORTANT (same as admin action)

            messages.success(request, "Journal posted.")
        except Exception as e:
            messages.error(request, f"Could not post journal: {e}")

        return redirect("ledger:journal-detail", pk=journal.pk)

    return render(
        request,
        "ledger/journal_detail.html",
        {
            "journal": journal,
            "lines": lines_qs,
            "debit_total": debit_total,
            "credit_total": credit_total,
            "is_balanced": is_balanced,
        },
    )
