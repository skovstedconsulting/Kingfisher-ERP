from django.contrib import admin
from .models import InboxDocument, InboxAttachment, InboxExtractionJob

class InboxAttachmentInline(admin.TabularInline):
    model = InboxAttachment
    extra = 0

@admin.register(InboxDocument)
class InboxDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "entity", "doc_type", "status", "title", "vendor_name", "total_amount", "currency", "created_at")
    list_filter = ("doc_type", "status", "currency")
    search_fields = ("title", "vendor_name", "invoice_no")
    inlines = [InboxAttachmentInline]

@admin.register(InboxExtractionJob)
class InboxExtractionJobAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "provider", "status", "created_at")
    list_filter = ("provider", "status")
