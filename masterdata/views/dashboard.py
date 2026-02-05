from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from core.models import Entity
from core.models.base_context import base_context
from masterdata.forms.itemForm import ItemForm
from masterdata.models import Item, ItemGroup
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone
from datetime import date, datetime , timedelta
from core.models.base_context import base_context
import json

import logging
logger = logging.getLogger(__name__)
   
def to_date(value):
    if value is None:
        return None
    # datetime is a subclass of date, so check datetime first
    if isinstance(value, datetime):
        return value.date()
    return value  # already a date


def fy_bounds(fy_year: int) -> tuple[date, date]:
    """
    Calendar financial year.
    FY 2026 => 2026-01-01 .. 2026-12-31
    """
    start = date(fy_year, 1, 1)
    end = date(fy_year, 12, 31)
    return start, end


import logging
logger = logging.getLogger(__name__)

@login_required
def dashboard(request):
    entity = request.user.profile.entity
    today = timezone.now().date()
    current_fy = today.year
    fy_options = list(range(current_fy - 5, current_fy + 1))

    try:
        selected_fy = int(request.GET.get("fy") or current_fy)
    except ValueError:
        selected_fy = current_fy

    start_date, end_date = fy_bounds(selected_fy)
    months = [date(selected_fy, m, 1) for m in range(1, 13)]

    revenue_monthly = []
    expenses_monthly = []
    invoice_counts = {"draft": 0, "posted": 0, "paid": 0}

    try:
        from documents.models.proxies import SalesInvoice, PurchaseInvoice

        sales_qs = SalesInvoice.objects.filter(
            entity=entity,
            date__gte=start_date,
            date__lte=end_date,
        ).filter(state__in=["posted", "paid", "partly_paid"])

        revenue_monthly = (
            sales_qs
            .annotate(m=TruncMonth("date"))
            .values("m")
            .annotate(total=Sum("total_base"))
        )

        purchase_qs = PurchaseInvoice.objects.filter(
            entity=entity,
            date__gte=start_date,
            date__lte=end_date,
        ).filter(state__in=["posted", "paid", "partly_paid"])

        expenses_monthly = (
            purchase_qs
            .annotate(m=TruncMonth("date"))
            .values("m")
            .annotate(total=Sum("total_base"))
        )

        base_inv = SalesInvoice.objects.filter(
            entity=entity,
            date__gte=start_date,
            date__lte=end_date,
        )

        invoice_counts["draft"] = base_inv.filter(state="invoice").count()
        invoice_counts["posted"] = base_inv.filter(state="posted").count()
        invoice_counts["paid"] = base_inv.filter(state="paid").count()

    except Exception:
        logger.exception("Dashboard query failed")

    rev_map = {to_date(r["m"]): (r["total"] or 0) for r in revenue_monthly}
    exp_map = {to_date(e["m"]): (e["total"] or 0) for e in expenses_monthly}

    series = []
    revenue_total = expenses_total = 0

    for dt in months:
        rev = rev_map.get(dt, 0)
        exp = exp_map.get(dt, 0)
        revenue_total += rev
        expenses_total += exp
        series.append({
            "month": dt.strftime("%Y-%m"),
            "revenue": float(rev),
            "expenses": float(exp),
            "result": float(rev - exp),
        })

    context = {
        **base_context(request),
        "entity": entity,
        "fy_options": fy_options,
        "selected_fy": selected_fy,
        "fy_start": start_date,
        "fy_end": end_date,
        "revenue_total": revenue_total,
        "expenses_total": expenses_total,
        "result_total": revenue_total - expenses_total,
        "invoice_posted": invoice_counts["posted"],
        "invoice_paid": invoice_counts["paid"],
        "invoice_draft": invoice_counts["draft"],
        "series_json": json.dumps(series),
    }
    return render(request, "masterdata/dashboard.html", context)
