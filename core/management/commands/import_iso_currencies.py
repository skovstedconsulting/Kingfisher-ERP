import json
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import IsoCurrencyCodes
from pathlib import Path
from django.conf import settings

class Command(BaseCommand):
    help = "Import ISO currencies from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=Path(settings.BASE_DIR) / "external_files" / "iso_currencies.json",
            help="Path to iso_currencies.json",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = options["path"]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)  # dict keyed by currency code

        created = 0
        updated = 0

        for code, row in data.items():
            if not code:
                continue

            defaults = {
                "name": row.get("name", "") or "",
                "demonym": row.get("demonym", "") or "",
                "iso_num": row.get("ISOnum", None),
                "iso_digits": row.get("ISOdigits", None),
                "symbol": row.get("symbol", "") or "",
                "symbol_native": row.get("symbolNative", "") or "",
                "major_single": row.get("majorSingle", "") or "",
                "major_plural": row.get("majorPlural", "") or "",
                "minor_single": row.get("minorSingle", "") or "",
                "minor_plural": row.get("minorPlural", "") or "",
                "decimals": row.get("decimals", None),
                "num_to_basic": row.get("numToBasic", None),
            }

            obj, was_created = IsoCurrencyCodes.objects.update_or_create(code=code, defaults=defaults)
            created += 1 if was_created else 0
            updated += 0 if was_created else 1

        self.stdout.write(self.style.SUCCESS(f"Imported currencies: created={created}, updated={updated}"))
