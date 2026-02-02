from __future__ import annotations

from decimal import Decimal
from xml.etree import ElementTree as ET

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from core.models import ExchangeRate


ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


class Command(BaseCommand):
    help = "Fetch daily ECB FX rates and store them as global ExchangeRate rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            default=ECB_DAILY_URL,
            help="ECB XML endpoint (defaults to daily rates).",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=20,
            help="HTTP timeout in seconds.",
        )
        parser.add_argument(
            "--base",
            default="EUR",
            help="Base currency (ECB is EUR).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate ECB XML without writing to DB.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        url: str = opts["url"]
        timeout: int = opts["timeout"]
        base: str = opts["base"].upper()
        dry_run: bool = bool(opts["dry_run"])

        self.stdout.write(f"Fetching ECB rates from {url}")

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        # Find <Cube time="YYYY-MM-DD">
        time_cube = None
        for el in root.iter():
            if el.tag.endswith("Cube") and "time" in el.attrib:
                time_cube = el
                break

        if time_cube is None:
            raise RuntimeError("ECB XML: could not find daily <Cube time='...'> node")

        rate_date = time_cube.attrib["time"]

        created = 0
        updated = 0

        for el in time_cube:
            if not el.tag.endswith("Cube"):
                continue

            quote = el.attrib.get("currency")
            rate_raw = el.attrib.get("rate")

            if not quote or not rate_raw:
                continue

            rate = Decimal(rate_raw)

            if dry_run:
                self.stdout.write(f"[DRY] {rate_date} 1 {base} = {rate} {quote}")
                continue

            obj, was_created = ExchangeRate.objects.update_or_create(
                entity=None,                 # GLOBAL rate
                date=rate_date,
                base=base,
                quote=quote,
                source=ExchangeRate.SOURCE_ECB,
                defaults={
                    "rate": rate,
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Parsed ECB rates for {rate_date}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"ECB rates {rate_date}: created={created}, updated={updated}"
                )
            )
