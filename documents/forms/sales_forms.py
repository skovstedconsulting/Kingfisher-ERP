from django import forms
from django.utils import timezone

from documents.models import SalesDocument, SalesLine
from core.models import IsoCurrencyCodes
from core.models import VatCode

class SalesDocumentForm(forms.ModelForm):
    """
    Usage:
        form = SalesDocumentForm(entity=request.user.profile.entity, data=request.POST or None)
    """

    class Meta:
        model = SalesDocument
        fields = [
            "date",
            "debtor",
            "currency",
            "reference",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "reference": forms.TextInput(attrs={"placeholder": "Optional reference"}),
        }

    def __init__(self, *args, entity=None, **kwargs):
        super().__init__(*args, **kwargs)

        # sensible default
        if not self.instance.pk and not self.initial.get("date"):
            self.initial["date"] = timezone.now().date()

        self._entity = entity

        # Entity-aware debtor filtering (and optional currency filtering)
        if entity is not None:
            # assumes Debtor has entity FK
            self.fields["debtor"].queryset = self.fields["debtor"].queryset.filter(entity=entity)

            # if you have per-entity currency rules, filter here; otherwise leave as-is
            # self.fields["currency"].queryset = self.fields["currency"].queryset.filter(...)
            
            # 🔒 limit currencies to entity if needed
            self.fields["currency"].queryset = IsoCurrencyCodes.objects.all()

            if not self.instance.pk and entity:
                self.initial.setdefault("currency", entity.base_currency_id)

    def save(self, commit=True):
        obj = super().save(commit=False)

        # ensure entity is set from request context (don’t trust the browser)
        if self._entity is not None and not obj.entity_id:
            obj.entity = self._entity

        if commit:
            obj.save()
            self.save_m2m()
        return obj


class SalesLineForm(forms.ModelForm):
    class Meta:
        model = SalesLine
        fields = [
            "item",
            "description",
            "qty",
            "unit_price_tx",
            "vat_code",
        ]
        widgets = {
            "description": forms.TextInput(attrs={"placeholder": "Optional (defaults from item)"}),
        }

    def __init__(self, *args, entity=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Entity-aware item filtering (assumes Item has entity FK)
        if entity is not None and "item" in self.fields:
            qs = self.fields["item"].queryset
            self.fields["item"].queryset = qs.filter(entity=entity)

        # ✅ VAT dropdown: show only VAT name
        if "vat_code" in self.fields:
            # optional: if VatCode has entity FK, filter it too
            qs = self.fields["vat_code"].queryset
            if entity is not None and hasattr(VatCode, "entity_id"):
                qs = qs.filter(entity=entity)
            self.fields["vat_code"].queryset = qs

            self.fields["vat_code"].label_from_instance = lambda obj: obj.name


SalesLineFormSet = forms.inlineformset_factory(
    SalesDocument,
    SalesLine,
    form=SalesLineForm,
    extra=1,
    can_delete=True,
)