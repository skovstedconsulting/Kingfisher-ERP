from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from documents.models.purchase import PurchaseDocument, PurchaseLine
from documents.models.proxies import PurchaseOrder, PurchaseInvoice

class PurchaseLineInline(admin.TabularInline):
    model = PurchaseLine
    extra = 0

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

    @admin.action(description="Post purchase invoice")
    def post_invoice(self, request, queryset):
        for doc in queryset:
            doc.post(by_user=request.user)
            doc.save()
