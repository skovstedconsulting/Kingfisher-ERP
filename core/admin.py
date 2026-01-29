from django.contrib import admin, messages
from django.core.exceptions import ValidationError
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

