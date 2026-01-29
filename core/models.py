from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from django.db.models import Q, F
from django.db.models.constraints import CheckConstraint

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

    CENT = Decimal("0.01")

    def validate_for_posting(self):
        """
        Hard validation: must pass before posted=True can be set.
        Raises ValidationError.
        """
        errors = {}

        # 1) Fiscal period / year open
        fy = (
            FiscalYear.objects
            .filter(entity=self.entity, start_date__lte=self.date, end_date__gte=self.date)
            .order_by("-year")
            .first()
        )
        if not fy:
            errors["date"] = _("Journal date is not covered by any fiscal year.")
        elif fy.is_closed:
            errors["date"] = _("Fiscal year is closed for this journal date.")

        # 2) Lines existence
        lines_qs = self.lines.select_related("account")
        if not lines_qs.exists():
            errors["lines"] = _("Journal must have at least one line.")
        else:
            # 3) Line-level checks
            line_errors = []
            for idx, ln in enumerate(lines_qs.order_by("id"), start=1):
                le = []

                if ln.account.entity_id != self.entity_id:
                    le.append(_("Line account entity does not match journal entity."))

                if not ln.account.is_active:
                    le.append(_("Account is inactive."))

                if ln.debit < 0 or ln.credit < 0:
                    le.append(_("Debit/Credit cannot be negative."))

                if ln.debit > 0 and ln.credit > 0:
                    le.append(_("A line cannot have both debit and credit."))

                if ln.debit == 0 and ln.credit == 0:
                    le.append(_("A line cannot be all zero."))

                if le:
                    line_errors.append({f"line_{idx}": le})

            if line_errors:
                # attach under "lines" so it shows as a group
                errors["lines"] = line_errors

            # 4) Double-entry balance
            totals = lines_qs.aggregate(
                debit_sum=Sum("debit"),
                credit_sum=Sum("credit"),
            )
            debit_sum = (totals["debit_sum"] or Decimal("0")).quantize(self.CENT)
            credit_sum = (totals["credit_sum"] or Decimal("0")).quantize(self.CENT)

            if debit_sum != credit_sum:
                errors["__all__"] = _(
                    f"Journal is not balanced: debit {debit_sum} != credit {credit_sum}."
                )

        if errors:
            raise ValidationError(errors)

    @transaction.atomic
    def post(self, *, by_user=None):
        j = Journal.objects.select_for_update().get(pk=self.pk)
        if j.posted:
            return

        list(j.lines.select_for_update().all())
        j.validate_for_posting()

        Journal.objects.filter(pk=j.pk, posted=False).update(posted=True)


    def save(self, *args, **kwargs):
        if self.pk:
            old = Journal.objects.only("posted").get(pk=self.pk)
            # If someone tries to flip posted via normal save, reject it
            if not old.posted and self.posted:
                raise ValidationError("Use Journal.post() to post a journal.")
            # If already posted, block edits (optional strictness)
            if old.posted:
                raise ValidationError("Cannot modify a posted journal.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Journal {self.id} ({self.date})"


from django.core.exceptions import ValidationError

class JournalLine(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def clean(self):
        # this runs in ModelForms (admin) and can be invoked manually too
        if self.journal_id and self.journal.posted:
            raise ValidationError(_("Cannot modify lines on a posted journal."))

        if self.debit < 0 or self.credit < 0:
            raise ValidationError(_("Debit/Credit cannot be negative."))

        if self.debit and self.credit:
            raise ValidationError(_("A line cannot have both debit and credit."))

        if self.debit == 0 and self.credit == 0:
            raise ValidationError(_("A line cannot be all zero."))

    def save(self, *args, **kwargs):
        if self.journal_id:
            # hard stop even outside forms
            Journal.objects.only("posted").get(pk=self.journal_id)  # ensure exists
            if self.journal.posted:
                raise ValidationError("Cannot save JournalLine on a posted journal.")
        return super().save(*args, **kwargs)

class Meta:
        constraints = [
            # Debit and credit must be non-negative
            CheckConstraint(
                condition=Q(debit__gte=0) & Q(credit__gte=0),
                name="jl_non_negative",
            ),
            # Cannot have both debit and credit on the same line
            CheckConstraint(
                condition=Q(debit=0) | Q(credit=0),
                name="jl_not_both_sides",
            ),
        ]
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


class Address(models.Model):
    label = models.CharField(max_length=50, blank=True, help_text=_("e.g. Billing, Delivery"))
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=2, blank=True, help_text=_("ISO-2 country code"))

    attention = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["country", "postal_code", "city", "line1"]

    def __str__(self):
        parts = [self.line1, self.postal_code, self.city, self.country]
        return ", ".join([p for p in parts if p])

class PaymentTerms(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="payment_terms")
    code = models.CharField(max_length=20)   # e.g. NET14, NET30
    name = models.CharField(max_length=100)
    days = models.PositiveIntegerField(default=14)

    class Meta:
        unique_together = ("entity", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.days} days)"

