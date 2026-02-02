from django.contrib import admin, messages

from guardian.admin import GuardedModelAdmin

from core.models.entity import Entity
from documents.mixins import SalesInlineDefaultsAdminMixin, SalesDocDefaultsMixin

from documents.models.sales import SalesDocument, SalesLine
from documents.models.purchase import PurchaseDocument, PurchaseLine
from documents.models.proxies import SalesOffer, SalesOrder, SalesInvoice, PurchaseOrder, PurchaseInvoice

from django.http import JsonResponse

from django.urls import path
from django.utils import timezone
from django.urls import reverse_lazy

from django.shortcuts import redirect
from django.db import transaction

from django.utils.html import format_html
from django.urls import reverse

class SalesLineInline(admin.TabularInline):
    model = SalesLine
    extra = 0
    fk_name = "document"
    
    class Media:
        js = ("admin/salesline_inline_defaults.js",)

@admin.register(SalesOffer)
class SalesOfferAdmin(
    SalesInlineDefaultsAdminMixin,
    SalesDocDefaultsMixin,
    GuardedModelAdmin,
):
    exclude = (
        "posted_by", "posted_at", "total_base", "total_tx", "posted_journal",
        "credited_by", "credited_at", "paid_by", "paid_at",
        "order_no", "invoice_no", "offer_no",
    )
    inlines = [SalesLineInline]
    list_display = ("date", "debtor", "state", "convert_btn")   

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/convert-to-order/",
                self.admin_site.admin_view(self.convert_to_order_from_list),
                name="documents_salesoffer_convert_to_order",
            ),
        ]
        return custom + urls

    @transaction.atomic
    def convert_to_order_from_list(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(request, "Offer not found.", level=messages.ERROR)
            return redirect("admin:documents_salesoffer_changelist")

        try:
            obj.convert_to_order(by_user=request.user)
            obj.save()
            self.message_user(request, "Converted to order.", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Could not convert: {e}", level=messages.ERROR)

        return redirect("admin:documents_salesoffer_changelist")

    def convert_btn(self, obj):
        url = reverse("admin:documents_salesoffer_convert_to_order", args=[obj.pk])
        return format_html('<a class="button" href="{}">Convert</a>', url)
    convert_btn.short_description = "Actions"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(state=SalesDocument.State.OFFER)

    actions = ["convert_to_order"]

    @admin.action(description="Convert to order")
    def convert_to_order(self, request, queryset):
        for doc in queryset:
            doc.convert_to_order(by_user=request.user)
            doc.save()


@admin.register(SalesOrder)
class SalesOrderAdmin(
    SalesInlineDefaultsAdminMixin,
    SalesDocDefaultsMixin,
    GuardedModelAdmin,
    admin.ModelAdmin,
):
    inlines = [SalesLineInline]
    list_display = ("date", "order_no", "debtor", "state")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(state=SalesDocument.State.ORDER)

    actions = ["convert_to_invoice"]

    @admin.action(description="Convert to invoice")
    def convert_to_invoice(self, request, queryset):
        for doc in queryset:
            doc.convert_to_invoice(by_user=request.user)
            doc.save()

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(
    SalesInlineDefaultsAdminMixin,
    SalesDocDefaultsMixin,
    GuardedModelAdmin,
    admin.ModelAdmin,
):
    inlines = [SalesLineInline]
    list_display = ("display_no", "date", "debtor", "state", "total_tx", "total_base", "invoice_no")
    list_filter = ("entity", "state", "currency")
    search_fields = ("invoice_no", "order_no", "offer_no", "debtor__name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(invoice_no__gt="").filter(
            state__in=[
                SalesDocument.State.INVOICE,
                SalesDocument.State.POSTED,
                SalesDocument.State.PARTLY_PAID,
                SalesDocument.State.PAID,
            ]
        )

    actions = ["post_invoice"]

    @admin.action(description="Post invoice")
    def post_invoice(self, request, queryset):
        for doc in queryset:
            doc.post(by_user=request.user)
            doc.save()

class PurchaseLineInline(admin.TabularInline):
    model = PurchaseLine
    extra = 0
    fk_name = "document"

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(GuardedModelAdmin, admin.ModelAdmin):
    inlines = [PurchaseLineInline]
    list_display = ("date", "order_no", "creditor", "state")
    readonly_fields = ("state", "posted_journal", "posted_at", "posted_by")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(state=PurchaseDocument.State.ORDER)

    actions = ["convert_to_invoice"]

    @admin.action(description="Convert to invoice")
    def convert_to_invoice(self, request, queryset):
        for doc in queryset:
            doc.convert_to_invoice(by_user=request.user)
            doc.save()

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(GuardedModelAdmin, admin.ModelAdmin):
    inlines = [PurchaseLineInline]
    list_display = ("date", "invoice_no", "creditor", "state")
    readonly_fields = ("state", "posted_journal", "posted_at", "posted_by")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(state=PurchaseDocument.State.INVOICE)

    actions = ["post_invoice"]

    @admin.action(description="Post invoice")
    def post_invoice(self, request, queryset):
        for doc in queryset:
            doc.post(by_user=request.user)
            doc.save()
