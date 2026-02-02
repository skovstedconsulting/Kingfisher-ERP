from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class VatGroup(models.Model):
    """VAT group per entity (used to organize VAT codes)."""

    entity = models.ForeignKey(
        "core.Entity",
        on_delete=models.CASCADE,
        related_name="vat_groups",
    )

    code = models.CharField(
        max_length=50,
        help_text="Internal group code (derived or slugified)",
    )

    name = models.CharField(
        max_length=255,
        help_text="Momsgruppe (e.g. 'Salg', 'Køb fra EU-lande')",
    )

    class Meta:
        unique_together = ("entity", "code")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class VatCode(models.Model):
    """VAT code per entity.

    This intentionally keeps a *lot* of explicit fields so you can load Danish
    VAT master data without complex normalization.
    """

    class VatType(models.TextChoices):
        SALE = "SALE", "Salg"
        PURCHASE = "PURCHASE", "Køb"

    entity = models.ForeignKey(
        "core.Entity",
        on_delete=models.CASCADE,
        related_name="vat_codes",
    )

    output_vat_account = models.ForeignKey(
        "core.Account",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        help_text=_("Sales VAT (udgående moms) account"),
    )
    input_vat_account = models.ForeignKey(
        "core.Account",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        help_text=_("Purchase VAT (indgående moms) account"),
    )

    group = models.ForeignKey(
        VatGroup,
        on_delete=models.PROTECT,
        related_name="vat_codes",
        default=None,
    )

    # Core identifiers
    code = models.CharField(max_length=20)
    legacy_code = models.CharField(max_length=20, blank=True)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    vat_type = models.CharField(
        max_length=10,
        choices=VatType.choices,
        default=None,
    )

    # Rates
    rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="VAT rate (e.g. 0.2500 for 25%)",
    )

    deduction_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Deduction rate (1.0 = 100%, 0.6666 = 66.66%)",
    )

    deduction_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="Skøn, Pro rata, Arealfordeling, Sektor, etc.",
    )

    reporting_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Momsangivelse / reporting description",
    )

    # Applicability flags
    dk_only = models.BooleanField(default=False)
    dk_mixed = models.BooleanField(default=False)
    international = models.BooleanField(default=False)
    international_mixed = models.BooleanField(default=False)
    special_scheme = models.BooleanField(default=False)

    class Meta:
        unique_together = ("entity", "code")
        ordering = ["group__code", "code"]

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"

    def effective_rate(self) -> Decimal:
        """Return an effective VAT rate.

        If deduction_rate is set (<1), the effective rate is reduced.
        """

        rate = self.rate or Decimal("0")
        deduction = self.deduction_rate if self.deduction_rate is not None else Decimal("1")
        return (rate * deduction)
