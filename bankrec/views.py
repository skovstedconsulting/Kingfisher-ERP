from __future__ import annotations

import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count
from .models import BankReconciliationSession, BankStatementStagingLine, BankMatch

from ledger.models.journal_line import JournalLine 

from decimal import Decimal, ROUND_HALF_UP

from .models import BankMatchBankLine, BankMatchJournalLine

@staff_member_required
def reconcile_view(request, session_id: int):
    session = get_object_or_404(BankReconciliationSession, id=session_id)

    matches = (
        session.matches
        .prefetch_related("bank_lines", "gl_lines")
        .order_by("-created_at")
    )

    # ✅ ALL bank lines for the statement (matched + unmatched)
    bank_lines = (
        BankStatementStagingLine.objects
        .filter(header=session.staging)
        .order_by("booking_date", "id")
    )

    # ✅ ALL GL lines on the configured bank account (matched + unmatched)
    gl_lines = (
        JournalLine.objects
        .select_related("journal")
        .filter(
            journal__entity_id=session.entity_id,
            account_id=session.setup.gl_bank_account_id,
        )
        .order_by("journal__date", "id")
    )

    return render(
        request,
        "bankrec/reconcile.html",
        {
            "session": session,
            "bank_lines": bank_lines,
            "gl_lines": gl_lines,
            "matches": matches,
        },
    )


def q2(x: Decimal) -> Decimal:
    return (x or Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def gl_signed_amount(gl: JournalLine) -> Decimal:
    # signed base amount on bank account line
    return q2(q2(gl.debit_base) - q2(gl.credit_base))



@staff_member_required
@require_POST
@csrf_protect
def match_create(request, session_id: int):
    session = get_object_or_404(BankReconciliationSession, id=session_id)

    bank_ids: list[int] = []
    gl_ids: list[int] = []

    try:
        payload = json.loads(request.body.decode("utf-8"))

        print (payload)

        # BANK
        if "bank_line_ids" in payload:
            bank_ids = [int(x) for x in payload["bank_line_ids"]]
        elif "bank_line_id" in payload:
            bank_ids = [int(payload["bank_line_id"])]

        print(bank_ids)

        # GL (accept multiple key names for compatibility)
        if "gl_line_ids" in payload:
            gl_ids = [int(x) for x in payload["gl_line_ids"]]
        elif "gl_line_id" in payload:
            gl_ids = [int(payload["gl_line_id"])]

        print(gl_ids)

        #elif "gl_entry_id" in payload:
        #    gl_ids = [int(payload["gl_entry_id"])]
        #elif "journal_line_ids" in payload:
        #    gl_ids = [int(x) for x in payload["journal_line_ids"]]
        #elif "journal_line_id" in payload:
        #    gl_ids = [int(payload["journal_line_id"])]

    except Exception:
        print("debug 1")
        return HttpResponseBadRequest("Invalid payload")

    if not bank_ids or not gl_ids:
        print("debug 2")
        return HttpResponseBadRequest("bank_line_ids and gl_lines are required")


    # --- GLOBAL UNIQUENESS (B) ---
    used_bank = BankMatchBankLine.objects.filter(bank_line_id__in=bank_ids)
        
    print("Debug 3")
    print(used_bank)
    print("Debut 4")

    if used_bank.exists():
        return JsonResponse(
            {"ok": False, "error": "already_matched", "kind": "bank",
             "ids": list(used_bank.values_list("bank_line", flat=True))},
            status=400,
        )

    print ("Debug 5")

    used_gl = BankMatchJournalLine.objects.filter(gl_line__in=gl_ids)
    
    if used_gl.exists():
        return JsonResponse(
            {"ok": False, "error": "already_matched", "kind": "gl",
             "ids": list(used_gl.values_list("gl_line", flat=True))},
            status=400,
        )

    # --- Load lines ---
    bank_lines = list(
        BankStatementStagingLine.objects.filter(id__in=bank_ids, header=session.staging)
    )
    if len(bank_lines) != len(set(bank_ids)):
        return HttpResponseBadRequest("One or more bank lines not found in this session")

    journal_lines = list(
        JournalLine.objects.select_related("journal").filter(id__in=gl_ids)
    )
    if len(journal_lines) != len(set(gl_ids)):
        return HttpResponseBadRequest("One or more GL lines not found")

    # --- Security ---
    for gl in journal_lines:
        if gl.journal.entity_id != session.entity_id:
            return HttpResponseBadRequest("GL line entity mismatch")
        if gl.account_id != session.setup.gl_bank_account_id:
            return HttpResponseBadRequest("GL line is not on configured bank account")

    # --- Amount check ---
    bank_sum = q2(sum((Decimal(str(bl.amount)) for bl in bank_lines), Decimal("0")))
    gl_sum = q2(sum((gl_signed_amount(gl) for gl in journal_lines), Decimal("0")))

    if bank_sum != gl_sum:
        return JsonResponse(
            {"ok": False, "error": "amount_mismatch",
             "bank_amount": str(bank_sum), "gl_amount": str(gl_sum)},
            status=400,
        )

    # --- Create match ---
    match = BankMatch.objects.create(session=session, created_by=request.user)
    match.bank_lines.add(*bank_lines, through_defaults={"matched_amount": None})
    match.gl_lines.add(*journal_lines, through_defaults={"matched_amount": None})

    return JsonResponse(
        {"ok": True, "match_id": match.id,
         "bank_lines": bank_ids, "gl_lines": gl_ids,
         "bank_amount": str(bank_sum), "gl_amount": str(gl_sum)}
    )


@staff_member_required
@require_POST
@csrf_protect
def match_delete(request, session_id: int):
    session = get_object_or_404(BankReconciliationSession, id=session_id)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        match_id = int(payload["match_id"])
    except Exception:
        return HttpResponseBadRequest("Invalid payload")

    match = get_object_or_404(BankMatch, id=match_id, session=session)
    match.delete()

    return JsonResponse({"ok": True})

@staff_member_required
def session_list(request):
    qs = (
        BankReconciliationSession.objects
        .select_related("entity", "setup", "staging")
        .annotate(match_count=Count("matches"))
        .order_by("-created_at")
    )

    # (valgfrit) filter
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    entity_id = request.GET.get("entity")
    if entity_id:
        qs = qs.filter(entity_id=entity_id)

    return render(request, "bankrec/session_list.html", {
        "sessions": qs,
        "status": status or "",
        "entity_id": entity_id or "",
    })