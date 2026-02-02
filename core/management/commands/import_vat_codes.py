import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from core.models import Entity, VatGroup, VatCode


def _parse_percent_to_rate(s: str | None):
    """
    "25%" -> Decimal("0.2500")
    "0%"  -> Decimal("0.0000")
    "x%" or "" -> None
    """
    if not s:
        return None
    s = s.strip()
    if not s or "x" in s.lower():
        return None
    if s.endswith("%"):
        num = s[:-1].strip().replace(",", ".")
        try:
            return (Decimal(num) / Decimal("100")).quantize(Decimal("0.0001"))
        except Exception:
            return None
    return None


def _flag(v: str | None) -> bool:
    return (v or "").strip().lower() == "x"


class Command(BaseCommand):
    help = "Import Danish VAT groups/codes from Momskoder-Bruttoliste JSON into VatGroup/VatCode for an entity"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="external_files/2026-01-01-Momskoder-Bruttoliste.json",
            help="Path to Momskoder-Bruttoliste.json",
        )
        parser.add_argument(
            "--entity-id",
            type=int,
            required=True,
            help="Entity ID to import VAT codes into",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing VAT codes/groups for the entity before importing",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]
        entity_id = opts["entity_id"]
        replace = bool(opts["replace"])

        entity = Entity.objects.get(id=entity_id)

        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        groups = payload.get("momskoder - bruttoliste", []) or []

        if replace:
            VatCode.objects.filter(entity=entity).delete()
            VatGroup.objects.filter(entity=entity).delete()

        created_g = 0
        updated_g = 0
        created_c = 0
        updated_c = 0

        for g in groups:
            group_name = (g.get("momsgruppe") or "").strip()
            if not group_name:
                continue

            group_code = slugify(group_name)[:50] or group_name[:50]

            vat_group, was_created = VatGroup.objects.update_or_create(
                entity=entity,
                code=group_code,
                defaults={"name": group_name},
            )
            created_g += int(was_created)
            updated_g += int(not was_created)

            for row in (g.get("momskoder") or []):
                vat_type_raw = (row.get("type") or "").strip().lower()
                vat_type = VatCode.VatType.SALE if "salg" in vat_type_raw else VatCode.VatType.PURCHASE

                # Prefer the "NY" naming as your canonical code, and store legacy in legacy_code.
                code = (row.get("momskode betegnelse NY") or "").strip()[:20]
                legacy_code = (row.get("momskode betegnelse") or "").strip()[:20]

                if not code:
                    # fallback if file is missing the NY field
                    code = (row.get("momskode NY") or row.get("momskode") or "").strip()[:20]

                if not code:
                    continue

                name = (row.get("overskrift") or row.get("momskode betegnelse NY") or row.get("momskode betegnelse") or "").strip()
                description = (row.get("vejledning") or "").strip()
                reporting_text = (row.get("momsangivelse") or "").strip()

                rate = _parse_percent_to_rate(row.get("momssats"))
                deduction_rate = _parse_percent_to_rate(row.get("fradragsret"))  # often blank; fine

                defaults = {
                    "group": vat_group,
                    "legacy_code": legacy_code,
                    "name": name[:255],
                    "description": description,
                    "vat_type": vat_type,
                    "rate": rate,
                    "deduction_rate": deduction_rate,
                    "deduction_method": (row.get("fradragsmetode") or row.get("deduction_method") or "").strip(),
                    "reporting_text": reporting_text[:255],
                    "dk_only": _flag(row.get("1. Udelukkende handel i DK")),
                    "dk_mixed": _flag(row.get("2. Udelukkende handel i DK + blandede aktiviteter")),
                    "international": _flag(row.get("3. Også handel med udlandet")),
                    "international_mixed": _flag(row.get("4. Også handel med udlandet + blandedeaktiviteter")),
                    "special_scheme": _flag(row.get("5. Særkoder")),
                }

                obj, was_created = VatCode.objects.update_or_create(
                    entity=entity,
                    code=code,
                    defaults=defaults,
                )
                created_c += int(was_created)
                updated_c += int(not was_created)

        self.stdout.write(self.style.SUCCESS(
            f"VAT import entity={entity_id}: "
            f"groups created={created_g}, updated={updated_g}; "
            f"codes created={created_c}, updated={updated_c}"
        ))
