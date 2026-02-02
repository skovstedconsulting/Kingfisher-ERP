from core.models import VatCode

def vat_code_allowed_for_debtor_area(vat_code: VatCode, vat_area: str) -> bool:
    """Return True if the vat_code is allowed for the debtor's VAT area.

    This is intentionally explicit and readable.
    You can evolve it later (e.g. add country-based rules, reverse charge, etc.).
    """
    if vat_area == "DK":
        return vat_code.dk_only or vat_code.dk_mixed
    if vat_area in {"EU_B2B", "EXPORT"}:
        return vat_code.international or vat_code.international_mixed
    if vat_area == "DK_SPECIAL":
        return vat_code.special_scheme
    return False
