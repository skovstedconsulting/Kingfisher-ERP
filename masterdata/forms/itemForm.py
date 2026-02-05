from django import forms
from masterdata.models import Item, ItemGroup


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "group",
            "number",
            "name",
            "is_stock_item",
            "sales_price",
            "purchase_cost",
            "ean",
        ]

    def __init__(self, *args, entity=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._entity = entity
        if entity:
            self.fields["group"].queryset = ItemGroup.objects.filter(entity=entity)

        # ✅ allow blank in the HTML form
        self.fields["group"].required = False

    def clean(self):
        cleaned = super().clean()
        # no extra validation needed right now
        return cleaned

    def save(self, commit=True, entity=None):
        entity = entity or self._entity
        item = super().save(commit=False)

        # default group if user left it empty
        if not item.group and entity:
            item.group = ItemGroup.objects.filter(entity=entity).first()

        if commit:
            item.save()
        return item