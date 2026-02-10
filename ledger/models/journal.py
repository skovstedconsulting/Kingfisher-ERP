from django.db import models
from django.conf import settings
from django.utils import timezone
from django_fsm import FSMField, transition
from simple_history.models import HistoricalRecords
from decimal import Decimal

class Journal(models.Model):
    """Accounting journal.

    State is controlled by django-fsm to prevent manual 'posted' changes.
    """
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="journals")
    state = FSMField(default=State.DRAFT, choices=State.choices, protected=True, editable=False)

    number = models.CharField(max_length=40, blank=True, default="")
    date = models.DateField()
    reference = models.CharField(max_length=255, blank=True, default="")

    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    history = HistoricalRecords()

    class Meta:
        ordering = ("-date", "-id")
        indexes = [models.Index(fields=["entity", "state", "date"])]

    def __str__(self):
        return f"Journal {self.number or self.pk} ({self.state})"

    def allocate_number_if_missing(self):
        if self.number:
            return
        if not self.entity.default_series_journal_id:
            raise ValueError("Entity.default_series_journal is required.")
        self.number = self.entity.default_series_journal.allocate()

    def assert_balanced(self):
        """Validate that sum(debit_base) == sum(credit_base)."""
        sums = self.lines.aggregate(d=models.Sum("debit_base"), c=models.Sum("credit_base"))
        d = (sums["d"] or Decimal("0.00")).quantize(Decimal("0.01"))
        c = (sums["c"] or Decimal("0.00")).quantize(Decimal("0.01"))
        if d != c:
            raise ValueError(f"Journal not balanced. Debit={d} Credit={c}")

    
    @transition(field=state, source=State.DRAFT, target=State.POSTED)
    def post(self, by_user=None):
        self.allocate_number_if_missing()
        self.assert_balanced()

        self.posted_at = timezone.now()
        self.posted_by = by_user

        #self.save(update_fields=["state", "number", "posted_at", "posted_by"])

        # IMPORTANT: don't include update_fields with "state" when protected=True
        self.save()
