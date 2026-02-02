from sre_parse import State
from django.db import models
from django.conf import settings
from django.utils import timezone
from django_fsm import FSMField, transition
from simple_history.models import HistoricalRecords
from django_fsm_log.decorators import fsm_log_by
from decimal import Decimal

class SalesDocument(models.Model):
    """Sales document with state machine.

    We store *separate numbers* for offer/order/invoice.
    Reason: you asked that the document must be aware of all numbers across lifecycle.
    We allocate numbers when transitioning (to avoid gaps).
    """

    class State(models.TextChoices):
        OFFER = "offer", "Offer"
        ORDER = "order", "Order"
        INVOICE = "invoice", "Invoice"
        POSTED = "posted", "Posted"
        PARTLY_PAID = "partly_paid", "Partly paid"
        PAID = "paid", "Paid"
        CREDITED = "credited", "Credited"

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="sales_documents")
    state = FSMField(default=State.OFFER, choices=State.choices, protected=True)

    date = models.DateField()
    debtor = models.ForeignKey("masterdata.Debtor", on_delete=models.PROTECT, related_name="sales_documents")

    currency = models.ForeignKey("core.IsoCurrencyCodes", on_delete=models.PROTECT)
    reference = models.CharField(max_length=255, blank=True, default="")

    # lifecycle numbers
    offer_no = models.CharField(max_length=40, blank=True, default="")
    order_no = models.CharField(max_length=40, blank=True, default="")
    invoice_no = models.CharField(max_length=40, blank=True, default="")

    total_tx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_base = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    posted_journal = models.OneToOneField("ledger.Journal", null=True, blank=True, on_delete=models.PROTECT, related_name="sales_source")
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    # optional (nice for reporting; not required if you can derive from OpenItem)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="+"
    )
    
    credited_at = models.DateTimeField(null=True, blank=True)
    credited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.PROTECT, related_name="+"
    )
    
    history = HistoricalRecords()

    class Meta:
        ordering = ("-date", "-id")
        indexes = [
            models.Index(fields=["entity", "state", "date"]),
            models.Index(fields=["entity", "offer_no"]),
            models.Index(fields=["entity", "order_no"]),
            models.Index(fields=["entity", "invoice_no"]),
        ]

    def __str__(self):
        return f"{self.get_state_display()} {self.invoice_no or self.order_no or self.offer_no or self.pk}"

    @property
    def display_no(self) -> str:
        """Convenient derived number for UI/printing.

        This is a computed value (not stored).
        The @property decorator lets you access it like a field:
            doc.display_no
        instead of:
            doc.display_no()
        """
        return self.invoice_no or self.order_no or self.offer_no or str(self.pk)

    def _ensure_lines(self):
        """Posting/transition precondition: document must have at least one line."""
        if not self.lines.exists():
            raise ValueError("Document has no lines.")

    def _allocate_offer_no_if_missing(self):
        """Allocate offer number if missing."""
        if self.offer_no:
            return
        series = self.entity.series_sales_offer
        if not series:
            raise ValueError("Entity missing series_sales_offer")
        self.offer_no = series.allocate()
        self.save(update_fields=["offer_no"])

    def _allocate_order_no_if_missing(self):
        """Allocate order number if missing."""
        if self.order_no:
            return
        series = self.entity.series_sales_order
        if not series:
            raise ValueError("Entity missing series_sales_order")
        self.order_no = series.allocate()
        self.save(update_fields=["order_no"])

    def _allocate_invoice_no_if_missing(self):
        """Allocate invoice number if missing."""
        if self.invoice_no:
            return
        series = self.entity.series_sales_invoice
        if not series:
            raise ValueError("Entity missing series_sales_invoice")
        self.invoice_no = series.allocate()
        self.save(update_fields=["invoice_no"])

    @fsm_log_by
    @transition(field=state, source=State.OFFER, target=State.ORDER)
    def convert_to_order(self, by_user=None):
        """Convert offer to order.

        - Ensures lines exist
        - Ensures an order number is allocated
        - Keeps the offer number (if you allocated it earlier)
        """
        self._ensure_lines()
        # If you want offers to always have an offer number, allocate it in create or here:
        self._allocate_offer_no_if_missing()
        self._allocate_order_no_if_missing()

    @fsm_log_by
    @transition(field=state, source=State.ORDER, target=State.INVOICE)
    def convert_to_invoice(self, by_user=None):
        """Convert order to invoice."""
        self._ensure_lines()
        self._allocate_invoice_no_if_missing()

    @fsm_log_by
    @transition(field=state, source=State.INVOICE, target=State.POSTED)
    def post(self, by_user=None):
        """Post sales invoice.

        The actual accounting work is delegated to a service function.
        If the service raises an error, the transaction is rolled back and state stays INVOICE.
        """
        from ledger.services.sales_posting import post_sales_invoice
        post_sales_invoice(self, by_user=by_user)

    @fsm_log_by
    @transition(field=state, source=State.POSTED, target=State.PARTLY_PAID)
    def mark_partly_paid(self, by_user=None):
        # don't stamp paid_at for partials (optional)
        pass

    @fsm_log_by
    @transition(field=state, source=[State.POSTED, State.PARTLY_PAID], target=State.PAID)
    def mark_paid(self, by_user=None):
        self.paid_at = timezone.now()
        self.paid_by = by_user

    @fsm_log_by
    @transition(field=state, source=[State.POSTED], target=State.CREDITED)
    def mark_credited(self, by_user=None):
        self.credited_at = timezone.now()
        self.credited_by = by_user


class SalesLine(models.Model):
    """Sales line.

    Defaulting description from item is done in save() in a simple, explicit way.
    """
    document = models.ForeignKey(SalesDocument, on_delete=models.CASCADE, related_name="lines")

    line_no = models.IntegerField()

    item = models.ForeignKey("masterdata.Item", null=True, blank=True, on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True, default="")

    qty = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0.000"))
    unit_price_tx = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    vat_code = models.ForeignKey("core.VatCode", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("document", "line_no")
        ordering = ["line_no"]

    def save(self, *args, **kwargs):
        """Default description from item if empty."""

        last = (
            SalesLine.objects
            .filter(document_id=self.document_id)
            .order_by("-line_no")
            .values_list("line_no", flat=True)
            .first()
        )
        
        self.line_no = (last or 0) + 10  # ERP-style spacing

        if not self.description and self.item_id:
            # Keep it readable: if user hasn't typed anything, copy the item name.
            self.description = self.item.name

        if (self.unit_price_tx is None or self.unit_price_tx == 0) and hasattr(self.item, "sales_price"):
            self.unit_price_tx = self.item.sales_price


        super().save(*args, **kwargs)

    @property
    def net_tx(self) -> Decimal:
        """Net amount in transaction currency."""
        return (self.qty * self.unit_price_tx).quantize(Decimal("0.01"))
