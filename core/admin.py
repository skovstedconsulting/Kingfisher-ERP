from django.contrib import admin, messages
from unfold.admin import ModelAdmin

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .documents import SalesOffer, SalesOrder, SalesInvoice, SalesCreditNote, PurchaseOrder, PurchaseInvoice, PurchaseCreditNote

from .models import (
    Entity,
    FiscalYear,
    Account,
    Journal,
    JournalLine,
    IsoCountryCodes,
    IsoCurrencyCodes,    
    ChartOfAccountsTemplate, 
    ChartOfAccountsNode,
    Address,
    PaymentTerms,
    DebtorGroup,
    Debtor,
    VatCode,
    VatGroup,
    ItemGroup,
    Item,
    DocumentStatus,
    Document,
    DocumentLine,
    NumberSeries, 
)

@admin.register(Entity)
class EntityAdmin(ModelAdmin):
    list_display = ("id", "name", "country", "currency", "is_active")
    list_filter = ("country", "currency", "is_active")
    search_fields = ("name", "registration_no")

    fieldsets = (
        (_("General"), {"fields": ("name", "registration_no", "country", "currency", "is_active")}),
        (_("Finance defaults"), {"fields": ("default_ap_account",)}),
        (_("Number series"), {
            "fields": (
                "default_series_journal",
                "default_series_debtor",
                "default_series_creditor",
                "default_series_item",
                "default_series_sales_offer",
                "default_series_sales_order",
                "default_series_sales_invoice",
                "default_series_sales_credit_note",
                "default_series_purchase_order",
                "default_series_purchase_invoice",
                "default_series_purchase_credit_note",
            )
        }),
    )

    autocomplete_fields = (
        "country", "currency",
        "default_ap_account",
        "default_series_journal",
        "default_series_debtor",
        "default_series_creditor",
        "default_series_item",
        "default_series_sales_offer",
        "default_series_sales_order",
        "default_series_sales_invoice",
        "default_series_sales_credit_note",
        "default_series_purchase_order",
        "default_series_purchase_invoice",
        "default_series_purchase_credit_note",
    )

@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ("entity", "year", "start_date", "end_date", "is_closed")
    list_filter = ("entity", "is_closed")
    ordering = ("-year",)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("entity", "number", "name", "type", "is_active")
    list_filter = ("entity", "type", "is_active")
    search_fields = ("number", "name")
    ordering = ("number",)


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 1

@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ("id", "entity", "date", "posted")
    list_filter = ("entity", "posted")
    inlines = [JournalLineInline]  # if you have one
    readonly_fields = ("posted",)  # IMPORTANT: prevent toggling posted in the form
    actions = ["post_selected"]

    @admin.action(description="Post selected journals")
    def post_selected(self, request, queryset):
        ok, failed = 0, 0
        for j in queryset:
            try:
                j.post(by_user=request.user)  # your posting method with validation
                ok += 1
            except ValidationError as e:
                failed += 1
                self.message_user(request, f"Journal {j.pk} failed: {e}", level=messages.ERROR)

        if ok:
            self.message_user(request, f"Posted {ok} journal(s).", level=messages.SUCCESS)


@admin.register(IsoCountryCodes)
class IsoCountryCodesAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "alpha_3", "region", "sub_region")
    search_fields = ("code", "name", "alpha_3")
    list_filter = ("region", "sub_region")

@admin.register(IsoCurrencyCodes)
class IsoCurrencyCodesAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "iso_num", "symbol", "decimals")
    search_fields = ("code", "name")
    list_filter = ("decimals",)

class ChartOfAccountsNodeInline(admin.TabularInline):
    model = ChartOfAccountsNode
    extra = 0

@admin.register(ChartOfAccountsTemplate)
class ChartOfAccountsTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "valid_from", "source_file")
    inlines = [ChartOfAccountsNodeInline]



@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("__str__", "label", "attention", "email", "phone", "country")
    search_fields = ("label", "attention", "line1", "line2", "postal_code", "city", "email", "phone")
    list_filter = ("country",)
    ordering = ("country", "postal_code", "city", "line1")


@admin.register(PaymentTerms)
class PaymentTermsAdmin(admin.ModelAdmin):
    list_display = ("entity", "code", "name", "days")
    list_filter = ("entity",)
    search_fields = ("code", "name")
    ordering = ("entity", "code")
    autocomplete_fields = ("entity",)


