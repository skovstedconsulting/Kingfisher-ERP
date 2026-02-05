from django.urls import path
from masterdata import views

app_name = "masterdata"

urlpatterns = [
    # Items
    path("items/", views.item_list, name="item-list"),
    path("items/<int:pk>/delete/", views.item_delete, name="item-delete"),
    path("", views.dashboard, name="dashboard"),

    # Add these when you have the views (or create stubs)
    #path("items/", views.item_list, name="item-list"),
    #path("items/<int:pk>/", views.item_detail, name="item-detail"),
    #path("items/<int:pk>/edit/", views.item_update, name="item-update"),

    # Groups (optional)
    #path("groups/", views.itemgroup_list, name="itemgroup-list"),
    #path("groups/<int:pk>/", views.itemgroup_detail, name="itemgroup-detail"),
]