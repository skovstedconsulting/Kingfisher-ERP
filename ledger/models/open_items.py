from django.conf import settings
from django.db import models
from decimal import Decimal

from ledger.models.journal_line import JournalLine

from django.db import models, transaction

from django.utils import timezone

class OpenItem(models.Model):
    """Represents an open AR/AP item created when an invoice is posted."""

    class Kind(models.TextChoices):
        AR = "AR", "Accounts receivable"
        AP = "AP", "Accounts payable"

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="open_items")
    kind = models.CharField(max_length=2, choices=Kind.choices)

    debtor = models.ForeignKey("masterdata.Debtor", null=True, blank=True, on_delete=models.PROTECT)
    creditor = models.ForeignKey("masterdata.Creditor", null=True, blank=True, on_delete=models.PROTECT)

    #sales_document = models.ForeignKey(SalesDocument, null=True, blank=True, on_delete=models.PROTECT)
    #purchase_document = models.ForeignKey(PurchaseDocument, null=True, blank=True, on_delete=models.PROTECT)


    sales_document = models.ForeignKey("documents.SalesDocument", null=True, blank=True, on_delete=models.PROTECT)
    purchase_document = models.ForeignKey("documents.PurchaseDocument", null=True, blank=True, on_delete=models.PROTECT)

    currency = models.ForeignKey("core.IsoCurrencyCodes", on_delete=models.PROTECT)
    original_tx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    original_base = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    remaining_tx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    remaining_base = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    due_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

class Settlement(models.Model):
    """Allocation between a payment journal line and an open item."""
    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="settlements")

    open_item = models.ForeignKey("ledger.OpenItem", on_delete=models.PROTECT, related_name="settlements")
    payment_line = models.ForeignKey("ledger.JournalLine", on_delete=models.PROTECT, related_name="settlements")

    amount_tx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    amount_base = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    settled_at = models.DateTimeField(null=True, blank=True)
    settled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    created_at = models.DateTimeField(auto_now_add=True)

    def _payment_effect_amounts(self, oi, pl):
        """
        Determine how much this payment line settles the open item.

        Baseline:
        - AR is settled by a CREDIT on the AR account line (credit reduces AR)
        - AP is settled by a DEBIT on the AP account line (debit reduces AP)
        """
        if oi.kind == oi.Kind.AR:
            tx = (pl.credit_tx or Decimal("0.00")) - (pl.debit_tx or Decimal("0.00"))
            base = (pl.credit_base or Decimal("0.00")) - (pl.debit_base or Decimal("0.00"))
        else:  # AP
            tx = (pl.debit_tx or Decimal("0.00")) - (pl.credit_tx or Decimal("0.00"))
            base = (pl.debit_base or Decimal("0.00")) - (pl.credit_base or Decimal("0.00"))

        # We expect a positive settlement effect (reducing remaining)
        return tx.quantize(Decimal("0.01")), base.quantize(Decimal("0.01"))

    @transaction.atomic
    def settle(self, *, by_user=None):
        """
        Apply this settlement: reduce open item remaining.

        Rules:
        - Cannot apply twice (settled_at is idempotency flag)
        - Entity must match OpenItem.entity and payment_line.journal.entity
        - Currency must match open item currency (strict baseline)
        - If amount_tx/base is 0, auto-derive from payment_line
        - Settlement amount must be > 0
        - Cannot settle more than remaining (strict)
        """
        if self.settled_at:
            raise ValueError("Settlement already applied.")

        # Lock OpenItem
        oi = (
            type(self.open_item).objects
            .select_for_update()
            .select_related("currency", "sales_document", "purchase_document")
            .get(pk=self.open_item_id)
        )

        # Load payment line (and journal entity)
        pl = (
            type(self.payment_line).objects
            .select_related("journal", "currency")
            .get(pk=self.payment_line_id)
        )

        # Validate entity consistency
        if oi.entity_id != self.entity_id:
            raise ValueError("Settlement.entity must match OpenItem.entity.")
        if pl.journal.entity_id != self.entity_id:
            raise ValueError("Settlement.entity must match payment_line.journal.entity.")

        # Currency check (strict baseline)
        # If payment line has null currency, treat it as entity base currency only if OpenItem is base currency.
        if pl.currency_id and oi.currency_id and pl.currency_id != oi.currency_id:
            raise ValueError("Currency mismatch: payment line currency must match open item currency.")

        # Determine amounts
        amt_tx = (self.amount_tx or Decimal("0.00")).quantize(Decimal("0.01"))
        amt_base = (self.amount_base or Decimal("0.00")).quantize(Decimal("0.01"))

        if amt_tx <= Decimal("0.00") and amt_base <= Decimal("0.00"):
            # Auto-derive from payment line
            derived_tx, derived_base = self._payment_effect_amounts(oi, pl)
            amt_tx, amt_base = derived_tx, derived_base

            # Persist derived amounts for audit clarity
            self.amount_tx = amt_tx
            self.amount_base = amt_base

        if amt_tx <= Decimal("0.00") and amt_base <= Decimal("0.00"):
            raise ValueError("Settlement amount must be > 0 (check payment line debit/credit).")

        # Current remaining
        rem_tx = (oi.remaining_tx or Decimal("0.00")).quantize(Decimal("0.01"))
        rem_base = (oi.remaining_base or Decimal("0.00")).quantize(Decimal("0.01"))

        # Strict: cannot exceed remaining (you can relax later for overpayments/credits)
        if amt_tx > Decimal("0.00") and rem_tx > Decimal("0.00") and amt_tx > rem_tx:
            raise ValueError(f"amount_tx {amt_tx} exceeds remaining_tx {rem_tx}")
        if amt_base > Decimal("0.00") and rem_base > Decimal("0.00") and amt_base > rem_base:
            raise ValueError(f"amount_base {amt_base} exceeds remaining_base {rem_base}")

        # Apply
        oi.remaining_tx = (rem_tx - amt_tx).quantize(Decimal("0.01"))
        oi.remaining_base = (rem_base - amt_base).quantize(Decimal("0.01"))

        # Normalize tiny rounding leftovers
        if Decimal("-0.01") < oi.remaining_tx < Decimal("0.01"):
            oi.remaining_tx = Decimal("0.00")
        if Decimal("-0.01") < oi.remaining_base < Decimal("0.01"):
            oi.remaining_base = Decimal("0.00")

        oi.save(update_fields=["remaining_tx", "remaining_base"])

        # Stamp settlement
        self.settled_at = timezone.now()
        self.settled_by = by_user
        self.save(update_fields=["amount_tx", "amount_base", "settled_at", "settled_by"])

        return oi
