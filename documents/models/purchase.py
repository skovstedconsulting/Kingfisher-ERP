from django.db import models
from django.conf import settings
from django_fsm import FSMField, transition
from simple_history.models import HistoricalRecords
from django_fsm_log.decorators import fsm_log_by
from decimal import Decimal

class PurchaseDocument(models.Model):
    """Purchase document with ORDER -> INVOICE -> POSTED.

    Stores separate order and invoice numbers.
    """
    class State(models.TextChoices):
        ORDER = "order", "Order"
        INVOICE = "invoice", "Invoice"
        POSTED = "posted", "Posted"

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="purchase_documents")
    state = FSMField(default=State.ORDER, choices=State.choices, protected=True)

    date = models.DateField()
    creditor = models.ForeignKey("masterdata.Creditor", on_delete=models.PROTECT, related_name="purchase_documents")
    currency = models.ForeignKey("core.IsoCurrencyCodes", on_delete=models.PROTECT)

    order_no = models.CharField(max_length=40, blank=True, default="")
    invoice_no = models.CharField(max_length=40, blank=True, default="")

    total_tx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_base = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    posted_journal = models.OneToOneField("ledger.Journal", null=True, blank=True, on_delete=models.PROTECT, related_name="purchase_source")
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    history = HistoricalRecords()

    class Meta:
        ordering = ("-date", "-id")
        indexes = [
            models.Index(fields=["entity", "state", "date"]),
            models.Index(fields=["entity", "order_no"]),
            models.Index(fields=["entity", "invoice_no"]),
        ]

    def __str__(self):
        return f"{self.get_state_display()} {self.invoice_no or self.order_no or self.pk}"

    def _ensure_lines(self):
        """Transition precondition: must have lines."""
        if not self.lines.exists():
            raise ValueError("Document has no lines.")

    def _allocate_order_no_if_missing(self):
        """Allocate purchase order number if missing."""
        if self.order_no:
            return
        series = self.entity.series_purchase_order
        if not series:
            raise ValueError("Entity missing series_purchase_order")
        self.order_no = series.allocate()
        self.save(update_fields=["order_no"])

    def _allocate_invoice_no_if_missing(self):
        """Allocate purchase invoice number if missing."""
        if self.invoice_no:
            return
        series = self.entity.series_purchase_invoice
        if not series:
            raise ValueError("Entity missing series_purchase_invoice")
        self.invoice_no = series.allocate()
        self.save(update_fields=["invoice_no"])

    @fsm_log_by
    @transition(field=state, source=State.ORDER, target=State.INVOICE)
    def convert_to_invoice(self, by_user=None):
        """Convert purchase order to invoice."""
        self._ensure_lines()
        self._allocate_order_no_if_missing()
        self._allocate_invoice_no_if_missing()

    @fsm_log_by
    @transition(field=state, source=State.INVOICE, target=State.POSTED)
    def post(self, by_user=None):
        """Post purchase invoice."""
        from ledger.services.purchase_posting import post_purchase_invoice
        post_purchase_invoice(self, by_user=by_user)


class PurchaseLine(models.Model):
    document = models.ForeignKey(PurchaseDocument, on_delete=models.CASCADE, related_name="lines")
    line_no = models.IntegerField()

    item = models.ForeignKey("masterdata.Item", null=True, blank=True, on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True, default="")

    qty = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0.000"))
    unit_cost_tx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    vat_code = models.ForeignKey("core.VatCode", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("document", "line_no")
        ordering = ["line_no"]

    def save(self, *args, **kwargs):
        """Default description from item if empty."""
        if not self.description and self.item_id:
            self.description = self.item.name
        super().save(*args, **kwargs)

    @property
    def net_tx(self) -> Decimal:
        return (self.qty * self.unit_cost_tx).quantize(Decimal("0.01"))
