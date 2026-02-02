from django.db import models
from django.utils.translation import gettext_lazy as _

class DebtorGroup(models.Model):
    """Holds accounting + payment settings for AR."""
    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="debtor_groups")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)

    ar_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    payment_terms_days = models.IntegerField(default=14)

    class Meta:
        unique_together = ("entity", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class Debtor(models.Model):
    """Customer model with VAT area."""

    class VatArea(models.TextChoices):
        DK = "DK", _("Denmark")
        EU_B2B = "EU_B2B", _("EU B2B")
        EXPORT = "EXPORT", _("Export / outside EU")
        DK_SPECIAL = "DK_SPECIAL", _("DK special scheme")

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="debtors")
    group = models.ForeignKey(DebtorGroup, on_delete=models.PROTECT, related_name="debtors")

    number = models.CharField(max_length=50)
    name = models.CharField(max_length=255)

    vat_area = models.CharField(max_length=20, choices=VatArea.choices, default=VatArea.DK)

    class Meta:
        unique_together = ("entity", "number")
        ordering = ["number"]

    def __str__(self):
        return f"{self.number} {self.name}"
