from django.conf import settings
from django.db import models
from django.utils import timezone
from core.models import Account, Entity
from core.models.iso_codes import IsoCurrencyCodes
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
import os

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
    vendor_name = models.ForeignKey("masterdata.Creditor", on_delete=models.SET_NULL, null=True, blank=True)
    invoice_no = models.CharField(max_length=100, blank=True, default="")
    doc_date = models.DateField(null=True, blank=True)

    gl_account = models.ForeignKey(
        "core.Account",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="inbox_documents_as_gl",
        )
    contra_account = models.ForeignKey(
        "core.Account",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="inbox_documents_as_contra",
    )

    total_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.ForeignKey("core.IsoCurrencyCodes", on_delete=models.PROTECT, null=True, blank=True)

    converted_purchase_invoice_id = models.BigIntegerField(null=True, blank=True)
    
    attachments = GenericRelation("inbox.Attachment", related_query_name="inbox_document")

    def __str__(self):
        t = self.title or self.vendor_name or "(incoming doc)"
        return f"{t} (#{self.pk})"


def inbox_upload_path(instance, filename: str) -> str:
    """
    Generic upload path for attachments.

    Works for:
      - InboxDocument (entity on document)
      - Journal (entity on journal)
      - Anything else with .entity or .entity_id
    """

    target = getattr(instance, "content_object", None)

    # Fallback: if you're still using old InboxAttachment in some places
    if target is None and hasattr(instance, "document"):
        target = instance.document

    # entity id resolution
    entity_id = None
    if target is not None:
        # If target has entity FK
        if hasattr(target, "entity_id") and target.entity_id:
            entity_id = target.entity_id
        elif hasattr(target, "entity") and target.entity:
            # could be int or model
            entity_id = getattr(target.entity, "id", target.entity)

    if entity_id is None:
        entity_id = "unknown"

    # group by date for sanity
    dt = timezone.now()
    yyyy = dt.strftime("%Y")
    mm = dt.strftime("%m")

    # keep filename safe-ish
    base = os.path.basename(filename)

    # Optional: include target type for readability
    ct = getattr(instance, "content_type", None)
    model_label = getattr(ct, "model", "object") if ct else "object"

    obj_id = getattr(instance, "object_id", None) or "unknown"

    return f"entity_{entity_id}/{model_label}/{obj_id}/{yyyy}/{mm}/{base}"


class Attachment(models.Model):
    # Generic link: can attach to InboxDocument, Journal, JournalLine, etc.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField(db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    uploaded_at = models.DateTimeField(default=timezone.now)

    file = models.FileField(upload_to=inbox_upload_path)
    original_name = models.CharField(max_length=255, blank=True, default="")
    content_type_guess = models.CharField(max_length=100, blank=True, default="")
    is_primary = models.BooleanField(default=False)
        
    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"Attachment#{self.pk} obj={self.content_type_id}:{self.object_id}"


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
