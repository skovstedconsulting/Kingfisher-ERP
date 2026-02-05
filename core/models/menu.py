from django.db import models

class Menu(models.Model):
    menu = models.CharField(max_length=255)

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    # ✅ order within the same parent (top-level uses parent=NULL)
    sort_order = models.PositiveIntegerField(default=0)

    url = models.CharField(max_length=500, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["parent_id", "sort_order", "menu"]

    def __str__(self):
        return self.menu
