from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django_fsm import can_proceed

from documents.forms.sales_forms import SalesDocumentForm, SalesLineFormSet
from documents.forms.sales_filters import SalesDocumentFilterForm
from documents.models import SalesDocument
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction

from masterdata.models import Debtor

def _get_docs_for_list(request, entity):
    filter_form = SalesDocumentFilterForm(request.GET or None, entity=entity)
    qs = (
        SalesDocument.objects
        .filter(entity=entity)
        .select_related("debtor", "currency")
        .order_by("-date", "-id")
    )

    if filter_form.is_valid():
        state = filter_form.cleaned_data.get("state")
        debtor = filter_form.cleaned_data.get("debtor")
        if state:
            qs = qs.filter(state=state)
        if debtor:
            qs = qs.filter(debtor=debtor)

    return filter_form, qs[:200]

@login_required
def sales_document_create(request):
    entity = request.user.profile.entity
    filter_form, docs = _get_docs_for_list(request, entity)

    if request.method == "POST":
        form = SalesDocumentForm(request.POST, entity=entity)

        if form.is_valid():
            doc = form.save(commit=False)
            doc.entity = entity

            try:
                with transaction.atomic():
                    # 1) save doc (so it has PK)
                    doc.save()

                    # 2) save lines
                    formset = SalesLineFormSet(
                        request.POST,
                        instance=doc,
                        form_kwargs={"entity": entity},
                    )
                    if not formset.is_valid():
                        raise ValueError("Line validation failed")
                    formset.save()

                    # 3) totals
                    doc.recalc_totals()

                    # 4) AUTO-CONVERT: offer -> order -> invoice
                    if can_proceed(doc.convert_to_order):
                        doc.convert_to_order(by_user=request.user)
                        doc.save()

                    if can_proceed(doc.convert_to_invoice):
                        doc.convert_to_invoice(by_user=request.user)
                        doc.save()

                messages.success(request, f"Saved and converted to invoice ({doc.display_no}).")
                return redirect("documents:sales_document_edit", pk=doc.pk)

            except Exception as e:
                messages.error(request, f"Save failed: {e}")
                # fall through to render with errors below
                formset = SalesLineFormSet(request.POST, form_kwargs={"entity": entity})

        else:
            formset = SalesLineFormSet(request.POST, form_kwargs={"entity": entity})

    
    
    else:
        initial = {}
        debtor_id = request.GET.get("debtor_id")
        if debtor_id:
            try:
                debtor = Debtor.objects.get(pk=debtor_id, entity=entity)
                initial["debtor"] = debtor.pk   # pk is fine for ModelChoiceField
            except Debtor.DoesNotExist:
                pass

        form = SalesDocumentForm(entity=entity, initial=initial)
        formset = SalesLineFormSet(form_kwargs={"entity": entity})

    return render(request, "documents/salesdocument_form.html", {
        "form": form,
        "formset": formset,
        "docs": docs,
        "filter_form": filter_form,
        "is_edit": False,
        "doc": None,
    })


@login_required
def sales_document_edit(request, pk):
    entity = request.user.profile.entity
    filter_form, docs = _get_docs_for_list(request, entity)

    doc = get_object_or_404(SalesDocument, pk=pk, entity=entity)

    if request.method == "POST":
        form = SalesDocumentForm(request.POST, instance=doc, entity=entity)
        formset = SalesLineFormSet(request.POST, instance=doc, form_kwargs={"entity": entity})

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    formset.save()
                    doc.recalc_totals()

                messages.success(request, "Updated.")
                return redirect("documents:sales_document_edit", pk=doc.pk)
            except Exception as e:
                messages.error(request, f"Update failed: {e}")
    else:
        form = SalesDocumentForm(instance=doc, entity=entity)
        formset = SalesLineFormSet(instance=doc, form_kwargs={"entity": entity})

    return render(request, "documents/salesdocument_form.html", {
        "form": form,
        "formset": formset,
        "docs": docs,
        "filter_form": filter_form,
        "is_edit": True,
        "doc": doc,
    })

@login_required
@require_POST
def sales_document_delete(request, pk):
    entity = request.user.profile.entity
    doc = get_object_or_404(SalesDocument, pk=pk, entity=entity)

    try:
        # (optional) protect posted docs
        if doc.state in ("posted", "paid", "partly_paid", "credited"):
            raise ValueError("Cannot delete a posted/paid/credited document.")

        doc.delete()
        messages.success(request, "Document deleted.")
    except Exception as e:
        messages.error(request, f"Delete failed: {e}")

    return redirect("documents:sales_document_create")


@login_required
@require_POST
def sales_document_action(request, pk):
    entity = request.user.profile.entity
    doc = get_object_or_404(SalesDocument, pk=pk, entity=entity)

    action = request.POST.get("action", "")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

    try:
        if action == "convert_to_order":
            if not can_proceed(doc.convert_to_order):
                raise ValueError("Not allowed from current state.")
            doc.convert_to_order(by_user=request.user)
            doc.save()

        elif action == "convert_to_invoice":
            if not can_proceed(doc.convert_to_invoice):
                raise ValueError("Not allowed from current state.")
            doc.convert_to_invoice(by_user=request.user)
            doc.save()

        elif action == "post":
            if not can_proceed(doc.post):
                raise ValueError("Not allowed from current state.")
            doc.post(by_user=request.user)
            doc.save()

        else:
            raise ValueError("Unknown action.")

        messages.success(request, "Action completed.")

    except Exception as e:
        messages.error(request, f"Action failed: {e}")

    return redirect(next_url)
