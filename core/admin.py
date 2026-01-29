from django.contrib import admin, messages
from unfold.admin import ModelAdmin

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
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

)


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ("id","name", "country", "currency", "is_active")
    list_filter = ("country", "currency", "is_active")
    search_fields = ("name", "registration_no")


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

@admin.register(DebtorGroup)
class DebtorGroupAdmin(admin.ModelAdmin):
    list_display = ("entity", "code", "name", "ar_account", "default_payment_terms")
    list_filter = ("entity",)
    search_fields = ("code", "name", "ar_account__number", "ar_account__name")
    ordering = ("entity", "code")
    autocomplete_fields = ("entity", "ar_account", "default_payment_terms")


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
    )

    fieldsets = (
        (_("General"), {"fields": ("entity", "code", "name", "is_active")}),
        (_("Defaults: Accounts"), {"fields": ("default_sales_account", "default_cogs_account", "default_inventory_account")}),
        (_("Defaults: VAT"), {"fields": ("default_vat_code",)}),
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
