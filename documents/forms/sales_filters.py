from django import forms
from documents.models import SalesDocument
from masterdata.models import Debtor  # adjust if your app name differs


class SalesDocumentFilterForm(forms.Form):
    state = forms.ChoiceField(
        required=False,
        choices=[("", "All states")] + list(SalesDocument.State.choices),
    )
    debtor = forms.ModelChoiceField(
        required=False,
        queryset=Debtor.objects.none(),
        empty_label="All debtors",
    )

    def __init__(self, *args, entity=None, **kwargs):
        super().__init__(*args, **kwargs)
        if entity is not None:
            # assumes Debtor has entity FK
            self.fields["debtor"].queryset = Debtor.objects.filter(entity=entity).order_by("name", "number")
        else:
            self.fields["debtor"].queryset = Debtor.objects.all().order_by("name", "number")
