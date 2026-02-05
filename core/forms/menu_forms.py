from django import forms
from core.models import Menu
from core.utils.url_choices import discover_named_urls

class MenuForm(forms.ModelForm):
    url = forms.ChoiceField(choices=(), required=False)

    class Meta:
        model = Menu
        fields = ["menu", "parent", "sort_order", "url", "active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["url"].choices = discover_named_urls()
        self.fields["sort_order"].help_text = "Lower numbers appear first."
