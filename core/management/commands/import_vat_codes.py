import json
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Entity
from models import VatGroup, VatCode


def parse_percent(value):
    if not value:
        return None
    value = value.replace("%", "").replace(",", ".").strip()
    if value.lower() == "x":
        return None
    return Decimal(value) / Decimal("100")


class Command(BaseCommand):
    help = "Import Danish VAT codes from official moms-koder JSON"

    def add_arguments(self, parser):
        parser.add_argument("entity_id", type=int)
        parser.add_argument("file", type=str)

    @transaction.atomic
    def handle(self, entity_id, file, *args, **options):
        entity = Entity.objects.get(pk=entity_id)

        with open(file, encoding="utf-8") as f:
            data = json.load(f)

        groups = data["momskoder - bruttoliste"]

        for group_data in groups:
            group_name = group_data["momsgruppe"]
            group_code = group_name.lower().replace(" ", "_")

            vat_group, _ = VatGroup.objects.get_or_create(
                entity=entity,
                code=group_code,
                defaults={"name": group_name},
            )

            for row in group_data["momskoder"]:
                vat_type = (
                    VatCode.VatType.SALE
                    if row["type"].strip().lower().startswith("salg")
                    else VatCode.VatType.PURCHASE
                )

                VatCode.objects.update_or_create(
                    entity=entity,
                    code=row.get("momskode NY") or row.get("momskode"),
                    defaults={
                        "group": vat_group,
                        "legacy_code": row.get("momskode", ""),
                        "name": row.get("overskrift", ""),
                        "description": row.get("vejledning", ""),
                        "vat_type": vat_type,
                        "rate": parse_percent(row.get("momssats")),
                        "deduction_rate": parse_percent(row.get("fradragsret")),
                        "deduction_method": row.get("fradragsret", "") if not row.get("fradragsret", "").endswith("%") else "",
                        "reporting_text": row.get("momsangivelse", ""),
                        "dk_only": row.get("1. Udelukkende handel i DK") == "x",
                        "dk_mixed": row.get("2. Udelukkende handel i DK + blandede aktiviteter") == "x",
                        "international": row.get("3. Også handel med udlandet") == "x",
                        "international_mixed": row.get("4. Også handel med udlandet + blandedeaktiviteter") == "x",
                        "special_scheme": row.get("5. Særkoder") == "x",
                    },
                )

        self.stdout.write(self.style.SUCCESS("VAT codes imported successfully"))
