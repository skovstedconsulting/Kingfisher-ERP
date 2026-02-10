from django.urls import path
from . import views

app_name = "ledger"

urlpatterns = [
    path("journals/", views.journal_list, name="journal-list"),

    path("journals/<int:pk>/", views.journal_detail, name="journal-detail"),
    path("journals/<int:pk>/edit/", views.journal_edit, name="journal-edit"),
    path("journals/post-day/", views.journal_post_all_drafts_for_day, name="journal-post-day"),

    path("journals/new/", views.journal_create, name="journal-create"),
]