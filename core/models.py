from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class IsoCountryCodes(models.Model):
    """
    Matches iso_countries.json structure:
    name, alpha-2, alpha-3, country-code, iso_3166-2, region, sub-region, intermediate-region, and code fields.
    """
    code = models.CharField(max_length=2, primary_key=True)  # alpha-2
    name = models.CharField(max_length=255)

    alpha_3 = models.CharField(max_length=3, blank=True, default="")
    numeric_code = models.CharField(max_length=3, blank=True, default="")  # "country-code" (string in file)
    iso_3166_2 = models.CharField(max_length=50, blank=True, default="")   # "iso_3166-2"

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

    def __str__(self):
        return f"{self.name} ({self.code})"


class IsoCurrencyCodes(models.Model):
    """
    Matches iso_currencies.json structure:
    name, demonym, major/minor names, ISO numeric, symbols, decimals, etc.
    """
    code = models.CharField(max_length=3, primary_key=True)  # ISO code like "DKK"
    name = models.CharField(max_length=255)

    demonym = models.CharField(max_length=100, blank=True, default="")
    iso_num = models.IntegerField(null=True, blank=True)     # "ISOnum" can be null
    iso_digits = models.IntegerField(null=True, blank=True)  # "ISOdigits"

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

    def __str__(self):
        return f"{self.code} – {self.name}"


class Entity(models.Model):
    """
    Legal or organizational entity (company).
    Uses ISO country/currency reference tables.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    registration_no = models.CharField(max_length=50, blank=True)

    country = models.ForeignKey(IsoCountryCodes, on_delete=models.PROTECT, related_name="entities")
    currency = models.ForeignKey(IsoCurrencyCodes, on_delete=models.PROTECT, related_name="entities")

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Entity")
        verbose_name_plural = _("Entities")

    def __str__(self):
        return self.name


class FiscalYear(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    year = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("entity", "year")
        ordering = ["-year"]

    def __str__(self):
        return f"{self.entity} {self.year}"


class Account(models.Model):
    class AccountType(models.TextChoices):
        ASSET = "ASSET", _("Asset")
        LIABILITY = "LIABILITY", _("Liability")
        EQUITY = "EQUITY", _("Equity")
        INCOME = "INCOME", _("Income")
        EXPENSE = "EXPENSE", _("Expense")

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=AccountType.choices)
    is_active = models.BooleanField(default=True)
    template_node = models.ForeignKey(
        "ChartOfAccountsNode",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="accounts",
        help_text=_("Origin in chart of accounts template"),
    )

    class Meta:
        unique_together = ("entity", "number")
        ordering = ["number"]

    def __str__(self):
        return f"{self.number} – {self.name}"


class Journal(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    date = models.DateField()
    reference = models.CharField(max_length=255, blank=True)
    posted = models.BooleanField(default=False)

    def __str__(self):
        return f"Journal {self.id} ({self.date})"


class JournalLine(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.account} D:{self.debit} C:{self.credit}"


class ChartOfAccountsTemplate(models.Model):
    """
    Metadata container for imported Standardkontoplan documents.
    Matches the top-level fields in the file (Document name, Valid from date, csv source file).
    """
    name = models.CharField(max_length=255)
    valid_from = models.DateField(null=True, blank=True)
    source_file = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = _("Chart of Accounts Template")
        verbose_name_plural = _("Chart of Accounts Templates")
        ordering = ["-valid_from", "name"]

    def __str__(self):
        return f"{self.name} ({self.valid_from or 'n/a'})"


class ChartOfAccountsNode(models.Model):
    """
    Tree structure for Standardkontoplan:
    hovedkonto (header), gruppekonto (group), konti (leaf accounts).
    """
    class NodeType(models.TextChoices):
        HEADER = "HEADER", _("Header")
        GROUP = "GROUP", _("Group")
        ACCOUNT = "ACCOUNT", _("Account")

    template = models.ForeignKey(ChartOfAccountsTemplate, on_delete=models.CASCADE, related_name="nodes")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")

    node_type = models.CharField(max_length=20, choices=NodeType.choices)
    number = models.IntegerField()
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ("template", "number")
        ordering = ["number"]

    def __str__(self):
        return f"{self.number} – {self.name}"
