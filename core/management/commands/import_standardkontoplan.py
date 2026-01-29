import json
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import ChartOfAccountsTemplate, ChartOfAccountsNode
from pathlib import Path
from django.conf import settings

class Command(BaseCommand):
    help = "Import Danish Standardkontoplan (chart of accounts template) from JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=Path(settings.BASE_DIR) / "external_files" / "2026-01-01-Standardkontoplan.json",
            help="Path to Standardkontoplan JSON",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete and re-import nodes for the matched template (by name + valid_from).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = options["path"]
        replace = options["replace"]

        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        info = payload.get("File info", {}) or {}
        template_name = info.get("Document name", "Standardkontoplan")
        valid_from_raw = info.get("Valid from date", None)
        source_file = info.get("csv source file", "") or ""

        valid_from = None
        if valid_from_raw:
            # expects "YYYY-MM-DD"
            y, m, d = [int(x) for x in valid_from_raw.split("-")]
            valid_from = date(y, m, d)

        template, _ = ChartOfAccountsTemplate.objects.update_or_create(
            name=template_name,
            valid_from=valid_from,
            defaults={"source_file": source_file},
        )

        if replace:
            ChartOfAccountsNode.objects.filter(template=template).delete()

        created = 0
        updated = 0

        def upsert_node(node_type, number, name, parent):
            nonlocal created, updated
            obj, was_created = ChartOfAccountsNode.objects.update_or_create(
                template=template,
                number=int(number),
                defaults={
                    "node_type": node_type,
                    "name": name or "",
                    "parent": parent,
                },
            )
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
            return obj

        kontoplan = payload.get("Kontoplan", []) or []
        current_header = None

        for entry in kontoplan:
            kontotype = entry.get("kontotype")
            number = entry.get("kontonummer")
            name = entry.get("navn", "")

            if kontotype == "hovedkonto":
                current_header = upsert_node(ChartOfAccountsNode.NodeType.HEADER, number, name, parent=None)

            elif kontotype == "gruppekonto":
                group_parent = current_header  # group sits under latest header (as in file)
                group_node = upsert_node(ChartOfAccountsNode.NodeType.GROUP, number, name, parent=group_parent)

                for leaf in entry.get("konti", []) or []:
                    upsert_node(
                        ChartOfAccountsNode.NodeType.ACCOUNT,
                        leaf.get("kontonummer"),
                        leaf.get("navn", ""),
                        parent=group_node,
                    )

            else:
                # If file introduces other types later, handle safely
                # Put it under current header if present.
                parent = current_header
                upsert_node(ChartOfAccountsNode.NodeType.ACCOUNT, number, name, parent=parent)

        self.stdout.write(self.style.SUCCESS(
            f"Imported Standardkontoplan template='{template}' nodes: created={created}, updated={updated}"
        ))
