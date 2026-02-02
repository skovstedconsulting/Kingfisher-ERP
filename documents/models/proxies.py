from documents.models.sales import SalesDocument
from documents.models.purchase import PurchaseDocument

class SalesOffer(SalesDocument):
    class Meta:
        proxy = True
        verbose_name = "Sales Offer"
        verbose_name_plural = "Sales Offers"

class SalesOrder(SalesDocument):
    class Meta:
        proxy = True
        verbose_name = "Sales Order"
        verbose_name_plural = "Sales Orders"

class SalesInvoice(SalesDocument):
    class Meta:
        proxy = True
        verbose_name = "Sales Invoice"
        verbose_name_plural = "Sales Invoices"

class PurchaseOrder(PurchaseDocument):
    class Meta:
        proxy = True
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"

class PurchaseInvoice(PurchaseDocument):
    class Meta:
        proxy = True
        verbose_name = "Purchase Invoice"
        verbose_name_plural = "Purchase Invoices"
