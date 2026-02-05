from django.contrib import admin

from guardian.admin import GuardedModelAdmin

from core.admin_utils import EntityScopedAdminMixin
from core.models import Entity, UserProfile, NumberSeries, Account

#from django.contrib.auth import get_user_model

from core.models.iso_codes import IsoCountryCodes
from core.models.iso_codes import IsoCurrencyCodes
from core.models.vat import VatCode, VatGroup
from core.models.menu import Menu

@admin.register(Entity)
class EntityAdmin(GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("name", "base_currency", "is_active")
    search_fields = ("name",)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "entity", "is_entity_admin")
    list_filter = ("entity", "is_entity_admin")

@admin.register(NumberSeries)
class NumberSeriesAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "code", "prefix", "next_number", "min_width")
    list_filter = ("entity",)
    search_fields = ("code", "prefix")

@admin.register(Account)
class AccountAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "number", "name", "is_postable")
    list_filter = ("entity", "is_postable")
    search_fields = ("number", "name")

@admin.register(IsoCountryCodes)
class IsoCountryCodesAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")

@admin.register(IsoCurrencyCodes)
class IsoCurrencyCodesAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("code", "name")
    
    search_fields = ("code", "name")

@admin.register(VatCode)
class VatCodeAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "code", "name")
    list_filter = ("entity",)
    search_fields = ("code", "name")

@admin.register(VatGroup)
class VatGroupAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ("entity", "code", "name")
    list_filter = ("entity",)
    search_fields = ("code", "name")

@admin.register(Menu)
class MenuAdmin(EntityScopedAdminMixin, GuardedModelAdmin, admin.ModelAdmin):
    list_display = ( "menu","parent","url","active", "created_at")
