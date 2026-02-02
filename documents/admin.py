from django.contrib import admin
#from unfold.admin import site as admin_site

from guardian.admin import GuardedModelAdmin

from documents.models.sales import SalesDocument, SalesLine
from documents.models.purchase import PurchaseDocument, PurchaseLine
from documents.models.proxies import SalesOffer, SalesOrder, SalesInvoice, PurchaseOrder, PurchaseInvoice

from django.http import JsonResponse

from django.urls import path

class SalesLineInline(admin.TabularInline):
    model = SalesLine
    extra = 0
    fk_name = "document"

@admin.register(SalesOffer)
class SalesOfferAdmin(GuardedModelAdmin, admin.ModelAdmin):
    inlines = [SalesLineInline]
    list_display = ("date", "offer_no", "debtor", "state")
    readonly_fields = ("state", "posted_journal", "posted_at", "posted_by")

    class Media:
        js = ("admin/salesline_inline_defaults.js",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(state=SalesDocument.State.OFFER)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "item-defaults/<int:item_id>/",
                self.admin_site.admin_view(self.item_defaults),
                name="sales_item_defaults",
            )
        ]
        return custom + urls

    def item_defaults(self, request, item_id):
        # Keep this fast + predictable (only return what you need)
        from masterdata.models import Item  # adjust import to your app
        item = Item.objects.get(pk=item_id)

        return JsonResponse({
            "description": item.name or "",
            "unit_price_tx": str(getattr(item, "sales_price", "0.00")),  # adjust field name if needed
            # "vat_code_id": item.vat_code_id if you want to set VAT too
        })
    
    actions = ["convert_to_order"]

    @admin.action(description="Convert to order")
    def convert_to_order(self, request, queryset):
        for doc in queryset:
            doc.convert_to_order(by_user=request.user)
            doc.save()

@admin.register(SalesOrder)
class SalesOrderAdmin(GuardedModelAdmin, admin.ModelAdmin):
    inlines = [SalesLineInline]
    list_display = ("date", "order_no", "debtor", "state")
    readonly_fields = ("state", "posted_journal", "posted_at", "posted_by")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(state=SalesDocument.State.ORDER)

    actions = ["convert_to_invoice"]

    @admin.action(description="Convert to invoice")
    def convert_to_invoice(self, request, queryset):
        for doc in queryset:
            doc.convert_to_invoice(by_user=request.user)
            doc.save()

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(GuardedModelAdmin, admin.ModelAdmin):
    inlines = [SalesLineInline]
    list_display = ("display_no", "date", "debtor", "state", "total_tx", "total_base", "invoice_no")
    readonly_fields = ("state", "posted_journal", "posted_at", "posted_by")
    list_filter = ("entity", "state", "currency")
    search_fields = ("invoice_no", "order_no", "offer_no", "debtor__name")
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.filter(
            # still invoices
            invoice_no__gt=""
        ).filter(
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
