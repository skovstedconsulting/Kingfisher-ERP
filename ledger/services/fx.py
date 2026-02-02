from decimal import Decimal
from core.models import ExchangeRate

def get_fx_rate(entity, date, base_code: str, quote_code: str) -> Decimal:
    """Fetch FX rate.

    Rule (simple):
    - Prefer entity-specific rate
    - Fallback to global (entity=NULL)
    - Exact date match required

    Advanced ideas are described in the docs/commentary in the chat response.
    """
    r = (ExchangeRate.objects
         .filter(entity__in=[entity, None], date=date, base=base_code, quote=quote_code)
         .order_by("-entity")
         .first())
    if not r:
        raise ValueError(f"Missing FX rate {base_code}->{quote_code} on {date}")
    return r.rate
