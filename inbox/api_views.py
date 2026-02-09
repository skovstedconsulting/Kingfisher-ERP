from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import InboxDocument, InboxAttachment


def _get_entity(request):
    try:
        return request.user.profile.entity
    except Exception:
        return None


@login_required
@require_http_methods(["GET"])
def api_list_documents(request):
    entity = _get_entity(request)
    qs = InboxDocument.objects.all().order_by("-created_at")[:200]
    if entity is not None:
        qs = qs.filter(entity=entity)

    data = []
    for d in qs:
        primary = d.attachments.filter(is_primary=True).first() or d.attachments.first()
        data.append({
            "id": d.id,
            "doc_type": d.doc_type,
            "status": d.status,
            "title": d.title,
            "vendor_name": d.vendor_name,
            "invoice_no": d.invoice_no,
            "total_amount": str(d.total_amount) if d.total_amount is not None else None,
            "currency": d.currency,
            "created_at": d.created_at.isoformat(),
            "primary_attachment_url": primary.file.url if primary else None,
        })
    return JsonResponse({"results": data})


@login_required
@require_http_methods(["POST"])
def api_create_document(request):
    entity = _get_entity(request)

    doc = InboxDocument.objects.create(
        entity=entity if entity is not None else 0,
        created_by=request.user,
        doc_type=request.POST.get("doc_type") or InboxDocument.DocType.OTHER,
        title=request.POST.get("title") or "",
        note=request.POST.get("note") or "",
        vendor_name=request.POST.get("vendor_name") or "",
        invoice_no=request.POST.get("invoice_no") or "",
        currency=request.POST.get("currency") or "DKK",
        status=InboxDocument.Status.NEW,
    )

    f = request.FILES.get("file")
    if f:
        doc.attachments.update(is_primary=False)
        InboxAttachment.objects.create(
            document=doc,
            file=f,
            original_name=getattr(f, "name", "") or "",
            content_type=getattr(f, "content_type", "") or "",
            is_primary=True,
        )

    return JsonResponse({"id": doc.id, "status": doc.status})


@login_required
@require_http_methods(["POST"])
def api_attach_file(request, pk: int):
    entity = _get_entity(request)
    doc = InboxDocument.objects.get(pk=pk, **({"entity": entity} if entity is not None else {}))

    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "Missing file"}, status=400)

    is_primary = (request.POST.get("is_primary") or "false").lower() in ("1", "true", "yes", "on")
    if is_primary:
        doc.attachments.update(is_primary=False)

    att = InboxAttachment.objects.create(
        document=doc,
        file=f,
        original_name=getattr(f, "name", "") or "",
        content_type=getattr(f, "content_type", "") or "",
        is_primary=is_primary,
    )

    return JsonResponse({"attachment_id": att.id})
