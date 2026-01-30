from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from core.models import ExchangeRate

def get_rate(date, base, quote, *, entity=None):
    if base == quote:
        return Decimal("1")

    qs = ExchangeRate.objects.filter(
        date__lte=date,
        base=base,
        quote=quote,
    ).order_by("-date")

    if entity:
        qs = qs.filter(models.Q(entity=entity) | models.Q(entity__isnull=True))
    else:
        qs = qs.filter(entity__isnull=True)

    rate = qs.first()
    if not rate:
        raise ValidationError(
            f"No exchange rate for {base}->{quote} on {date}"
        )

    return rate.rate
