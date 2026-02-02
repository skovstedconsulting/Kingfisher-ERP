from django.db import models
from django.utils.translation import gettext_lazy as _


class IsoCountryCodes(models.Model):
    """ISO 3166 country codes.

    This matches the structure you import from ``iso_countries.json``.
    We keep the fields flat and explicit for readability.
    """

    code = models.CharField(max_length=2, primary_key=True)  # alpha-2
    name = models.CharField(max_length=255)

    alpha_3 = models.CharField(max_length=3, blank=True, default="")
    numeric_code = models.CharField(max_length=3, blank=True, default="")
    iso_3166_2 = models.CharField(max_length=50, blank=True, default="")

    region = models.CharField(max_length=100, blank=True, default="")
    sub_region = models.CharField(max_length=100, blank=True, default="")
    intermediate_region = models.CharField(max_length=100, blank=True, default="")

    region_code = models.CharField(max_length=10, blank=True, default="")
    sub_region_code = models.CharField(max_length=10, blank=True, default="")
    intermediate_region_code = models.CharField(max_length=10, blank=True, default="")

    class Meta:
        verbose_name = _("ISO Country Code")
        verbose_name_plural = _("ISO Country Codes")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class IsoCurrencyCodes(models.Model):
    """ISO 4217 currency codes.

    This matches the structure you import from ``iso_currencies.json``.
    """

    code = models.CharField(max_length=3, primary_key=True)  # ISO code like "DKK"
    name = models.CharField(max_length=255)

    demonym = models.CharField(max_length=100, blank=True, default="")
    iso_num = models.IntegerField(null=True, blank=True)
    iso_digits = models.IntegerField(null=True, blank=True)

    symbol = models.CharField(max_length=32, blank=True, default="")
    symbol_native = models.CharField(max_length=32, blank=True, default="")

    major_single = models.CharField(max_length=100, blank=True, default="")
    major_plural = models.CharField(max_length=100, blank=True, default="")
    minor_single = models.CharField(max_length=100, blank=True, default="")
    minor_plural = models.CharField(max_length=100, blank=True, default="")

    decimals = models.IntegerField(null=True, blank=True)
    num_to_basic = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = _("ISO Currency Code")
        verbose_name_plural = _("ISO Currency Codes")
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"
