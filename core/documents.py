from .models import Document

class SalesOffer(Document):
    class Meta:
        proxy = True
        verbose_name = "Sales offer"
        verbose_name_plural = "Sales offers"


class SalesOrder(Document):
    class Meta:
        proxy = True
        verbose_name = "Sales order"
        verbose_name_plural = "Sales orders"


class SalesInvoice(Document):
    class Meta:
        proxy = True
        verbose_name = "Sales invoice"
        verbose_name_plural = "Sales invoices"


class SalesCreditNote(Document):
    class Meta:
        proxy = True
        verbose_name = "Sales credit note"
        verbose_name_plural = "Sales credit notes"


class PurchaseOrder(Document):
    class Meta:
        proxy = True
        verbose_name = "Purchase order"
        verbose_name_plural = "Purchase orders"


class PurchaseInvoice(Document):
    class Meta:
        proxy = True
        verbose_name = "Purchase invoice"
        verbose_name_plural = "Purchase invoices"


class PurchaseCreditNote(Document):
    class Meta:
        proxy = True
        verbose_name = "Purchase credit note"
        verbose_name_plural = "Purchase credit notes"
