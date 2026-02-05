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
   