from django.db import models
from decimal import Decimal
from documents.models.purchase import PurchaseLine
from documents.models.sales import SalesLine

class InventoryLayer(models.Model):
    """FIFO layer created from purchase postings."""
    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="inventory_layers")
    item = models.ForeignKey("masterdata.Item", on_delete=models.PROTECT, related_name="layers")

    qty_remaining = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0.000"))
    unit_cost_base = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0.0000"))

    created_at = models.DateTimeField(auto_now_add=True)

class StockMove(models.Model):
    """Audit trail for stock movements."""
    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="stock_moves")
    item = models.ForeignKey("masterdata.Item", on_delete=models.PROTECT)

    date = models.DateField()
    qty = models.DecimalField(max_digits=14, decimal_places=3)

    unit_cost_base = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0.0000"))

    sales_line = models.ForeignKey(SalesLine, null=True, blank=True, on_delete=models.PROTECT)
    purchase_line = models.ForeignKey(PurchaseLine, null=True, blank=True, on_delete=models.PROTECT)
