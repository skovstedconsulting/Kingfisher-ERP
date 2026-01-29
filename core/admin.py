from django.contrib import admin
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
    date_hierarchy = "date"
    inlines = [JournalLineInline]


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