@admin.register(VatCode)
class VatCodeAdmin(admin.ModelAdmin):
    list_display = ("entity", "code", "name", "rate")
    list_filter = ("entity",)
    search_fields = ("code", "name")
    ordering = ("entity", "code")
    autocomplete_fields = ("entity",)

@admin.register(VatGroup)
class VatGroupAdmin(admin.ModelAdmin):
    list_display = ("entity", "code", "name")
    list_filter = ("entity",)
    search_fields = ("code", "name")
    ordering = ("entity", "code")
    autocomplete_fields = ("entity",)

# -----------------------------
# Debtors
# -----------------------------



@admin.register(Debtor)
class DebtorAdmin(admin.ModelAdmin):
    list_display = ("entity", "number", "name", "group", "is_active", "email", "phone")
    list_filter = ("entity", "group", "is_active")
    search_fields = ("number", "name", "email", "phone", "group__code", "group__name")
    ordering = ("entity", "number")

    autocomplete_fields = (
        "entity",
        "group",
        "payment_terms",
        "billing_address",
        "delivery_address",
    )

    fieldsets = (
        (_("General"), {"fields": ("entity", "number", "name", "is_active", "group")}),
        (_("Contact"), {"fields": ("email", "phone")}),
        (_("Terms"), {"fields": ("payment_terms",)}),
        (_("Addresses"), {"fields": ("billing_address", "delivery_address")}),
    )

    # If you go with AddressLink instead, comment out the address fields above
    # and enable this inline:
    # inlines = [AddressLinkInline]


# -----------------------------
# Items
# -----------------------------

@admin.register(ItemGroup)
class ItemGroupAdmin(admin.ModelAdmin):
    list_display = (
        "entity",
        "code",
        "name",
        "default_sales_account",
        "default_vat_code",
        "number_series",
        "is_active",
    )
    list_filter = ("entity", "is_active")
    search_fields = (
        "code",
        "name",
        "default_sales_account__number",
        "default_sales_account__name",
        "default_vat_code__code",
        "default_vat_code__name",
    )
    ordering = ("entity", "code")
    autocomplete_fields = (
        "entity",
        "default_sales_account",
        "default_cogs_account",
        "default_inventory_account",
        "default_vat_code",
        "number_series",
    )

    fieldsets = (
        (_("General"), {"fields": ("entity", "code", "name", "is_active")}),
        (_("Defaults: Accounts"), {"fields": ("default_sales_account", "default_cogs_account", "default_inventory_account")}),
        (_("Defaults: VAT"), {"fields": ("default_vat_code",)}),
        (_("Defaults: Numbering"), {"fields": ("number_series",)}),
    )





@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("entity", "sku", "name", "group", "is_active", "effective_sales_account_display", "effective_vat_code_display")
    list_filter = ("entity", "group", "is_active")
    search_fields = ("sku", "name", "group__code", "group__name")
    ordering = ("entity", "sku")

    autocomplete_fields = (
        "entity",
        "group",
        "sales_account",
        "cogs_account",
        "inventory_account",
        "vat_code",
    )

    fieldsets = (
        (_("General"), {"fields": ("entity", "sku", "name", "is_active", "group")}),
        (_("Overrides: Accounts"), {"fields": ("sales_account", "cogs_account", "inventory_account")}),
        (_("Overrides: VAT"), {"fields": ("vat_code",)}),
    )

    @admin.display(description=_("Sales acct (effective)"))
    def effective_sales_account_display(self, obj):
        acc = obj.effective_sales_account
        return str(acc) if acc else ""

    @admin.display(description=_("VAT (effective)"))
    def effective_vat_code_display(self, obj):
        vat = obj.effective_vat_code
        return str(vat) if vat else ""


@admin.register(DocumentStatus)
class DocumentStatusAdmin(ModelAdmin):
    list_display = ("entity", "doc_type", "code", "name", "is_default", "is_final", "is_active", "sort_order")
    list_filter = ("entity", "doc_type", "is_default", "is_final", "is_active")
    search_fields = ("code", "name")
    ordering = ("entity", "doc_type", "sort_order", "code")

