from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static

CORE_APP_LABEL = "core"
AUTH_APP_LABEL = "auth"


def admin_changelist(app_label: str, model: str):
    """
    model must be the lowercase model name used by Django admin url patterns.
    Examples:
      admin:core_account_changelist
      admin:auth_user_changelist
      admin:auth_group_changelist
    """
    return reverse_lazy(f"admin:{app_label}_{model}_changelist")


UNFOLD = {
    "SITE_HEADER": "Kingfisher ERP",
    "SITE_TITLE": "Kingfisher ERP",
    "SITE_URL": "/",
 
    # Small brand mark in sidebar / header (aim for ~32px height)
    "SITE_ICON": {
        "light": lambda request: static("core/brand/kingfisher.png"),
        "dark":  lambda request: static("core/brand/kingfisher.png"),
    },

    # Optional bigger logo (also ~32px height works best)
    "SITE_LOGO": {
        "light": lambda request: static("core/brand/kingfisher.png"),
        "dark":  lambda request: static("core/brand/kingfisher.png"),
    },

    # Browser tab favicon(s)
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/png",
            "href": lambda request: static("core/brand/kingfisher.png"),
        },
    ],
 
 
 
 
 
 
 
 
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Company & Setup"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": _("Entities"), "icon": "apartment", "link": admin_changelist(CORE_APP_LABEL, "entity")},
                    {"title": _("Fiscal years"), "icon": "event", "link": admin_changelist(CORE_APP_LABEL, "fiscalyear")},
                    {"title": _("Addresses"), "icon": "home_pin", "link": admin_changelist(CORE_APP_LABEL, "address")},
                    {"title": _("Payment terms"), "icon": "schedule", "link": admin_changelist(CORE_APP_LABEL, "paymentterms")},
                ],
            },
            {
                "title": _("Finance"),
                "collapsible": True,
                "items": [
                    {"title": _("Accounts"), "icon": "account_balance", "link": admin_changelist(CORE_APP_LABEL, "account")},
                    {"title": _("Journals"), "icon": "receipt_long", "link": admin_changelist(CORE_APP_LABEL, "journal")},
                ],
            },
            {
                "title": _("VAT"),
                "collapsible": True,
                "items": [
                    {"title": _("VAT groups"), "icon": "folder", "link": admin_changelist(CORE_APP_LABEL, "vatgroup")},
                    {"title": _("VAT codes"), "icon": "percent", "link": admin_changelist(CORE_APP_LABEL, "vatcode")},
                ],
            },
            {
                "title": _("Sales (AR)"),
                "collapsible": True,
                "items": [
                    {"title": _("Debtor groups"), "icon": "groups", "link": admin_changelist(CORE_APP_LABEL, "debtorgroup")},
                    {"title": _("Debtors"), "icon": "person", "link": admin_changelist(CORE_APP_LABEL, "debtor")},
                ],
            },
            {
                "title": _("Items"),
                "collapsible": True,
                "items": [
                    {"title": _("Item groups"), "icon": "category", "link": admin_changelist(CORE_APP_LABEL, "itemgroup")},
                    {"title": _("Items"), "icon": "inventory_2", "link": admin_changelist(CORE_APP_LABEL, "item")},
                ],
            },
            {
                "title": _("Chart of Accounts"),
                "collapsible": True,
                "items": [
                    {"title": _("COA templates"), "icon": "account_tree", "link": admin_changelist(CORE_APP_LABEL, "chartofaccountstemplate")},
                ],
            },
            {
                "title": _("Reference data"),
                "collapsible": True,
                "items": [
                    {"title": _("ISO countries"), "icon": "public", "link": admin_changelist(CORE_APP_LABEL, "isocountrycodes")},
                    {"title": _("ISO currencies"), "icon": "currency_exchange", "link": admin_changelist(CORE_APP_LABEL, "isocurrencycodes")},
                ],
            },
            {
                "title": _("Users & Permissions"),
                "collapsible": True,
                "items": [
                    {"title": _("Users"), "icon": "manage_accounts", "link": admin_changelist(AUTH_APP_LABEL, "user")},
                    {"title": _("Groups"), "icon": "admin_panel_settings", "link": admin_changelist(AUTH_APP_LABEL, "group")},
                ],
            },
        ],
    },
}
