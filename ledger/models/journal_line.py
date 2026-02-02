from django.db import models
from decimal import Decimal
from ledger.models.journal import Journal

class JournalLine(models.Model):
    """Journal line stores both transaction and base amounts.

    If the journal currency equals entity base currency, tx and base can be the same.
    For FX documents, base is used for balancing and reporting.
    """
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey("core.Account", on_delete=models.PROTECT)

    description = models.CharField(max_length=255, blank=True, default="")

    currency = models.ForeignKey("core.IsoCurrencyCodes", null=True, blank=True, on_delete=models.PROTECT)
    fx_rate = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)

    debit_tx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    credit_tx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    debit_base = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    credit_base = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["id"]
