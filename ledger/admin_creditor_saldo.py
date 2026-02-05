from decimal import Decimal

from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce

from ledger.models import OpenItem


# ----------------------------
# Dummy unmanaged model
# ----------------------------
class CreditorSaldoRow(models.Model):
    entity = models.ForeignKey("core.Entity", on_delete=models.DO_NOTHING)
    creditor = models.ForeignKey("masterdata.Creditor", on_delete=models.DO_NOTHING)
    saldo_base = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    saldo_tx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    class Meta:
        managed = False
        verbose_name = "Creditor saldo"
        verbose_name_plural = "Creditor saldo"


# ----------------------------
# Custom ChangeList
# ----------------------------
class CreditorSaldoChangeList(ChangeList):
    """
    ChangeList that renders rows from an aggregated OpenItem query,
    but as instances of CreditorSaldoRow so admin can display them.
    """

    def get_queryset(self, request):
        # Admin expects *some* queryset; we won't use it for results.
        return CreditorSaldoRow.objects.none()

    def get_results(self, request):
        """
        Build the results list + counts in a way admin understands.
        """
        # Base aggregated query
        agg = (
            OpenItem.objects
            .select_related("entity", "creditor")
            .filter(kind=OpenItem.Kind.AP, creditor__isnull=False)
            .values("entity_id", "creditor_id", "entity__name", "creditor__name")
            .annotate(
                saldo_base=Coalesce(
                    Sum("remaining_base"),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                saldo_tx=Coalesce(
                    Sum("remaining_tx"),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
            )
        )

        # Apply admin list_filter for entity, if present in GET
        # Django's built-in filter parameter for FK is typically "entity__id__exact"
        entity_id = request.GET.get("entity__id__exact")
        if entity_id:
            agg = agg.filter(entity_id=entity_id)

        # Basic ordering (you can expand later)
        agg = agg.order_by("entity__name", "debtor__name")

        # Materialize rows into dummy model instances
        rows = []
        for r in agg:
            obj = CreditorSaldoRow(
                entity_id=r["entity_id"],
                creditor_id=r["creditor_id"],
                saldo_base=r["saldo_base"],
                saldo_tx=r["saldo_tx"],

            )
            # Stable fake PK (admin requires pk for each row)
            obj.pk = (r["entity_id"] * 10_000_000) + r[ "creditor_id"]
            rows.append(obj)

        # Pagination
        paginator = Paginator(rows, self.list_per_page)
        page_num = self.page_num + 1  # ChangeList.page_num is 0-based
        page = paginator.get_page(page_num)

        self.result_count = paginator.count
        self.full_result_count = paginator.count
        self.result_list = page.object_list
        self.can_show_all = False
        self.multi_page = paginator.num_pages > 1
        self.paginator = paginator
        self.show_all = False


# ----------------------------
# Admin
# ----------------------------
@admin.register(CreditorSaldoRow)
class CreditorSaldoAdmin(admin.ModelAdmin):
    list_display = ("entity", "creditor", "saldo_base", "saldo_tx")
    list_filter = ("entity","creditor",)
    search_fields = ("creditor__name", "creditor__no", "creditor")
    list_display_links = None
    
    list_per_page = 100

    # Read-only
    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_model_perms(self, request):
        # Ensures it appears under "Ledger" on the admin index
        return {"view": True}

    def get_changelist(self, request, **kwargs):
        return CreditorSaldoChangeList