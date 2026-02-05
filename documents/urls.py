from django.urls import path

from documents.views.sales import (
    sales_document_create,
    sales_document_edit,
    sales_document_action,
    sales_document_delete,
)

app_name = "documents"

urlpatterns = [
    path("sales/new/", sales_document_create, name="sales_document_create"),
    path("sales/<int:pk>/", sales_document_edit, name="sales_document_edit"),
    path("sales/<int:pk>/action/", sales_document_action, name="sales_document_action"),
    path("sales/<int:pk>/delete/", sales_document_delete, name="sales_document_delete"),
]