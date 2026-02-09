from django import forms
from .models import InboxDocument

class InboxDocumentForm(forms.ModelForm):
    class Meta:
        model = InboxDocument
        fields = [
            "doc_type",
            "title",
            "vendor_name",
            "invoice_no",
            "doc_date",
            "total_amount",
            "currency",
            "note",
        ]
