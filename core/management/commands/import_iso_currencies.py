import json
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import IsoCurrencyCodes


class Command(BaseCommand):
    help = "Import ISO 4217 currencies from external_files/iso_currencies.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="external_files/iso_currencies.json",
            help="Path to iso_currencies.json",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)  # dict keyed by currency code

        created = 0
        updated = 0

        for code, row in data.items():
            code = (code or "").strip().upper()
            if not code:
                continue

            defaults = {
                "name": (row.get("name") or "").strip(),
                "demonym": (row.get("demonym") or "").strip(),
                "iso_num": row.get("ISOnum", None),
                "iso_digits": row.get("ISOdigits", None),
                "symbol": (row.get("symbol") or "").strip(),
                "symbol_native": (row.get("symbolNative") or "").strip(),
                "major_single": (row.get("majorSingle") or "").strip(),
                "major_plural": (row.get("majorPlural") or "").strip(),
                "minor_single": (row.get("minorSingle") or "").strip(),
                "minor_plural": (row.get("minorPlural") or "").strip(),
                "decimals": row.get("decimals", None),
                "num_to_basic": row.get("numToBasic", None),
            }

            obj, was_created = IsoCurrencyCodes.objects.update_or_create(
                code=code,
                defaults=defaults,
            )
            created += int(was_created)
            updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(f"ISO currencies: created={created}, updated={updated}"))
