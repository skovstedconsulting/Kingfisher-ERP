from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from core.admin_utils import EntityScopedAdminMixin
from masterdata.models import Debtor, DebtorGroup, Creditor, CreditorGroup, Item, ItemGroup

@admin.register(DebtorGroup)
class DebtorGroupAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "code", "name", "payment_terms_days")
    list_filter = ("entity",)
    search_fields = ("code", "name")

@admin.register(Debtor)
class DebtorAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "number", "name", "vat_area", "group")
    list_filter = ("entity", "vat_area", "group")
    search_fields = ("number", "name")

@admin.register(CreditorGroup)
class CreditorGroupAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "code", "name")
    list_filter = ("entity",)
    search_fields = ("code", "name")

@admin.register(Creditor)
class CreditorAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "number", "name", "group")
    list_filter = ("entity", "group")
    search_fields = ("number", "name")

@admin.register(ItemGroup)
class ItemGroupAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "code", "name")
    list_filter = ("entity",)
    search_fields = ("code", "name")

@admin.register(Item)
class ItemAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "number", "name", "group", "is_stock_item")
    list_filter = ("entity", "group", "is_stock_item")
    search_fields = ("number", "name")
