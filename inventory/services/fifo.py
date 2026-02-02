from django.db import transaction
from decimal import Decimal
from inventory.models import InventoryLayer

@transaction.atomic
def consume_fifo(entity, item, qty_out: Decimal):
    """Consume FIFO layers for qty_out.

    Returns list of (qty_taken, unit_cost_base).

    We lock layers to avoid two postings consuming the same stock at the same time.
    """
    if qty_out <= 0:
        return []

    remaining = qty_out
    result = []

    layers = (InventoryLayer.objects
              .select_for_update()
              .filter(entity=entity, item=item, qty_remaining__gt=0)
              .order_by("created_at", "id"))

    for layer in layers:
        if remaining <= 0:
            break

        take = min(layer.qty_remaining, remaining)
        layer.qty_remaining = layer.qty_remaining - take
        layer.save(update_fields=["qty_remaining"])

        result.append((take, layer.unit_cost_base))
        remaining -= take

    if remaining > 0:
        raise ValueError(f"Not enough stock for item {item}. Missing qty={remaining}")

    return result
