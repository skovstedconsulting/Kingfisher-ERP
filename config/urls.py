from django.contrib import admin
from django.urls import path

# Ensure all app admin modules (core.admin, documents.admin, etc.) are imported.
admin.autodiscover()

urlpatterns = [
    path("admin/", admin.site.urls),
]
