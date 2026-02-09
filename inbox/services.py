from django.db import transaction
from .models import InboxDocument, InboxExtractionJob

@transaction.atomic
def convert_to_purchase_invoice(doc: InboxDocument, user) -> int:
    """STUB: replace with real purchase invoice creation."""
    if doc.converted_purchase_invoice_id:
        return int(doc.converted_purchase_invoice_id)

    created_invoice_id = 100000 + doc.id  # placeholder
    doc.converted_purchase_invoice_id = created_invoice_id
    doc.status = InboxDocument.Status.CONVERTED
    doc.save(update_fields=["converted_purchase_invoice_id", "status"])
    return created_invoice_id


@transaction.atomic
def queue_extraction(doc: InboxDocument, provider: str = "external") -> InboxExtractionJob:
    job = InboxExtractionJob.objects.create(
        document=doc,
        provider=provider,
        status=InboxExtractionJob.Status.QUEUED,
        request_payload={"document_id": doc.id},
    )
    doc.status = InboxDocument.Status.EXTRACTING
    doc.save(update_fields=["status"])
    return job
