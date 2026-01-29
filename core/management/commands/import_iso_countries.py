import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from config import settings
from core.models import IsoCountryCodes


class Command(BaseCommand):
    help = "Import ISO countries from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=Path(settings.BASE_DIR) / "external_files" / "iso_countries.json",

            help="Path to iso_countries.json",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = options["path"]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        created = 0
        updated = 0

        for row in data:
            code = row.get("alpha-2")
            if not code:
                continue

            defaults = {
                "name": row.get("name", "") or "",
                "alpha_3": row.get("alpha-3", "") or "",
                "numeric_code": row.get("country-code", "") or "",
                "iso_3166_2": row.get("iso_3166-2", "") or "",
                "region": row.get("region", "") or "",
                "sub_region": row.get("sub-region", "") or "",
                "intermediate_region": row.get("intermediate-region", "") or "",
                "region_code": row.get("region-code", "") or "",
                "sub_region_code": row.get("sub-region-code", "") or "",
                "intermediate_region_code": row.get("intermediate-region-code", "") or "",
            }

            obj, was_created = IsoCountryCodes.objects.update_or_create(code=code, defaults=defaults)
            created += 1 if was_created else 0
            updated += 0 if was_created else 1

        self.stdout.write(self.style.SUCCESS(f"Imported countries: created={created}, updated={updated}"))
