from django.contrib import admin, messages
#from unfold.admin import site as admin_site

from django_object_actions import action
from guardian.admin import GuardedModelAdmin

from core.models.entity import Entity
from documents.models.sales import SalesDocument, SalesLine
from documents.models.purchase import PurchaseDocument, PurchaseLine
from documents.models.proxies import SalesOffer, SalesOrder, SalesInvoice, PurchaseOrder, PurchaseInvoice

from django.http import JsonResponse

from django.urls import path
from django.utils import timezone
from django.urls import reverse_lazy

from django.shortcuts import redirect
from django.db import transaction
from django_object_actions import DjangoObjectActions, action

from django.utils.html import format_html
from django.urls import reverse

class SalesLineInline(admin.TabularInline):
    model = SalesLine
    extra = 0
    fk_name = "document"

@admin.register(SalesOffer)
#class SalesOfferAdmin(GuardedModelAdmin, admin.ModelAdmin):
class SalesOfferAdmin(DjangoObjectActions, GuardedModelAdmin, admin.ModelAdmin):

    inlines = [SalesLineInline]

    list_display = ("date", "offer_no", "debtor", "state", "convert_btn")

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

        # reuse your existing method
        self.convert_to_order_action(request, obj)

        return redirect("admin:documents_salesoffer_changelist")
    
    def convert_btn(self, obj):
        url = reverse("admin:documents_salesoffer_convert_to_order", args=[obj.pk])
        return format_html('<a class="button" href="{}">Convert</a>', url)

    convert_btn.short_description = "Actions"
    
    readonly_fields = ("state", "posted_journal", "posted_at", "posted_by")

    actions_list = ('custom_list_action', )
    actions_row = ('custom_row_action', )
    actions_detail = ('custom_detail_action', )

    def custom_list_action(self, request):
        # custom logic here
        return redirect(reverse_lazy('admin:APP_MODEL_changelist'))
    custom_list_action.short_description = 'Custom name'
    custom_list_action.url_path = 'clean-url-path-1'

    def custom_row_action(self, request, pk):
        # custom logic here
        return redirect(reverse_lazy('admin:APP_MODEL_changelist'))
    custom_row_action.short_description = 'Row custom name'
    custom_row_action.url_path = 'clean-url-path-2'

    def custom_detail_action(self, request, pk):
        # custom logic here
        return redirect(reverse_lazy('admin:APP_MODEL_changelist'))
    custom_detail_action.short_description = 'Detail custom name'
    custom_detail_action.url_path = 'clean-url-path-3'
    
    
    change_actions = ("convert_to_order_action",)

    def get_change_actions(self, request, object_id, form_url):
            # Optional: show/hide buttons based on current state
            obj = self.get_object(request, object_id)
            if not obj:
                return ()
            if obj.state == SalesDocument.State.OFFER:
                return ("convert_to_order_action",)
            #if obj.state == SalesDocument.State.ORDER:
            #    return ("convert_to_invoice_action",)
            #if obj.state == SalesDocument.State.INVOICE:
            #    return ("post_action",)
            return ()

    @action(label="Convert to order", description="Convert offer to order")
    @transaction.atomic
    def convert_to_order_action(self, request, obj):
        try:
            obj.convert_to_order(by_user=request.user)
            obj.save()
            self.message_user(request, "Converted to order.", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Could not convert: {e}", level=messages.ERROR)

    class Media:
        js = ("admin/salesline_inline_defaults.js",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(state=SalesDocument.State.OFFER)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)

        # Date defaults to today (shows immediately on add form)
        initial.setdefault("date", timezone.localdate())

        # Entity defaults to user's profile entity (shows immediately on add form)
        prof = getattr(request.user, "profile", None)
        if prof and prof.entity_id:
            initial.setdefault("entity", prof.entity_id)

        initial.setdefault("currency", "DKK")  # or your default currency code

        return initial

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Only on "add" page (obj is None)
        if obj is None and "entity" in form.base_fields:
            prof = getattr(request.user, "profile", None)
            if prof and prof.entity_id:
                f = form.base_fields["entity"]
                f.initial = prof.entity_id

                # optional: only allow selecting their own entity
                f.queryset = Entity.objects.filter(pk=prof.entity_id)

                # optional: lock it (still visible)
                f.disabled = True

        return form


    def item_defaults(self, request, item_id):
        # Keep this fast + predictable (only return what you need)
        from masterdata.models import Item  # adjust import to your app
        item = Item.objects.get(pk=item_id)
    
        vat = None
        if item.group_id and item.group.default_sales_vat_code_id:
            vat = item.group.default_sales_vat_code_id  # ✅ integer / uuid etc.

        return JsonResponse({
            "description": item.name or "",
            "unit_price_tx": str(getattr(item, "sales_price", "0.00")),
            "vat_code": vat,  # ✅ serializable
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
