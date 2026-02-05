from django.urls import path

from masterdata.views.debitor import debtor_list, debtor_delete, debtor_detail
from masterdata.views.dashboard import dashboard
from masterdata.views.items import item_delete, item_detail, item_list

app_name = "masterdata"

urlpatterns = [
    # Items
    path("items/", item_list, name="item-list"),
    path("items/<int:pk>/delete/", item_delete, name="item-delete"),
    path("", dashboard, name="dashboard"),

    path("debtors/", debtor_list, name="debtor-list"),
    path("debtors/<int:pk>/", debtor_detail, name="debtor-detail"),
    path("debtors/<int:pk>/delete/", debtor_delete, name="debtor-delete"),

    # Add these when you have the views (or create stubs)
    #path("items/", views.item_list, name="item-list"),
    #path("items/<int:pk>/", views.item_detail, name="item-detail"),
    #path("items/<int:pk>/edit/", views.item_update, name="item-update"),

    # Groups (optional)
    #path("groups/", views.itemgroup_list, name="itemgroup-list"),
    #path("groups/<int:pk>/", views.itemgroup_detail, name="itemgroup-detail"),
]