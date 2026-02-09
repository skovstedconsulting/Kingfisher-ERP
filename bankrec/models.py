# bankrec/models.py
from __future__ import annotations
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint

from django.utils import timezone

from core.models import Account
from ledger.models.journal_line import JournalLine   # <-- tilpas import-path hvis din fil hedder andet


class BankReconciliationSetup(models.Model):
    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="bankrec_setups")
    name = models.CharField(max_length=120, default="Default bank setup")
    
    bank_account_no = models.CharField(max_length=64, blank=True, default="", help_text="IBAN / bankkonto-id (valgfri)")

    # ✅ Bankkonto i finans = core.Account
    gl_bank_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="bankrec_setups",
        help_text="Finanskonto der repræsenterer bankkontoen",
    )

    amount_tolerance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    date_window_days = models.IntegerField(default=3)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("entity", "name")]

    def __str__(self) -> str:
        return f"{self.entity} – {self.name}"


class BankStatementStaging(models.Model):
    STATUS_NEW = "new"
    STATUS_READY = "ready"
    STATUS_RECONCILING = "reconciling"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_READY, "Ready"),
        (STATUS_RECONCILING, "Reconciling"),
        (STATUS_CLOSED, "Closed"),
    ]

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="bank_staging_headers")
    setup = models.ForeignKey(BankReconciliationSetup, on_delete=models.PROTECT, related_name="staging_headers")

    statement_id = models.CharField(max_length=80)
    statement_date_from = models.DateField(null=True, blank=True)
    statement_date_to = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="DKK")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)

    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = [("entity", "statement_id")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.entity} {self.statement_id}"


class BankStatementStagingLine(models.Model):
    header = models.ForeignKey(BankStatementStaging, on_delete=models.CASCADE, related_name="lines")

    bank_tx_id = models.CharField(max_length=120)
    booking_date = models.DateField()
    value_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    text = models.CharField(max_length=512, blank=True, default="")
    reference = models.CharField(max_length=128, blank=True, default="")
    raw_payload = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = [("header", "bank_tx_id")]
        ordering = ["booking_date", "id"]


class BankReconciliationSession(models.Model):
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [(STATUS_OPEN, "Open"), (STATUS_CLOSED, "Closed")]

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="bankrec_sessions")
    setup = models.ForeignKey(BankReconciliationSetup, on_delete=models.PROTECT, related_name="sessions")
    staging = models.OneToOneField(BankStatementStaging, on_delete=models.PROTECT, related_name="reconciliation_session")

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_OPEN)

    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    gl_date_from = models.DateField(null=True, blank=True)
    gl_date_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class BankMatch(models.Model):
    #session = models.ForeignKey(BankReconciliationSession, on_delete=models.CASCADE, related_name="matches")
    #created_at = models.DateTimeField(default=timezone.now)
    #created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=255, blank=True, default="")

    # ✅ match imod JournalLine (bankkonto-linjer)
    #bank_lines = models.ManyToManyField(BankStatementStagingLine, through="BankMatchBankLine", related_name="matches")
    #gl_lines = models.ManyToManyField(JournalLine, through="BankMatchJournalLine", related_name="bank_matches")
    
    session = models.ForeignKey(
        "bankrec.BankReconciliationSession",
        on_delete=models.CASCADE,
        related_name="matches",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL
    )

    bank_lines = models.ManyToManyField(
        "bankrec.BankStatementStagingLine",
        through="bankrec.BankMatchBankLine",
        related_name="bank_matches",
    )
    gl_lines = models.ManyToManyField(
        "ledger.JournalLine",
        through="bankrec.BankMatchJournalLine",
        related_name="bank_matches",
    )


    def __str__(self) -> str:
        return f"Match {self.id} (session {self.session_id})"


class BankMatchBankLine(models.Model):
    #match = models.ForeignKey(BankMatch, on_delete=models.CASCADE)
    #bank_line = models.ForeignKey(BankStatementStagingLine, on_delete=models.PROTECT)
    #matched_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    #class Meta:
    #    unique_together = [("match", "bank_line")]

    match = models.ForeignKey(BankMatch, on_delete=models.CASCADE)
    bank_line = models.ForeignKey(
        "bankrec.BankStatementStagingLine", on_delete=models.CASCADE
    )

    matched_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    class Meta:
        unique_together = [("match", "bank_line")]
        constraints = [
            # 🔒 a bank line can only be used once EVER
            UniqueConstraint(
                fields=["bank_line"],
                name="uniq_bank_line_global_match",
            ),
        ]



class BankMatchJournalLine(models.Model):
    match = models.ForeignKey(BankMatch, on_delete=models.CASCADE)
    gl_line = models.ForeignKey("ledger.JournalLine", on_delete=models.CASCADE)
    matched_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [("match", "gl_line")]
        constraints = [
            UniqueConstraint(fields=["gl_line"], name="uniq_gl_line_global_match"),
        ]

