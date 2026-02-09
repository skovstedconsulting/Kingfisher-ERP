from django.urls import path
from . import views

app_name = "bankrec"

urlpatterns = [
    path("sessions/", views.session_list, name="session-list"),
    path("reconcile/<int:session_id>/", views.reconcile_view, name="reconcile"),
    path("reconcile/<int:session_id>/match/", views.match_create, name="match-create"),
    path("reconcile/<int:session_id>/unmatch/", views.match_delete, name="match-delete"),
]
