from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class ExchangeRate(models.Model):
    """Exchange rate for a given date.

    Stored as: 1 BASE = rate * QUOTE

    Example:
        base=EUR, quote=DKK, rate=7.46038

    Scope:
        - entity = NULL: global rate
        - entity != NULL: entity-specific rate overrides global
    """

    SOURCE_ECB = "ECB"
    SOURCE_MANUAL = "MANUAL"
    SOURCE_CHOICES = (
        (SOURCE_ECB, "European Central Bank"),
        (SOURCE_MANUAL, "Manual"),
    )

    entity = models.ForeignKey(
        "core.Entity",
        on_delete=models.CASCADE,
        related_name="exchange_rates",
        null=True,
        blank=True,
        help_text="Optional. Null = global rate",
    )

    date = models.DateField(db_index=True)

    base = models.CharField(max_length=3, db_index=True, help_text="Base currency (e.g. EUR)")
    quote = models.CharField(max_length=3, db_index=True, help_text="Quote currency (e.g. DKK)")

    rate = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        validators=[MinValueValidator(Decimal("0.0000000001"))],
        help_text="1 base = rate * quote",
    )

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_ECB)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "entity",
            "date",
            "base",
            "quote",
            "source",
        )
        indexes = [
            models.Index(fields=["date", "base", "quote"]),
            models.Index(fields=["entity", "date"]),
        ]
        ordering = ["-date", "base", "quote"]

    def __str__(self) -> str:
        scope = self.entity_id or "GLOBAL"
        return f"{self.date} {scope}: 1 {self.base} = {self.rate} {self.quote}"
