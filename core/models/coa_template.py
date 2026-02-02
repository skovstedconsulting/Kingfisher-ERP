from django.db import models
from django.utils.translation import gettext_lazy as _


class ChartOfAccountsTemplate(models.Model):
    """Metadata container for imported Standardkontoplan documents.

    Matches the top-level fields in the file (Document name, valid-from date,
    csv source file).

    This model is **not** tied to Entity so you can keep a library of templates.
    """

    name = models.CharField(max_length=255)
    valid_from = models.DateField(null=True, blank=True)
    source_file = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = _("Chart of Accounts Template")
        verbose_name_plural = _("Chart of Accounts Templates")
        ordering = ["-valid_from", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.valid_from or 'n/a'})"


class ChartOfAccountsNode(models.Model):
    """Tree structure for Standardkontoplan.

    Represents header/group/account nodes in the imported template.
    We do not use django-mptt here because this tree is typically static and
    used only for importing.
    """

    class NodeType(models.TextChoices):
        HEADER = "HEADER", _("Header")
        GROUP = "GROUP", _("Group")
        ACCOUNT = "ACCOUNT", _("Account")

    template = models.ForeignKey(
        ChartOfAccountsTemplate, on_delete=models.CASCADE, related_name="nodes"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    node_type = models.CharField(max_length=20, choices=NodeType.choices)
    number = models.IntegerField()
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ("template", "number")
        ordering = ["number"]

    def __str__(self) -> str:
        return f"{self.number} – {self.name}"
