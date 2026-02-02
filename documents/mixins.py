from django.contrib import admin, messages
from django.http import JsonResponse
from django.urls import path, reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.shortcuts import redirect
from django.db import transaction

from guardian.admin import GuardedModelAdmin
from django_object_actions import DjangoObjectActions, action

from core.models.entity import Entity
from documents.models.sales import SalesDocument, SalesLine
from documents.models.proxies import SalesOffer, SalesOrder, SalesInvoice

class SalesDocDefaultsMixin:
    readonly_fields = ("state", "posted_journal", "posted_at", "posted_by")

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)

        initial.setdefault("date", timezone.localdate())

        prof = getattr(request.user, "profile", None)
        if prof and prof.entity_id:
            initial.setdefault("entity", prof.entity_id)

        initial.setdefault("currency", "DKK")
        return initial

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if obj is None and "entity" in form.base_fields:
            prof = getattr(request.user, "profile", None)
            if prof and prof.entity_id:
                f = form.base_fields["entity"]
                f.initial = prof.entity_id
                f.queryset = Entity.objects.filter(pk=prof.entity_id)
                f.disabled = True

        return form


class SalesInlineDefaultsAdminMixin:
    """
    Exposes: item-defaults/<item_id>/ for the inline JS.
    Works for any Sales*Admin that uses SalesLineInline.
    """

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "item-defaults/<int:item_id>/",
                self.admin_site.admin_view(self.item_defaults),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_item_defaults",
            ),
        ]
        return custom + urls

    def item_defaults(self, request, item_id):
        from masterdata.models import Item  # adjust if needed

        try:
            item = Item.objects.select_related("group").get(pk=item_id)
        except Item.DoesNotExist:
            return JsonResponse(
                {"description": "", "unit_price_tx": "0.00", "vat_code": None},
                status=404,
            )

        vat = None
        if item.group_id and getattr(item.group, "default_sales_vat_code_id", None):
            vat = item.group.default_sales_vat_code_id

        return JsonResponse(
            {
                "description": item.name or "",
                "unit_price_tx": str(getattr(item, "sales_price", "0.00") or "0.00"),
                "vat_code": vat,
            }
        )
