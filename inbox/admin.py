from django.contrib import admin
from .models import InboxDocument, InboxExtractionJob
from .models import Attachment
from django.contrib.contenttypes.admin import GenericTabularInline  # ✅

class InboxAttachmentInline(GenericTabularInline):
    model = Attachment
    extra = 0
    fields = ("file", "original_name", "content_type_guess", "is_primary", "uploaded_at")
    readonly_fields = ("uploaded_at",)

@admin.register(InboxDocument)
class InboxDocumentAdmin(admin.ModelAdmin):
    inlines = [InboxAttachmentInline]
    list_display = ("id", "entity", "doc_type", "status", "vendor_name", "invoice_no", "doc_date", "created_at")
    list_filter = ("entity", "doc_type", "status")
    search_fields = ("title", "vendor_name", "invoice_no")

@admin.register(InboxExtractionJob)
class InboxExtractionJobAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "provider", "status", "created_at")
    list_filter = ("provider", "status")

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "content_type", "object_id", "original_name", "content_type_guess", "is_primary", "uploaded_at")
    list_filter = ("is_primary", "uploaded_at")
    search_fields = ("original_name", "content_type_guess")