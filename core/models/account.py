from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

class Account(MPTTModel):
    """Chart of accounts node for a specific entity (tree via django-mptt)."""

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="accounts")

    number = models.CharField(max_length=50)
    name = models.CharField(max_length=255)

    parent = TreeForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    is_postable = models.BooleanField(default=True)

    class Meta:
        unique_together = ("entity", "number")
        ordering = ["number"]

    def __str__(self):
        return f"{self.number} – {self.name}"
