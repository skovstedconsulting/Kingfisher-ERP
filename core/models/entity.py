from django.db import models
from django.conf import settings

class Entity(models.Model):
    """Company/legal entity.

    Key principle:
    - Almost every business object belongs to an Entity (multi-tenant / multi-company).
    - Entity holds default configuration: base currency, number series, control accounts.
    """

    name = models.CharField(max_length=255)

    country = models.ForeignKey("core.IsoCountryCodes", on_delete=models.PROTECT)
    base_currency = models.ForeignKey("core.IsoCurrencyCodes", on_delete=models.PROTECT)

    # Number series used during transitions/posting
    default_series_journal = models.ForeignKey("core.NumberSeries", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    series_sales_offer = models.ForeignKey("core.NumberSeries", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    series_sales_order = models.ForeignKey("core.NumberSeries", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    series_sales_invoice = models.ForeignKey("core.NumberSeries", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    series_purchase_order = models.ForeignKey("core.NumberSeries", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    series_purchase_invoice = models.ForeignKey("core.NumberSeries", null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    # Control accounts (defaults)
    default_ap_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    # NOTE: AR is usually per debtor group (DebtorGroup.ar_account). However, we also provide an entity-level fallback.
    default_ar_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    fx_gain_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    fx_loss_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Connect a user to an Entity."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="users")
    
    image_url = models.URLField(max_length=512, blank=True)
    address = models.TextField(blank=True)

    is_entity_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} @ {self.entity}"