class DebtorGroup(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="debtor_groups")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)

    ar_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="debtor_groups_ar",
        help_text=_("Accounts receivable control account for this group"),
    )

    default_payment_terms = models.ForeignKey(
        PaymentTerms,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="debtor_groups_default",
    )

    class Meta:
        unique_together = ("entity", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.name}"

class Debtor(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="debtors")
    number = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    group = models.ForeignKey(
        DebtorGroup,
        on_delete=models.PROTECT,
        related_name="debtors",
    )

    payment_terms = models.ForeignKey(
        PaymentTerms,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="debtors",
        help_text=_("If blank, group default is used"),
    )

    billing_address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="billing_debtors",
    )

    delivery_address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="delivery_debtors",
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ("entity", "number")
        ordering = ["number"]

    def __str__(self):
        return f"{self.number} – {self.name}"

    @property
    def effective_payment_terms(self):
        return self.payment_terms or self.group.default_payment_terms

    @property
    def ar_account(self):
        # AR account comes from group (as requested)
        return self.group.ar_account

class VatGroup(models.Model):
    entity = models.ForeignKey(
        Entity,
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

    def __str__(self):
        return self.name


class VatCode(models.Model):
    class VatType(models.TextChoices):
        SALE = "SALE", "Salg"
        PURCHASE = "PURCHASE", "Køb"

    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="vat_codes",
    )

    group = models.ForeignKey(
        VatGroup,
        on_delete=models.PROTECT,
        related_name="vat_codes",
        default=None,
    )

    # Core identifiers
    code = models.CharField(max_length=20)              # momskode NY (preferred)
    legacy_code = models.CharField(max_length=20, blank=True)  # momskode (old)

    name = models.CharField(max_length=255)             # overskrift
    description = models.TextField(blank=True)          # vejledning

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

    # Reporting
    reporting_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Momsangivelse / reporting description",
    )

    # Applicability flags (normalized from the 1–5 columns)
    dk_only = models.BooleanField(default=False)
    dk_mixed = models.BooleanField(default=False)
    international = models.BooleanField(default=False)
    international_mixed = models.BooleanField(default=False)
    special_scheme = models.BooleanField(default=False)

    class Meta:
        unique_together = ("entity", "code")
        ordering = ["group__code", "code"]

    def __str__(self):
        return f"{self.code} – {self.name}"


class ItemGroup(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="item_groups")

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)

    # Defaults used when Item doesn't override
    default_sales_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="item_groups_sales",
        help_text=_("Default revenue account for items in this group"),
    )

    default_cogs_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="item_groups_cogs",
        help_text=_("Default cost-of-goods-sold account (optional)"),
    )

    default_inventory_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="item_groups_inventory",
        help_text=_("Default inventory/stock account (optional)"),
    )

    default_vat_code = models.ForeignKey(
        "VatCode",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="item_groups_default_vat",
        help_text=_("Default VAT code for sales of items in this group"),
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("entity", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.name}"


class Item(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="items")

    sku = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    group = models.ForeignKey(
        ItemGroup,
        on_delete=models.PROTECT,
        related_name="items",
    )

    # Optional overrides (leave blank to use group defaults)
    sales_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="items_sales",
        help_text=_("Overrides group default sales account"),
    )

    cogs_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="items_cogs",
        help_text=_("Overrides group default COGS account"),
    )

    inventory_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="items_inventory",
        help_text=_("Overrides group default inventory account"),
    )

    vat_code = models.ForeignKey(
        "VatCode",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="items_vat",
        help_text=_("Overrides group default VAT code"),
    )

    class Meta:
        unique_together = ("entity", "sku")
        ordering = ["sku"]

    def __str__(self):
        return f"{self.sku} – {self.name}"

    def clean(self):
        if self.group and self.group.entity_id != self.entity_id:
            raise ValidationError({"group": "Item group entity must match item entity."})

        for field in ["sales_account", "cogs_account", "inventory_account"]:
            acc = getattr(self, field)
            if acc and acc.entity_id != self.entity_id:
                raise ValidationError({field: "Account entity must match item entity."})

        if self.vat_code and self.vat_code.entity_id != self.entity_id:
            raise ValidationError({"vat_code": "VAT code entity must match item entity."})
        
    # Effective values used for posting
    @property
    def effective_sales_account(self):
        return self.sales_account or self.group.default_sales_account

    @property
    def effective_cogs_account(self):
        return self.cogs_account or self.group.default_cogs_account

    @property
    def effective_inventory_account(self):
        return self.inventory_account or self.group.default_inventory_account

    @property
    def effective_vat_code(self):
        return self.vat_code or self.group.default_vat_code


