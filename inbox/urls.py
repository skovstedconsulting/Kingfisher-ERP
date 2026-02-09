from django.urls import path
from . import views

app_name = "inbox"

urlpatterns = [
    path("", views.inbox_list, name="list"),
    path("create/", views.inbox_create, name="create"),
    path("<int:pk>/edit/", views.inbox_edit, name="edit"),
    path("<int:pk>/delete/", views.inbox_delete, name="delete"),
    path("<int:pk>/convert/purchase-invoice/", views.convert_purchase_invoice, name="convert-purchase-invoice"),
    path("<int:pk>/extract/", views.extract_document, name="extract"),
    path("attachment/<int:attachment_id>/popout/", views.attachment_popout, name="attachment-popout"),
    path("attachment/<int:attachment_id>/view/", views.attachment_view, name="attachment-view"),
]
