from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, F, Sum
from django.db.models.constraints import CheckConstraint

from django.utils import timezone

from config import settings

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

    #Until you have Supplier/Vendor groups, add on Entity:
    default_ap_account = models.ForeignKey(
        "core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

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
    output_vat_account = models.ForeignKey(
        "core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+",
        help_text=_("Sales VAT (udgående moms) account")
    )
    input_vat_account = models.ForeignKey(
        "core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+",
        help_text=_("Purchase VAT (indgående moms) account")
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

class DocumentStatus(models.Model):
    """
    Configurable status values per document type.
    Example:
      - Sales Order: Draft, Confirmed, Delivered, Invoiced, Cancelled
      - Purchase Invoice: Draft, Approved, Posted, Cancelled
    """

    class DocumentType(models.TextChoices):
        SALES_OFFER = "SALES_OFFER", _("Sales offer")
        SALES_ORDER = "SALES_ORDER", _("Sales order")
        SALES_INVOICE = "SALES_INVOICE", _("Sales invoice")
        SALES_CREDIT_NOTE = "SALES_CREDIT_NOTE", _("Sales credit note")
        PURCHASE_ORDER = "PURCHASE_ORDER", _("Purchase order")
        PURCHASE_INVOICE = "PURCHASE_INVOICE", _("Purchase invoice")
        PURCHASE_CREDIT_NOTE = "PURCHASE_CREDIT_NOTE", _("Purchase credit note")

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="document_statuses")
    doc_type = models.CharField(max_length=40, choices=DocumentType.choices)

    code = models.CharField(max_length=30)  # e.g. DRAFT / APPROVED / POSTED
    name = models.CharField(max_length=80)  # human label
    is_default = models.BooleanField(default=False)

    # Optional flags you’ll likely want later:
    is_final = models.BooleanField(default=False)      # “locked” state
    is_cancelled = models.BooleanField(default=False)  # cancellation state

    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("entity", "doc_type", "code")
        ordering = ("entity", "doc_type", "sort_order", "code")
        constraints = [
            # only one default per (entity, doc_type)
            models.UniqueConstraint(
                fields=["entity", "doc_type"],
                condition=Q(is_default=True),
                name="uniq_default_status_per_entity_and_type",
            ),
        ]

    def __str__(self):
        return f"{self.entity} {self.doc_type}: {self.code} ({self.name})"


class Document(models.Model):
    """
    Single table for all commercial documents.
    Each specific doc type will be exposed via proxy models (admin entries).
    """

    class DocumentType(models.TextChoices):
        SALES_OFFER = DocumentStatus.DocumentType.SALES_OFFER
        SALES_ORDER = DocumentStatus.DocumentType.SALES_ORDER
        SALES_INVOICE = DocumentStatus.DocumentType.SALES_INVOICE
        SALES_CREDIT_NOTE = DocumentStatus.DocumentType.SALES_CREDIT_NOTE
        PURCHASE_ORDER = DocumentStatus.DocumentType.PURCHASE_ORDER
        PURCHASE_INVOICE = DocumentStatus.DocumentType.PURCHASE_INVOICE
        PURCHASE_CREDIT_NOTE = DocumentStatus.DocumentType.PURCHASE_CREDIT_NOTE

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=40, choices=DocumentType.choices)

    number = models.CharField(max_length=40, blank=True)  # your numbering logic later
    date = models.DateField()

    reference = models.CharField(max_length=255, blank=True)

    # Parties – keep generic at first; you can replace with Debtor/Vendor models later
    debtor = models.ForeignKey("core.Debtor", null=True, blank=True, on_delete=models.PROTECT, related_name="sales_documents")
    # supplier = models.ForeignKey("core.Supplier", null=True, blank=True, on_delete=models.PROTECT, related_name="purchase_documents")

    status = models.ForeignKey(
        DocumentStatus,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="documents",
        help_text=_("Must belong to the same entity and document type."),
    )

    currency = models.ForeignKey("core.IsoCurrencyCodes", null=True, blank=True, on_delete=models.PROTECT)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    posted_journal = models.OneToOneField(
        "core.Journal", null=True, blank=True, on_delete=models.PROTECT, related_name="source_document"
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional: lock flag if status is_final, but better computed from status
    # is_locked = models.BooleanField(default=False)

    class Meta:
        ordering = ("-date", "-id")
        indexes = [
            models.Index(fields=["entity", "doc_type", "date"]),
            models.Index(fields=["entity", "doc_type", "number"]),
        ]

    def clean(self):
        # 1) Require correct party depending on type (basic example)
        if self.doc_type in {
            self.DocumentType.SALES_OFFER,
            self.DocumentType.SALES_ORDER,
            self.DocumentType.SALES_INVOICE,
            self.DocumentType.SALES_CREDIT_NOTE,
        } and not self.debtor_id:
            raise ValidationError({"debtor": _("Debtor is required for sales documents.")})

        # 2) Status must match entity and doc_type
        if self.status_id:
            if self.status.entity_id != self.entity_id:
                raise ValidationError({"status": _("Status must belong to the same entity.")})
            if self.status.doc_type != self.doc_type:
                raise ValidationError({"status": _("Status must belong to the same document type.")})

    def save(self, *args, **kwargs):
        # ensure clean() runs when saving outside forms
        self.full_clean()
        # Auto-assign default status if missing
        if not self.status_id:
            default_status = (
                DocumentStatus.objects
                .filter(entity=self.entity, doc_type=self.doc_type, is_default=True, is_active=True)
                .order_by("sort_order", "id")
                .first()
            )
            if default_status:
                self.status = default_status
        super().save(*args, **kwargs)

    def _get_ar_account(self):
        if not self.debtor_id:
            raise ValidationError("Debtor is required.")
        if not self.debtor.group_id or not self.debtor.group.ar_account_id:
            raise ValidationError("Debtor group with AR account is required.")
        return self.debtor.group.ar_account

    def _get_ap_account(self):
        if not self.entity.default_ap_account_id:
            raise ValidationError("Entity.default_ap_account is required for purchase posting.")
        return self.entity.default_ap_account

    def _vat_rate(self, vat_code) -> Decimal:
        # Your VatCode.rate is a decimal fraction (0.2500) in earlier model
        return vat_code.rate or Decimal("0")

    def _effective_sales_account_for_line(self, line):
        if line.sales_account_id:
            return line.sales_account
        if line.item_id:
            acc = line.item.effective_sales_account
            if acc:
                return acc
        raise ValidationError(f"Missing sales account for line {line.line_no}.")

    def _effective_expense_account_for_line(self, line):
        if line.expense_account_id:
            return line.expense_account
        if line.item_id:
            # if you don’t have effective expense yet, wire to cogs_account
            acc = line.item.effective_cogs_account if hasattr(line.item, "effective_cogs_account") else None
            if acc:
                return acc
        raise ValidationError(f"Missing expense/COGS account for line {line.line_no}.")

    def _effective_vat_code_for_line(self, line):
        if line.vat_code_id:
            return line.vat_code
        if line.item_id:
            vat = line.item.effective_vat_code
            if vat:
                return vat
        return None  # allow no-VAT lines

    def _assert_can_post(self):
        if self.posted_journal_id:
            raise ValidationError("Document is already posted.")
        if not self.lines.exists():
            raise ValidationError("Document has no lines.")
        if self.is_locked:
            raise ValidationError("Document is locked (final status).")

    @transaction.atomic
    def post(self, by_user=None):
        # Lock document row to prevent double posting in concurrency
        doc = Document.objects.select_for_update().get(pk=self.pk)
        doc._assert_can_post()

        # Build journal
        from core.models import Journal, JournalLine  # adjust import to your module layout

        j = Journal.objects.create(
            entity=doc.entity,
            date=doc.date,
            reference=f"{doc.get_doc_type_display()} {doc.number or doc.pk}",
            posted=False,
        )

        # Helper: add a journal line
        def add_line(account, debit=Decimal("0.00"), credit=Decimal("0.00"), desc=""):
            if debit and credit:
                raise ValidationError("JournalLine cannot have both debit and credit.")
            JournalLine.objects.create(
                journal=j,
                account=account,
                description=desc[:255],
                debit=debit,
                credit=credit,
            )

        # Accumulators
        total_net = Decimal("0.00")
        total_vat = Decimal("0.00")

        # Post lines
        for line in doc.lines.select_related("item", "vat_code").all():
            net = line.net_amount
            vat_code = doc._effective_vat_code_for_line(line)
            vat_amt = Decimal("0.00")

            if vat_code:
                rate = doc._vat_rate(vat_code)
                vat_amt = (net * rate).quantize(Decimal("0.01"))
            total_net += net
            total_vat += vat_amt

            # Determine behavior per doc type
            if doc.doc_type in {doc.DocumentType.SALES_INVOICE, doc.DocumentType.SALES_CREDIT_NOTE}:
                revenue_acc = doc._effective_sales_account_for_line(line)
                # Credit revenue on invoice, debit revenue on credit note
                if doc.doc_type == doc.DocumentType.SALES_INVOICE:
                    add_line(revenue_acc, credit=net.quantize(Decimal("0.01")), desc=line.description or "Revenue")
                else:
                    add_line(revenue_acc, debit=net.quantize(Decimal("0.01")), desc=line.description or "Revenue reversal")

                if vat_code and vat_amt != 0:
                    if not vat_code.output_vat_account_id:
                        raise ValidationError(f"Missing output VAT account on VAT code {vat_code.code}.")
                    if doc.doc_type == doc.DocumentType.SALES_INVOICE:
                        add_line(vat_code.output_vat_account, credit=vat_amt, desc=f"Output VAT {vat_code.code}")
                    else:
                        add_line(vat_code.output_vat_account, debit=vat_amt, desc=f"Output VAT reversal {vat_code.code}")

            elif doc.doc_type in {doc.DocumentType.PURCHASE_INVOICE, doc.DocumentType.PURCHASE_CREDIT_NOTE}:
                exp_acc = doc._effective_expense_account_for_line(line)
                # Debit expense on invoice, credit on credit note
                if doc.doc_type == doc.DocumentType.PURCHASE_INVOICE:
                    add_line(exp_acc, debit=net.quantize(Decimal("0.01")), desc=line.description or "Expense")
                else:
                    add_line(exp_acc, credit=net.quantize(Decimal("0.01")), desc=line.description or "Expense reversal")

                if vat_code and vat_amt != 0:
                    if not vat_code.input_vat_account_id:
                        raise ValidationError(f"Missing input VAT account on VAT code {vat_code.code}.")
                    if doc.doc_type == doc.DocumentType.PURCHASE_INVOICE:
                        add_line(vat_code.input_vat_account, debit=vat_amt, desc=f"Input VAT {vat_code.code}")
                    else:
                        add_line(vat_code.input_vat_account, credit=vat_amt, desc=f"Input VAT reversal {vat_code.code}")
            else:
                raise ValidationError(f"Posting not implemented for {doc.doc_type} yet.")

        gross = (total_net + total_vat).quantize(Decimal("0.01"))

        # Control account line (AR/AP)
        if doc.doc_type in {doc.DocumentType.SALES_INVOICE, doc.DocumentType.SALES_CREDIT_NOTE}:
            ar = doc._get_ar_account()
            if doc.doc_type == doc.DocumentType.SALES_INVOICE:
                add_line(ar, debit=gross, desc="Accounts receivable")
            else:
                add_line(ar, credit=gross, desc="Accounts receivable reversal")
        else:
            ap = doc._get_ap_account()
            if doc.doc_type == doc.DocumentType.PURCHASE_INVOICE:
                add_line(ap, credit=gross, desc="Accounts payable")
            else:
                add_line(ap, debit=gross, desc="Accounts payable reversal")

        # Validate balance
        sums = j.lines.aggregate(
            d=models.Sum("debit"),
            c=models.Sum("credit"),
        )
        d = (sums["d"] or Decimal("0.00")).quantize(Decimal("0.01"))
        c = (sums["c"] or Decimal("0.00")).quantize(Decimal("0.01"))
        if d != c:
            raise ValidationError(f"Journal not balanced. Debit={d} Credit={c}")

        # Mark posted
        j.posted = True
        j.save(update_fields=["posted"])

        doc.posted_journal = j
        doc.posted_at = timezone.now()
        doc.posted_by = by_user
        doc.save(update_fields=["posted_journal", "posted_at", "posted_by"])

        return j

    @property
    def is_locked(self):
        return bool(self.status_id and self.status.is_final)

    def __str__(self):
        return f"{self.get_doc_type_display()} {self.number or self.pk}"

class DocumentLine(models.Model):
    document = models.ForeignKey("core.Document", on_delete=models.CASCADE, related_name="lines")

    line_no = models.PositiveIntegerField(default=1)
    description = models.CharField(max_length=255, blank=True)

    item = models.ForeignKey("core.Item", null=True, blank=True, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("1.0000"))
    unit_price = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0.0000"))
    discount_pct = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.0000"))  # 0..1

    # Allow override of accounts per line (optional). If null -> use item effective accounts.
    sales_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    expense_account = models.ForeignKey("core.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    vat_code = models.ForeignKey("core.VatCode", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        ordering = ("document_id", "line_no", "id")

    def clean(self):
        # Prevent edits when posted
        if self.document_id and getattr(self.document, "posted_journal_id", None):
            raise ValidationError(_("Cannot modify lines on a posted document."))

        if self.quantity == 0:
            raise ValidationError({"quantity": _("Quantity cannot be zero.")})

        if self.discount_pct < 0 or self.discount_pct > 1:
            raise ValidationError({"discount_pct": _("Discount must be between 0 and 1 (e.g. 0.10).")})

    @property
    def net_amount(self) -> Decimal:
        return (self.quantity * self.unit_price) * (Decimal("1.0") - (self.discount_pct or Decimal("0")))

    def __str__(self):
        return f"{self.document} #{self.line_no}"