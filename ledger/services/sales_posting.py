from django.db import transaction
from decimal import Decimal
from django.utils import timezone

from core.services.vat import vat_code_allowed_for_debtor_area
from ledger.models import Journal, JournalLine, OpenItem
from ledger.services.fx import get_fx_rate
from inventory.services.fifo import consume_fifo
from inventory.models import StockMove
from core.models import Entity

@transaction.atomic
def post_sales_invoice(doc, by_user=None):
    """Post a sales invoice.

    What it does (high level):
    1) Lock the document row to prevent double posting
    2) Create a draft Journal
    3) For each sales line:
       - Resolve VAT code (line or item group default)
       - Validate VAT allowed for debtor VAT area
       - Credit revenue
       - Credit output VAT
       - If stock item: post COGS + reduce inventory using FIFO
    4) Add AR control line (debit)
    5) Post the journal (FSM transition draft->posted)
    6) Create an OpenItem (AR)
    7) Stamp document posted fields + totals

    Notes:
    - This is a readable baseline. Later you can add:
      * credit notes
      * discounts
      * rounding lines
      * partial deliveries/invoicing
      * FX revaluation of open items
    """

    # Re-load and lock the document row
    doc = type(doc).objects.select_for_update().select_related("entity", "currency", "debtor", "debtor__group").get(pk=doc.pk)

    if doc.posted_journal_id:
        raise ValueError("Document is already posted.")
    if not doc.lines.exists():
        raise ValueError("Document has no lines.")

    entity = doc.entity
    base_ccy = entity.base_currency

    # FX logic (simple baseline)
    fx_rate = Decimal("1.0")
    if doc.currency_id != base_ccy.pk:
        fx_rate = get_fx_rate(entity, doc.date, base_ccy.code, doc.currency.code)

    # Create draft journal
    j = Journal.objects.create(
        entity=entity,
        date=doc.date,
        reference=f"Sales invoice {doc.invoice_no or doc.pk}",
    )

    def add_line(account, *, debit_base=Decimal("0.00"), credit_base=Decimal("0.00"),
                 debit_tx=Decimal("0.00"), credit_tx=Decimal("0.00"),
                 currency=None, fx_rate=None, description=""):
        """Create a JournalLine (helper for readability)."""
        JournalLine.objects.create(
            journal=j,
            account=account,
            description=description[:255],
            currency=currency,
            fx_rate=fx_rate,
            debit_base=debit_base,
            credit_base=credit_base,
            debit_tx=debit_tx,
            credit_tx=credit_tx,
        )

    total_net_tx = Decimal("0.00")
    total_net_base = Decimal("0.00")
    total_vat_tx = Decimal("0.00")
    total_vat_base = Decimal("0.00")
    total_cogs_base = Decimal("0.00")

    for line in doc.lines.select_related("item", "vat_code", "item__group").all():
        # Net amounts
        net_tx = line.net_tx
        net_base = (net_tx / fx_rate).quantize(Decimal("0.01")) if fx_rate != 0 else Decimal("0.00")

        # VAT code: line overrides, else from item group
        vat_code = line.vat_code
        if not vat_code and line.item_id and line.item.group_id:
            vat_code = line.item.group.default_sales_vat_code

        if vat_code:
            # Ensure VAT code matches debtor VAT area (DK/EU/export etc.)
            if not vat_code_allowed_for_debtor_area(vat_code, doc.debtor.vat_area):
                raise ValueError(
                    f"VAT code {vat_code.code} not allowed for debtor VAT area {doc.debtor.vat_area}"
                )

        vat_tx = Decimal("0.00")
        vat_base = Decimal("0.00")
        if vat_code and vat_code.rate:
            vat_tx = (net_tx * vat_code.rate).quantize(Decimal("0.01"))
            vat_base = (vat_tx / fx_rate).quantize(Decimal("0.01")) if fx_rate != 0 else Decimal("0.00")

        total_net_tx += net_tx
        total_net_base += net_base
        total_vat_tx += vat_tx
        total_vat_base += vat_base

        # Revenue posting (credit)
        if not line.item_id or not line.item.group_id:
            raise ValueError("Sales line must have an item with a group for posting.")

        group = line.item.group
        if not group.sales_account_id:
            raise ValueError(f"ItemGroup {group} missing sales_account.")

        add_line(
            account=group.sales_account,
            credit_base=net_base,
            credit_tx=net_tx,
            currency=doc.currency,
            fx_rate=fx_rate,
            description=line.description or "Revenue",
        )

        # Output VAT posting (credit)
        if vat_tx != 0:
            if not vat_code.output_vat_account_id:
                raise ValueError(f"VAT code {vat_code.code} missing output_vat_account.")
            add_line(
                account=vat_code.output_vat_account,
                credit_base=vat_base,
                credit_tx=vat_tx,
                currency=doc.currency,
                fx_rate=fx_rate,
                description=f"Output VAT {vat_code.code}",
            )

        # Inventory/COGS posting for stock items (FIFO)
        if line.item.is_stock_item:
            if not group.inventory_account_id:
                raise ValueError(f"ItemGroup {group} missing inventory_account.")
            if not group.cogs_account_id:
                raise ValueError(f"ItemGroup {group} missing cogs_account.")

            # Consume FIFO layers and compute COGS in base currency
            fifo = consume_fifo(entity, line.item, qty_out=line.qty)
            cogs_line_base = sum((qty * unit_cost) for qty, unit_cost in fifo).quantize(Decimal("0.01"))
            total_cogs_base += cogs_line_base

            # Debit COGS, credit inventory
            add_line(
                account=group.cogs_account,
                debit_base=cogs_line_base,
                description="COGS",
            )
            add_line(
                account=group.inventory_account,
                credit_base=cogs_line_base,
                description="Inventory",
            )

            # Stock movement audit
            StockMove.objects.create(
                entity=entity,
                item=line.item,
                date=doc.date,
                qty=-line.qty,
                unit_cost_base=(cogs_line_base / line.qty).quantize(Decimal("0.0001")) if line.qty else Decimal("0.0000"),
                sales_line=line,
            )

    gross_tx = (total_net_tx + total_vat_tx).quantize(Decimal("0.01"))
    gross_base = (total_net_base + total_vat_base).quantize(Decimal("0.01"))

    # AR control line (debit)
    ar = None
    if doc.debtor.group_id and doc.debtor.group.ar_account_id:
        ar = doc.debtor.group.ar_account
    elif entity.default_ar_account_id:
        ar = entity.default_ar_account

    if not ar:
        raise ValueError("Missing AR account. Set DebtorGroup.ar_account or Entity.default_ar_account.")

    add_line(
        account=ar,
        debit_base=gross_base,
        debit_tx=gross_tx,
        currency=doc.currency,
        fx_rate=fx_rate,
        description="Accounts receivable",
    )

    # Post the journal (FSM transition)
    j.post(by_user=by_user)

    # Create AR open item for settlement
    OpenItem.objects.create(
        entity=entity,
        kind=OpenItem.Kind.AR,
        debtor=doc.debtor,
        sales_document=doc,
        currency=doc.currency,
        original_tx=gross_tx,
        original_base=gross_base,
        remaining_tx=gross_tx,
        remaining_base=gross_base,
        due_date=doc.date,  # later: debtor group payment terms
    )

    # Stamp document
    doc.posted_journal = j
    doc.posted_at = timezone.now()
    doc.posted_by = by_user
    doc.total_tx = gross_tx
    doc.total_base = gross_base
    doc.save(update_fields=["posted_journal", "posted_at", "posted_by", "total_tx", "total_base"])
