from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from django.conf import settings

admin.autodiscover()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("masterdata.urls")),
    path("", include("core.urls")),
    path("", include("documents.urls")),
    path("", include("ledger.urls")),
    path("", include("inventory.urls")),
    path("", include("bankrec.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
