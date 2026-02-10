from decimal import Decimal, InvalidOperation
from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory, BaseInlineFormSet

from ledger.models.journal import Journal
from ledger.models.journal_line import JournalLine
from core.models import Account


class JournalForm(forms.ModelForm):
    auto_fill_base = forms.BooleanField(required=False, initial=True)
    auto_balance = forms.BooleanField(required=False, initial=False)
    balancing_account = forms.ModelChoiceField(queryset=Account.objects.none(), required=False)
    balancing_description = forms.CharField(required=False, initial="Auto balance")

    class Meta:
        model = Journal
        fields = ["date", "reference"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
        }

    def __init__(self, *args, entity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].input_formats = ["%Y-%m-%d"]

        if entity is not None:
            qs = Account.objects.all()
            if hasattr(Account, "entity_id"):
                qs = qs.filter(entity=entity)
            self.fields["balancing_account"].queryset = qs


class JournalLineForm(forms.ModelForm):
    class Meta:
        model = JournalLine
        fields = [
            "account",
            "description",
            "currency",
            "fx_rate",
            "debit_tx",
            "credit_tx",
            "debit_base",
            "credit_base",
        ]


class BaseJournalLineFormSet(BaseInlineFormSet):
    """
    Prevent saving if journal is not balanced in base currency.
    """
    def clean(self):
        super().clean()

        if any(self.errors):
            # If individual forms have errors, don't add a misleading balance error
            return

        debit = Decimal("0")
        credit = Decimal("0")

        for form in self.forms:
            # Skip empty extra forms
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            # If form is totally empty (common for extra forms), skip it
            if not form.has_changed() and not form.instance.pk:
                continue

            d = form.cleaned_data.get("debit_base") or Decimal("0")
            c = form.cleaned_data.get("credit_base") or Decimal("0")

            try:
                debit += Decimal(d)
                credit += Decimal(c)
            except (InvalidOperation, TypeError):
                # Let field validation handle bad inputs
                return

        diff = debit - credit

        # Tolerance for rounding (e.g., 0.01)
        if diff.copy_abs() > Decimal("0.005"):
            raise ValidationError(
                f"Journal is not balanced. Debit (base) {debit:.2f} vs Credit (base) {credit:.2f} (diff {diff:.2f})."
            )


JournalLineFormSet = inlineformset_factory(
    parent_model=Journal,
    model=JournalLine,
    form=JournalLineForm,
    formset=BaseJournalLineFormSet,   # <-- important
    extra=5,
    can_delete=True,
)
