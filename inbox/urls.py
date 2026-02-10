from django.urls import path
from . import views

app_name = "inbox"

urlpatterns = [
    path("inbox", views.inbox_list, name="list"),
    path("inbox/create/", views.inbox_create, name="create"),
    path("inbox/<int:pk>/edit/", views.inbox_edit, name="edit"),
    path("inbox/<int:pk>/delete/", views.inbox_delete, name="delete"),
    path("inbox/<int:pk>/convert/purchase-invoice/", views.convert_purchase_invoice, name="convert-purchase-invoice"),
    path("<int:pk>/extract/", views.extract_document, name="extract"),
    path("inbox/attachment/<int:attachment_id>/popout/", views.attachment_popout, name="attachment-popout"),
    path("inbox/attachment/<int:attachment_id>/view/", views.attachment_view, name="attachment-view"),
]
