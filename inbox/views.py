import mimetypes
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import InboxDocumentForm
from .models import InboxDocument, InboxAttachment
from .services import convert_to_purchase_invoice, queue_extraction

from django.http import FileResponse
from django.views.decorators.clickjacking import xframe_options_exempt

from django.http import FileResponse, HttpResponse, StreamingHttpResponse
import os
import logging
logger = logging.getLogger(__name__)

def _get_entity(request):
    try:
        return request.user.profile.entity
    except Exception:
        return None


@login_required
def inbox_list(request):
    entity = _get_entity(request)
    qs = InboxDocument.objects.all().select_related("created_by")
    if entity is not None:
        qs = qs.filter(entity=entity)

    qs = qs.prefetch_related("attachments").order_by("-created_at")[:500]
    docs = list(qs)

    selected = None
    selected_id = request.GET.get("selected")
    if selected_id:
        selected = next((d for d in docs if str(d.id) == str(selected_id)), None)
    if not selected and docs:
        selected = docs[0]

    create_form = InboxDocumentForm()

    return render(request, "inbox/inbox_list.html", {
        "docs": docs,
        "selected": selected,
        "create_form": create_form,
    })



@login_required
def inbox_create(request):
    if request.method != "POST":
        return redirect("inbox:list")

    entity = _get_entity(request)

    # IMPORTANT: include request.FILES
    form = InboxDocumentForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Could not create document")
        return redirect("inbox:list")

    files = request.FILES.getlist("file")

    doc: InboxDocument = form.save(commit=False)
    if entity is not None:
        doc.entity = entity
    doc.created_by = request.user

    # Default title from filename (only if empty)
    if not (doc.title or "").strip() and files:
        filename = files[0].name or ""
        doc.title = os.path.splitext(filename)[0]

    doc.save()
    form.save_m2m()

    # Create attachments
    if files:
        doc.attachments.update(is_primary=False)
        for i, f in enumerate(files):
            InboxAttachment.objects.create(
                document=doc,
                file=f,
                original_name=getattr(f, "name", "") or "",
                content_type=getattr(f, "content_type", "") or "",
                is_primary=(i == 0),
            )

    messages.success(request, f"Inbox row created (#{doc.id})")
    return redirect(f"{redirect('inbox:list').url}?selected={doc.id}")


@login_required
def inbox_edit(request, pk: int):
    entity = _get_entity(request)
    doc = get_object_or_404(InboxDocument, pk=pk, **({"entity": entity} if entity is not None else {}))

    if request.method != "POST":
        return redirect(f"{redirect('inbox:list').url}?selected={doc.id}")

    form = InboxDocumentForm(request.POST, instance=doc)
    if form.is_valid():
        doc = form.save()
        if doc.status == InboxDocument.Status.NEW:
            doc.status = InboxDocument.Status.IN_REVIEW
            doc.save(update_fields=["status"])
        messages.success(request, "Saved")
    else:
        messages.error(request, "Fix errors (some fields were invalid)")

    return redirect(f"{redirect('inbox:list').url}?selected={doc.id}")


@login_required
@require_POST
def inbox_delete(request, pk: int):
    entity = _get_entity(request)
    doc = get_object_or_404(InboxDocument, pk=pk, **({"entity": entity} if entity is not None else {}))
    doc.delete()
    messages.success(request, "Deleted")
    return redirect("inbox:list")


@login_required
@require_POST
def convert_purchase_invoice(request, pk: int):
    entity = _get_entity(request)
    doc = get_object_or_404(InboxDocument, pk=pk, **({"entity": entity} if entity is not None else {}))
    invoice_id = convert_to_purchase_invoice(doc, request.user)
    messages.success(request, f"Converted to Purchase Invoice (id={invoice_id})")
    return redirect(f"{redirect('inbox:list').url}?selected={doc.id}")


@login_required
@require_POST
def extract_document(request, pk: int):
    entity = _get_entity(request)
    doc = get_object_or_404(InboxDocument, pk=pk, **({"entity": entity} if entity is not None else {}))
    job = queue_extraction(doc, provider="external")
    messages.success(request, f"Extraction queued (job #{job.id})")
    return redirect(f"{redirect('inbox:list').url}?selected={doc.id}")


@login_required
def attachment_popout(request, attachment_id: int):
    entity = _get_entity(request)
    att = get_object_or_404(
        InboxAttachment,
        pk=attachment_id,
        **({"document__entity": entity} if entity is not None else {}),
    )
    return render(request, "inbox/popout.html", {"att": att})

@login_required
@xframe_options_exempt
def attachment_view(request, attachment_id: int):
    entity = _get_entity(request)
    att = get_object_or_404(
        InboxAttachment,
        pk=attachment_id,
        **({"document__entity": entity} if entity is not None else {}),
    )

    f = att.file.open("rb")
    resp = FileResponse(f, content_type=att.content_type or "application/octet-stream")

    # Encourage inline viewing (important for PDFs)
    filename = att.original_name or os.path.basename(att.file.name)
    resp["Content-Disposition"] = f'inline; filename="{filename}"'
    return resp


@login_required
@xframe_options_exempt
def attachment_view(request, attachment_id: int):
    entity = _get_entity(request)
    att = get_object_or_404(
        InboxAttachment,
        pk=attachment_id,
        **({"document__entity": entity} if entity is not None else {}),
    )

    # Guess content type if it wasn't stored
    filename = att.original_name or os.path.basename(att.file.name)
    content_type = (att.content_type or "").strip()
    if not content_type:
        guessed, _ = mimetypes.guess_type(filename)
        content_type = guessed or "application/octet-stream"

    file_size = att.file.size
    range_header = request.META.get("HTTP_RANGE")

    def _base_headers(resp: HttpResponse):
        resp["Accept-Ranges"] = "bytes"
        resp["Content-Disposition"] = f'inline; filename="{filename}"'
        resp["X-Content-Type-Options"] = "nosniff"
        return resp

    # Simple single-range support (enough for browser PDF viewers)
    start = end = None
    path = getattr(att.file, "path", None)
    if range_header and path and range_header.startswith("bytes="):
        try:
            byte_range = range_header.split("=", 1)[1].strip()
            start_s, end_s = byte_range.split("-", 1)
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else (file_size - 1)
            if start < 0 or end < start or end >= file_size:
                raise ValueError("invalid range")
        except Exception:
            range_header = None
            start = end = None

    if range_header and path and start is not None and end is not None:
        length = end - start + 1

        def file_iterator(fp, chunk_size=8192):
            fp.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fp.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

        fp = att.file.open("rb")
        resp = StreamingHttpResponse(file_iterator(fp), status=206, content_type=content_type)
        resp["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        resp["Content-Length"] = str(length)
        return _base_headers(resp)

    # Full response
    f = att.file.open("rb")
    resp = FileResponse(f, content_type=content_type)
    resp["Content-Length"] = str(file_size)
    return _base_headers(resp)