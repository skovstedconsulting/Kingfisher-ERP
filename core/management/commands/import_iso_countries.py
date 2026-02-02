import json
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import IsoCountryCodes


class Command(BaseCommand):
    help = "Import ISO 3166 countries from external_files/iso_countries.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="external_files/iso_countries.json",
            help="Path to iso_countries.json",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        created = 0
        updated = 0

        for row in data:
            code = (row.get("alpha-2") or "").strip().upper()
            if not code:
                continue

            defaults = {
                "name": (row.get("name") or "").strip(),
                "alpha_3": (row.get("alpha-3") or "").strip().upper(),
                "numeric_code": (row.get("country-code") or "").strip(),
                "iso_3166_2": (row.get("iso_3166-2") or "").strip(),
                "region": (row.get("region") or "").strip(),
                "sub_region": (row.get("sub-region") or "").strip(),
                "intermediate_region": (row.get("intermediate-region") or "").strip(),
                "region_code": (row.get("region-code") or "").strip(),
                "sub_region_code": (row.get("sub-region-code") or "").strip(),
                "intermediate_region_code": (row.get("intermediate-region-code") or "").strip(),
            }

            obj, was_created = IsoCountryCodes.objects.update_or_create(
                code=code,
                defaults=defaults,
            )
            created += int(was_created)
            updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(f"ISO countries: created={created}, updated={updated}"))
