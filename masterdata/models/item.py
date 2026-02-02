from django.db import models
from decimal import Decimal

class ItemGroup(models.Model):
    """Holds default VAT and accounting settings per group."""
    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="item_groups")

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)

    # VAT defaults
    default_sales_vat_code = models.ForeignKey("core.VatCode", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    default_purchase_vat_code = models.ForeignKey("core.VatCode", null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    # Accounting defaults
    sales_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    expense_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    inventory_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    cogs_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    class Meta:
        unique_together = ("entity", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class Item(models.Model):
    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="items")
    group = models.ForeignKey(ItemGroup, on_delete=models.PROTECT, related_name="items")

    number = models.CharField(max_length=50)
    name = models.CharField(max_length=255)

    is_stock_item = models.BooleanField(default=True)

    sales_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    purchase_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("entity", "number")
        ordering = ["number"]

    def __str__(self):
        return f"{self.number} {self.name}"
