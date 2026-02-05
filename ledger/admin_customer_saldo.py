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
class CustomerSaldoRow(models.Model):
    entity = models.ForeignKey("core.Entity", on_delete=models.DO_NOTHING)
    debtor = models.ForeignKey("masterdata.Debtor", on_delete=models.DO_NOTHING)
    saldo_base = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    saldo_fx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        managed = False
        verbose_name = "Customer saldo"
        verbose_name_plural = "Customer saldo"


# ----------------------------
# Custom ChangeList
# ----------------------------
class CustomerSaldoChangeList(ChangeList):
    """
    ChangeList that renders rows from an aggregated OpenItem query,
    but as instances of CustomerSaldoRow so admin can display them.
    """

    def get_queryset(self, request):
        # Admin expects *some* queryset; we won't use it for results.
        return CustomerSaldoRow.objects.none()

    def get_results(self, request):
        """
        Build the results list + counts in a way admin understands.
        """
        # Base aggregated query
        agg = (
            OpenItem.objects
            .select_related("entity", "debtor")
            .filter(kind=OpenItem.Kind.AR, debtor__isnull=False)
            .values("entity_id", "debtor_id", "entity__name", "debtor__name")
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
            obj = CustomerSaldoRow(
                entity_id=r["entity_id"],
                debtor_id=r["debtor_id"],
                saldo_base=r["saldo_base"],
                saldo_fx=r["saldo_tx"],

            )
            # Stable fake PK (admin requires pk for each row)
            obj.pk = (r["entity_id"] * 10_000_000) + r["debtor_id"]
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
@admin.register(CustomerSaldoRow)
class CustomerSaldoAdmin(admin.ModelAdmin):
    list_display = ("entity", "debtor", "saldo_base", "saldo_fx")
    list_filter = ("entity","debtor",)
    search_fields = ("debtor__name", "debtor__no", "debtor")
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
        return CustomerSaldoChangeList
