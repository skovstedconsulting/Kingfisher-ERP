from pyexpat.errors import messages
from django.contrib import admin, messages
from guardian.admin import GuardedModelAdmin

from core.admin_utils import EntityScopedAdminMixin
from ledger.models import Journal, JournalLine, OpenItem, Settlement
from ledger.services.settlement import sync_sales_doc_payment_state

from django.db import transaction
from django.db.models import Q


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0

@admin.register(Journal)
class JournalAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    inlines = [JournalLineInline]
    list_display = ("entity", "date", "number", "state", "reference")
    list_filter = ("entity", "state")
    search_fields = ("number", "reference")

    actions = ["post_journal"]

    @admin.action(description="Post journal")
    def post_journal(self, request, queryset):
        for journal in queryset:
            journal.post(by_user=request.user)
            journal.save()

@admin.register(JournalLine)
class JournalLineAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("id","account", "description", "debit_base", "credit_base", "currency")
    #list_filter = ("entity", "state")
    #search_fields = ("number", "reference")

@admin.register(OpenItem)
class OpenItemAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "kind", "debtor", "creditor", "remaining_base", "currency")
    list_filter = ("entity", "kind")
    search_fields = ("id",)


@admin.register(Settlement)
class SettlementAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "open_item", "payment_line", "amount_base", "amount_tx", "settled_at", "settled_by")
    list_filter = ("entity", "settled_at")
    actions = ["settle"]

    @admin.action(description="Settle")
    def settle(self, request, queryset):
        ok = 0
        skipped = 0
        failed = 0

        queryset = queryset.select_related(
            "open_item",
            "open_item__sales_document",
            "payment_line",
            "payment_line__journal",
        )

        for s in queryset:
            if s.settled_at:
                skipped += 1
                continue

            try:
                with transaction.atomic():
                    oi = s.settle(by_user=request.user)

                    # Sync sales doc payment FSM state (only if tied to a sales doc)
                    doc = getattr(oi, "sales_document", None)
                    if doc is not None:
                        sync_sales_doc_payment_state(doc, by_user=request.user)

                ok += 1

            except ValueError as e:
                skipped += 1
                self.message_user(request, f"Settlement #{s.pk} skipped: {e}", level=messages.WARNING)

            except Exception as e:
                failed += 1
                self.message_user(request, f"Settlement #{s.pk} failed: {e}", level=messages.ERROR)

        if ok:
            self.message_user(request, f"Settled {ok} settlement(s).", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"Skipped {skipped} settlement(s).", level=messages.WARNING)
        if failed:
            self.message_user(request, f"Failed {failed} settlement(s).", level=messages.ERROR)
