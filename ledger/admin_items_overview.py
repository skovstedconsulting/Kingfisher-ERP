from decimal import Decimal

from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce

from inventory.models import InventoryLayer

#ledger.InventoryOverviewRow.item: (fields.E307) The field ledger.InventoryOverviewRow.item was declared with a lazy reference to 'inventory.item', but app 'inventory' doesn't provide model 'item'.

# ----------------------------
# Dummy unmanaged model
# ----------------------------
class InventoryOverviewRow(models.Model):
    entity = models.ForeignKey("core.Entity", on_delete=models.DO_NOTHING)
    item = models.ForeignKey("masterdata.Item", on_delete=models.DO_NOTHING)
    #quantity = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    qty_remaining = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    class Meta:
        managed = False
        verbose_name = "Inventory overview"
        verbose_name_plural = "Inventory overview"


# ----------------------------
# Custom ChangeList
# ----------------------------
class InventoryOverviewChangeList(ChangeList):
    """
    ChangeList that renders rows from an aggregated OpenItem query,
    but as instances of InventoryOverviewRow so admin can display them.
    """

    def get_queryset(self, request):
        # Admin expects *some* queryset; we won't use it for results.
        return InventoryOverviewRow.objects.none()

    def get_results(self, request):
        """
        Build the results list + counts in a way admin understands.
        """
        # Base aggregated query
        #agg = (
        #    InventoryLayer.objects
        #    .select_related("entity", "item")
        #    .filter(kind=InventoryLayer.Kind.AR, item__isnull=False)
        #    .values("entity_id", "item_id", "entity__name", "item__name")
        #    .annotate(
        #        saldo_base=Coalesce(
        #            Sum("remaining_base"),
        #            Value(Decimal("0.00")),
        #            output_field=DecimalField(max_digits=14, decimal_places=2),
        #        ),
        #        saldo_tx=Coalesce(
        #            Sum("remaining_tx"),
        #            Value(Decimal("0.00")),
        #            output_field=DecimalField(max_digits=14, decimal_places=2),
        #        ),
        #    )
        #)

        data = (
            InventoryLayer.objects
            .select_related("entity", "item")
            .values("entity_id", "item_id", "entity__name", "item__name")
            .annotate(
                qty_remaining=Coalesce(
                    Sum("qty_remaining"),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
            )
        )

        entity_id = request.GET.get("entity__id__exact")
        if entity_id:
            data = data.filter(entity_id=entity_id)

        data = data.order_by("entity__name", "item__name")

        rows = []
        for r in data:
            obj = InventoryOverviewRow(
                entity_id=r["entity_id"],
                item_id=r["item_id"],
                qty_remaining=r["qty_remaining"],
            )
            obj.pk = (r["entity_id"] * 10_000_000) + r["item_id"]
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
@admin.register(InventoryOverviewRow)
class InventoryOverviewAdmin(admin.ModelAdmin):
    list_display = ("entity", "item", "qty_remaining")
    list_filter = ("entity","item",)
    search_fields = ("item__name", "item__no", "item")
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
        return InventoryOverviewChangeList