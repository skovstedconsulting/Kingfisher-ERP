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
                    {"title": _("VAT groups"), "icon": "folder", "link": admin_changelist(CORE_APP_LABEL, "vatgroup")},
                    {"title": _("VAT codes"), "icon": "percent", "link": admin_changelist(CORE_APP_LABEL, "vatcode")},
                    {"title": _("ISO countries"), "icon": "public", "link": admin_changelist(CORE_APP_LABEL, "isocountrycodes")},
                    {"title": _("ISO currencies"), "icon": "currency_exchange", "link": admin_changelist(CORE_APP_LABEL, "isocurrencycodes")},
                    {"title": _("COA templates"), "icon": "account_tree", "link": admin_changelist(CORE_APP_LABEL, "chartofaccountstemplate")},        
                    {"title": _("Document statuses"), "icon": "tune", "link": admin_changelist(CORE_APP_LABEL, "documentstatus")},
                    {"title": _("Number series"), "icon": "format_list_numbered", "link": admin_changelist(CORE_APP_LABEL, "numberseries")},
                ],
            },
            {
                "title": _("Finance"),
                "collapsible": True,
                "items": [
                    {"title": _("Accounts"), "icon": "account_balance", "link": admin_changelist(CORE_APP_LABEL, "account")},
                    {"title": _("Journals"), "icon": "receipt_long", "link": admin_changelist(CORE_APP_LABEL, "journal")},
                    {"title": _("Journal lines"), "icon": "post_add", "link": admin_changelist(CORE_APP_LABEL, "journalline")},
                ],
            },
            {
                "title": _("Purchases (AP)"),
                "collapsible": True,
                "items": [                    
                    {"title": _("Purchase orders"), "icon": "inventory", "link": admin_changelist(CORE_APP_LABEL, "purchaseorder")},
                    {"title": _("Purchase invoices"), "icon": "description", "link": admin_changelist(CORE_APP_LABEL, "purchaseinvoice")},
                    {"title": _("Purchase credit notes"), "icon": "undo", "link": admin_changelist(CORE_APP_LABEL, "purchasecreditnote")},
                    
                ],
            },
            {
                "title": _("Sales (AR)"),
                "collapsible": True,
                "items": [

                    {"title": _("Debtors"), "icon": "person", "link": admin_changelist(CORE_APP_LABEL, "debtor")},
                    {"title": _("Sales offers"), "icon": "request_quote", "link": admin_changelist(CORE_APP_LABEL, "salesoffer")},
                    {"title": _("Sales orders"), "icon": "shopping_cart", "link": admin_changelist(CORE_APP_LABEL, "salesorder")},
                    {"title": _("Sales invoices"), "icon": "receipt", "link": admin_changelist(CORE_APP_LABEL, "salesinvoice")},
                    {"title": _("Sales credit notes"), "icon": "assignment_return", "link": admin_changelist(CORE_APP_LABEL, "salescreditnote")},
                    {"title": _("Debtor groups"), "icon": "groups", "link": admin_changelist(CORE_APP_LABEL, "debtorgroup")},
                ],
            },
            {
                "title": _("Items"),
                "collapsible": True,
                "items": [
                    {"title": _("Items"), "icon": "inventory_2", "link": admin_changelist(CORE_APP_LABEL, "item")},
                    {"title": _("Item groups"), "icon": "category", "link": admin_changelist(CORE_APP_LABEL, "itemgroup")},
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
