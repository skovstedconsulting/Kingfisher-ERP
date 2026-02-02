from django.db import models

class CreditorGroup(models.Model):
    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="creditor_groups")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ("entity", "code")
        ordering = ["code"]

class Creditor(models.Model):
    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="creditors")
    group = models.ForeignKey(CreditorGroup, on_delete=models.PROTECT, related_name="creditors")

    class VatArea(models.TextChoices):
        DK = "DK", "Denmark"
        EU_B2B = "EU_B2B", "EU B2B"
        EXPORT = "EXPORT", "Export / outside EU"
        DK_SPECIAL = "DK_SPECIAL", "DK special scheme"

    vat_area = models.CharField(max_length=20, choices=VatArea.choices, default=VatArea.DK)

    number = models.CharField(max_length=50)
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ("entity", "number")
        ordering = ["number"]