class DocumentLineInline(admin.TabularInline):
    model = DocumentLine
    extra = 0
    autocomplete_fields = ("item", "vat_code", "sales_account", "expense_account")

    def has_add_permission(self, request, obj=None):
        if obj and obj.posted_journal_id:
            return False
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.posted_journal_id:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.posted_journal_id:
            return False
        return super().has_delete_permission(request, obj)

class BaseDocumentAdmin(ModelAdmin):
    list_display = ("id", "entity", "doc_type", "number", "date", "status", "reference", "total")
    list_filter = ("entity", "status", "date")
    search_fields = ("number", "reference")
    ordering = ("-date", "-id")
    autocomplete_fields = ("entity", "status", "debtor", "currency")

    inlines = [DocumentLineInline]
    readonly_fields = ("posted_journal", "posted_at", "posted_by")

    # Ensure status dropdown only shows valid statuses for entity+type
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "status":
            # When adding a new doc, we filter by doc_type from admin class constant
            doc_type = getattr(self, "DOC_TYPE", None)
            if doc_type:
                field.queryset = field.queryset.filter(doc_type=doc_type, is_active=True)
        return field

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and obj.number:
            ro.append("number")
        return ro

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        doc_type = getattr(self, "DOC_TYPE", None)
        return qs.filter(doc_type=doc_type) if doc_type else qs

    def save_model(self, request, obj, form, change):
        # force type from the proxy admin
        doc_type = getattr(self, "DOC_TYPE", None)
        if doc_type:
            obj.doc_type = doc_type
        super().save_model(request, obj, form, change)
    
    @admin.action(description="Post selected documents")
    def post_selected(self, request, queryset):
        ok, failed = 0, 0
        for doc in queryset:
            try:
                doc.post(by_user=request.user)
                ok += 1
            except ValidationError as e:
                failed += 1
                self.message_user(request, f"Doc {doc.pk} failed: {e}", level="ERROR")
        if ok:
            self.message_user(request, f"Posted {ok} document(s).", level="SUCCESS")




@admin.register(SalesOffer)
class SalesOfferAdmin(BaseDocumentAdmin):
    DOC_TYPE = Document.DocumentType.SALES_OFFER
    list_display = ("id", "entity", "number", "date", "status", "debtor", "total")


@admin.register(SalesOrder)
class SalesOrderAdmin(BaseDocumentAdmin):
    DOC_TYPE = Document.DocumentType.SALES_ORDER
    list_display = ("id", "entity", "number", "date", "status", "debtor", "total")


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(BaseDocumentAdmin):
    DOC_TYPE = Document.DocumentType.SALES_INVOICE
    list_display = ("id", "entity", "number", "date", "status", "debtor", "total")


@admin.register(SalesCreditNote)
class SalesCreditNoteAdmin(BaseDocumentAdmin):
    DOC_TYPE = Document.DocumentType.SALES_CREDIT_NOTE
    list_display = ("id", "entity", "number", "date", "status", "debtor", "total")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(BaseDocumentAdmin):
    DOC_TYPE = Document.DocumentType.PURCHASE_ORDER


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(BaseDocumentAdmin):
    DOC_TYPE = Document.DocumentType.PURCHASE_INVOICE


@admin.register(PurchaseCreditNote)
class PurchaseCreditNoteAdmin(BaseDocumentAdmin):
    DOC_TYPE = Document.DocumentType.PURCHASE_CREDIT_NOTE





@admin.register(NumberSeries)
class NumberSeriesAdmin(ModelAdmin):
    list_display = ("entity", "code", "name", "purpose", "is_active", "next_number", "increment", "prefix", "suffix", "padding")
    list_filter = ("entity", "purpose", "is_active")
    search_fields = ("code", "name")
    ordering = ("entity", "purpose", "code")
    autocomplete_fields = ("entity",)




@admin.register(DebtorGroup)
class DebtorGroupAdmin(ModelAdmin):
    list_display = ("entity", "code", "name", "ar_account", "default_payment_terms", "number_series")
    list_filter = ("entity",)
    search_fields = ("code", "name", "ar_account__number", "ar_account__name")
    ordering = ("entity", "code")
    autocomplete_fields = ("entity", "ar_account", "default_payment_terms", "number_series")

    fieldsets = (
        (_("General"), {"fields": ("entity", "code", "name")}),
        (_("Accounting"), {"fields": ("ar_account",)}),
        (_("Defaults"), {"fields": ("default_payment_terms", "number_series")}),
    )

