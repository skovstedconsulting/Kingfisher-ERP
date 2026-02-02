from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from core.admin_utils import EntityScopedAdminMixin
from inventory.models import InventoryLayer, StockMove

@admin.register(InventoryLayer)
class InventoryLayerAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "item", "qty_remaining", "unit_cost_base", "created_at")
    list_filter = ("entity", "item")

@admin.register(StockMove)
class StockMoveAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "date", "item", "qty", "unit_cost_base")
    list_filter = ("entity", "item")
