from django.contrib import admin
from .models import (
    BankReconciliationSetup,
    BankStatementStaging,
    BankStatementStagingLine,
    BankReconciliationSession,
    BankMatch,
    BankMatchBankLine,
    BankMatchJournalLine,  # <-- NY
)


class BankStatementStagingLineInline(admin.TabularInline):
    model = BankStatementStagingLine
    extra = 0
    fields = ("bank_tx_id", "booking_date", "value_date", "amount", "reference", "text")
    #readonly_fields = fields


@admin.register(BankReconciliationSetup)
class BankReconciliationSetupAdmin(admin.ModelAdmin):
    list_display = (
        "entity",
        "name",
        "bank_account_no",
        "gl_bank_account",
        "amount_tolerance",
        "date_window_days",
        "is_active",
    )
    list_filter = ("entity", "is_active")
    search_fields = ("name", "bank_account_no")


@admin.register(BankStatementStaging)
class BankStatementStagingAdmin(admin.ModelAdmin):
    list_display = (
        "entity",
        "statement_id",
        "currency",
        "status",
        "statement_date_from",
        "statement_date_to",
        "created_at",
    )
    list_filter = ("entity", "status", "currency")
    search_fields = ("statement_id",)
    inlines = [BankStatementStagingLineInline]


@admin.register(BankReconciliationSession)
class BankReconciliationSessionAdmin(admin.ModelAdmin):
    list_display = ("entity", "id", "setup", "staging", "status", "created_at")
    list_filter = ("entity", "status")
    search_fields = ("staging__statement_id", "setup__name")


class BankMatchBankLineInline(admin.TabularInline):
    model = BankMatchBankLine
    extra = 0
    #autocomplete_fields = ("bank_line",)


class BankMatchJournalLineInline(admin.TabularInline):
    model = BankMatchJournalLine  # <-- NY
    extra = 0
    #autocomplete_fields = ("journal_line",)


@admin.register(BankMatch)
class BankMatchAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "created_at", "created_by", "note")
    list_filter = ("session__entity",)
    search_fields = ("note", "session__staging__statement_id")
    inlines = [BankMatchBankLineInline, BankMatchJournalLineInline]
