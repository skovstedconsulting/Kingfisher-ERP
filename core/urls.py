from django.urls import path
from core.views.profile import profile_edit
from core.views.menu import menu_edit, menu_delete

app_name = "core"

urlpatterns = [
    path("profile/", profile_edit, name="profile"),
    path("menus/", menu_edit, name="menu-edit"),
    path("menus/<int:pk>/", menu_edit, name="menu-edit"),
    path("menus/<int:pk>/delete/", menu_delete, name="menu-delete"),
]