from django.urls import path
from . import api_views

urlpatterns = [
    path("documents/", api_views.api_list_documents, name="api-list-documents"),
    path("documents/create/", api_views.api_create_document, name="api-create-document"),
    path("documents/<int:pk>/attach/", api_views.api_attach_file, name="api-attach-file"),
]
