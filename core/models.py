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
