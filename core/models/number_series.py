from django.db import models, transaction

class NumberSeries(models.Model):
    """Simple, readable number series.

    The important part is *concurrency safety*:
    - We lock the NumberSeries row in the database (select_for_update)
    - We read next_number
    - We increment next_number and save
    - We return a formatted string (prefix + zero-padded number)

    This guarantees that two users posting at the same time do not get the same number.
    """

    entity = models.ForeignKey("core.Entity", on_delete=models.CASCADE, related_name="number_series")

    code = models.CharField(max_length=50)
    prefix = models.CharField(max_length=50, blank=True, default="")
    next_number = models.IntegerField(default=1)
    min_width = models.IntegerField(default=1)

    class Meta:
        unique_together = ("entity", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.entity} {self.code}"

    @transaction.atomic
    def allocate(self) -> str:
        """Allocate the next number without duplicates.

        Step-by-step:
        1) Start a DB transaction (atomic)
        2) Lock *this* NumberSeries row with select_for_update
        3) Read current next_number
        4) Increment next_number and save
        5) Return formatted string

        The lock is held until the transaction commits, so no other allocation can read
        the old next_number in parallel.
        """
        series = type(self).objects.select_for_update().get(pk=self.pk)

        current = series.next_number
        series.next_number = current + 1
        series.save(update_fields=["next_number"])

        return f"{series.prefix}{str(current).zfill(series.min_width)}"
