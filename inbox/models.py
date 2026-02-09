from django.conf import settings
from django.db import models
from django.utils import timezone

try:
    from core.models import Entity
except Exception:  # pragma: no cover
    Entity = None  # type: ignore


class InboxDocument(models.Model):
    class DocType(models.TextChoices):
        ORDER = "order", "Order"
        PURCHASE_INVOICE = "purchase_invoice", "Purchase invoice"
        RECEIPT = "receipt", "Receipt"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_REVIEW = "in_review", "In review"
        EXTRACTING = "extracting", "Extracting"
        READY = "ready", "Ready"
        CONVERTED = "converted", "Converted"
        REJECTED = "rejected", "Rejected"

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, db_index=True) if Entity else models.IntegerField(db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inbox_documents")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    doc_type = models.CharField(max_length=30, choices=DocType.choices, default=DocType.OTHER, db_index=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW, db_index=True)

    title = models.CharField(max_length=255, blank=True, default="")
    note = models.TextField(blank=True, default="")

    # Common header fields (optional)
    vendor_name = models.CharField(max_length=255, blank=True, default="")
    invoice_no = models.CharField(max_length=100, blank=True, default="")
    doc_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True, default="DKK")

    converted_purchase_invoice_id = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        t = self.title or self.vendor_name or "(incoming doc)"
        return f"{t} (#{self.pk})"


def inbox_upload_path(instance, filename: str) -> str:
    entity_id = instance.document.entity_id if hasattr(instance.document, "entity_id") else instance.document.entity
    return f"inbox/{entity_id}/{instance.document_id}/{filename}"


class InboxAttachment(models.Model):
    document = models.ForeignKey(InboxDocument, on_delete=models.CASCADE, related_name="attachments")
    uploaded_at = models.DateTimeField(default=timezone.now)

    file = models.FileField(upload_to=inbox_upload_path)
    original_name = models.CharField(max_length=255, blank=True, default="")
    content_type = models.CharField(max_length=100, blank=True, default="")
    is_primary = models.BooleanField(default=True)

    def __str__(self):
        return f"Attachment#{self.pk} doc={self.document_id}"


class InboxExtractionJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        ERROR = "error", "Error"

    document = models.ForeignKey(InboxDocument, on_delete=models.CASCADE, related_name="extraction_jobs")
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)

    provider = models.CharField(max_length=50, default="external", db_index=True)
    request_payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")

    def __str__(self):
        return f"ExtractionJob#{self.pk} doc={self.document_id} {self.status}"
