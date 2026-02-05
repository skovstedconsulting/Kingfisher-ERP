from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from core.models import Entity
from core.models.base_context import base_context
from masterdata.forms.itemForm import ItemForm

from masterdata.models import Item, ItemGroup
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from datetime import date, datetime , timedelta

from core.models.base_context import base_context

@login_required
def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    return render(request, "masterdata/item_detail.html", {"item": item})


@login_required
def item_list(request):
    entity = request.user.profile.entity

    if request.method == "POST":
        form = ItemForm(request.POST, entity=entity)
        if form.is_valid():
            item = form.save(commit=False, entity=entity)
            item.entity = entity
            item.save()
            messages.success(request, f"Item created: {item.number}")
            return redirect("masterdata:item-list")

    else:
        form = ItemForm(entity=entity)

    items = (
        Item.objects
        .filter(entity=entity)
        .select_related("group")
        .order_by("number")
    )

    return render(request, "masterdata/item_list.html", {"items": items, "form": form, **base_context(request),})

@login_required
def item_delete(request, pk):
    if request.method != "POST":
        return redirect("masterdata:item-list")

    item = get_object_or_404(Item, pk=pk)
    item_number = item.number
    item.delete()

    messages.success(request, f"Item deleted: {item_number}")
    return redirect("masterdata:item-list")
   
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

    # Build months axis: Jan → Dec
    months = [date(selected_fy, m, 1) for m in range(1, 13)]

    revenue_monthly = []
    expenses_monthly = []
    invoice_counts = {"open": 0, "paid": 0, "draft": 0}

    try:
        from documents.models.proxies import SalesInvoice, PurchaseInvoice

        sales_qs = SalesInvoice.objects.filter(
            entity=entity,
            date__gte=start_date,
            date__lte=end_date,
        )

        if hasattr(SalesInvoice, "status"):
            sales_qs = sales_qs.filter(status__in=["POSTED", "PAID", "OPEN"])
            status_field = "status"
        else:
            status_field = "state"

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
        )

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

        invoice_counts["draft"] = base_inv.filter(**{f"{status_field}": "DRAFT"}).count()
        invoice_counts["open"] = base_inv.filter(**{f"{status_field}": "OPEN"}).count()
        invoice_counts["paid"] = base_inv.filter(**{f"{status_field}": "PAID"}).count()

    except Exception:
        pass

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
        "entity": entity,
        "fy_options": fy_options,
        "selected_fy": selected_fy,
        "fy_start": start_date,
        "fy_end": end_date,
        "revenue_total": revenue_total,
        "expenses_total": expenses_total,
        "result_total": revenue_total - expenses_total,
        "invoice_open": invoice_counts["open"],
        "invoice_paid": invoice_counts["paid"],
        "invoice_draft": invoice_counts["draft"],
        "series_json": json.dumps(series),
    }

    #return render(request, "masterdata/dashboard.html", context)
    
    return render(request, "masterdata/dashboard.html", {
        **base_context(request),
    
    })