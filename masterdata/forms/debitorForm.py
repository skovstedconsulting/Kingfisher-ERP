from django import forms
from masterdata.models import Debtor, DebtorGroup


class DebtorForm(forms.ModelForm):
    class Meta:
        model = Debtor
        fields = ["group", "number", "name", "vat_area"]

    def __init__(self, *args, entity=None, **kwargs):
        super().__init__(*args, **kwargs)
        if entity is not None:
            self.fields["group"].queryset = DebtorGroup.objects.filter(entity=entity).order_by("code")
