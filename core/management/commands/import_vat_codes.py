import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Entity, VatCode, VatGroup


VAT_FILE_PATH = (
    Path(settings.BASE_DIR)
    / "external_files"
    / "2026-01-01-Momskoder-Bruttoliste.json"
)

from decimal import Decimal, InvalidOperation

def parse_percent(value):
    """
    Parses "25%" -> 0.2500, "66,6%" -> 0.6660
    Returns None for "", "x%", "x", None, or non-numeric.
    """
    if not value:
        return None

    s = str(value).strip()
    if not s:
        return None

    # common placeholders in your source
    if s.lower() in {"x", "x%", "-"}:
        return None

    if "%" not in s:
        return None

    s = s.replace("%", "").replace(",", ".").strip()

    # after cleanup, still might not be numeric
    try:
        return Decimal(s) / Decimal("100")
    except (InvalidOperation, ValueError):
        return None


def parse_deduction(value):
    """
    Returns (deduction_rate, deduction_method)
    - "100%" -> (1.0, "")
    - "Skøn" -> (None, "Skøn")
    - "Delvis" -> (None, "Delvis")
    - "Maks 25% ..." -> (None, "Maks 25% ...")
    """
    if not value:
        return (None, "")

    s = str(value).strip()
    if not s:
        return (None, "")

    rate = parse_percent(s)
    if rate is not None:
        return (rate, "")

    # not a numeric percent -> treat as method/descriptor
    return (None, s)

class Command(BaseCommand):
    help = "Import Danish VAT codes from official moms-koder JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "entity_id",
            help="Entity ID to import VAT codes into",
        )

    @transaction.atomic
    def handle(self, entity_id, *args, **options):
        # ---- Entity ----
        try:
            entity = Entity.objects.get(pk=entity_id)
        except Entity.DoesNotExist:
            raise CommandError(f"Entity with id={entity_id} does not exist")

        # ---- File ----
        if not VAT_FILE_PATH.exists():
            raise CommandError(f"VAT file not found: {VAT_FILE_PATH}")

        self.stdout.write(f"Using VAT file: {VAT_FILE_PATH}")

        with VAT_FILE_PATH.open(encoding="utf-8") as f:
            data = json.load(f)

        groups = data.get("momskoder - bruttoliste", [])

        created_groups = 0
        created_codes = 0

        for group_data in groups:
            group_name = group_data["momsgruppe"]
            group_code = group_name.lower().replace(" ", "_")

            vat_group, group_created = VatGroup.objects.get_or_create(
                entity=entity,
                code=group_code,
                defaults={"name": group_name},
            )

            if group_created:
                created_groups += 1

            for row in group_data.get("momskoder", []):
                vat_type = (
                    VatCode.VatType.SALE
                    if row.get("type", "").strip().lower().startswith("salg")
                    else VatCode.VatType.PURCHASE
                )

                ded_rate, ded_method = parse_deduction(row.get("fradragsret"))

                _, code_created = VatCode.objects.update_or_create(
                    entity=entity,
                    code=row.get("momskode NY") or row.get("momskode"),
                    defaults={
                        "group": vat_group,
                        "legacy_code": row.get("momskode", ""),
                        "name": row.get("overskrift", ""),
                        "description": row.get("vejledning", ""),
                        "vat_type": vat_type,
                        "rate": parse_percent(row.get("momssats")),
                        "deduction_rate": ded_rate,
                        "deduction_method": ded_method,
                        "reporting_text": row.get("momsangivelse", ""),
                        "dk_only": row.get("1. Udelukkende handel i DK") == "x",
                        "dk_mixed": row.get("2. Udelukkende handel i DK + blandede aktiviteter") == "x",
                        "international": row.get("3. Også handel med udlandet") == "x",
                        "international_mixed": row.get("4. Også handel med udlandet + blandedeaktiviteter") == "x",
                        "special_scheme": row.get("5. Særkoder") == "x",
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"VAT import completed: {created_groups} groups, {created_codes} new VAT codes"
            )
        )
