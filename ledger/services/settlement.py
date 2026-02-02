from decimal import Decimal
from django.db import transaction
from ledger.models import OpenItem

@transaction.atomic
def sync_sales_doc_payment_state(doc, *, by_user=None):
    """
    Sets doc.state based on the AR OpenItem remaining balance.
    Should be called after any settlement that changes remaining_*.
    """
    oi = (
        OpenItem.objects
        .select_for_update()
        .filter(sales_document=doc, kind=OpenItem.Kind.AR)
        .order_by("-id")
        .first()
    )
    if not oi:
        return  # not posted or no AR item

    # Normalize tiny rounding leftovers
    remaining = (oi.remaining_tx or Decimal("0.00")).quantize(Decimal("0.01"))
    original = (oi.original_tx or Decimal("0.00")).quantize(Decimal("0.01"))

    if remaining <= Decimal("0.00"):
        if doc.state != doc.State.PAID:
            doc.mark_paid(by_user=by_user)
            doc.save(update_fields=["state", "paid_at", "paid_by"])
        return

    # remaining > 0
    if remaining < original:
        if doc.state == doc.State.POSTED:
            doc.mark_partly_paid(by_user=by_user)
            doc.save(update_fields=["state"])
    else:
        # fully unpaid: optionally revert PARTLY_PAID back to POSTED if you support undo
        if doc.state == doc.State.PARTLY_PAID:
            doc.mark_unpaid(by_user=by_user)
            doc.save(update_fields=["state"])
