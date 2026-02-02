import json
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from core.models import ChartOfAccountsTemplate, ChartOfAccountsNode


class Command(BaseCommand):
    help = "Import Standardkontoplan JSON into ChartOfAccountsTemplate and ChartOfAccountsNode"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="external_files/2026-01-01-Standardkontoplan.json",
            help="Path to Standardkontoplan.json",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing nodes for same template name+valid_from before importing",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        path = opts["path"]
        replace = bool(opts["replace"])

        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        info = payload.get("File info", {}) or {}
        name = info.get("Document name") or "Standardkontoplan"
        valid_from = parse_date(info.get("Valid from date") or "")  # may be None
        source_file = info.get("csv source file") or ""

        template, _ = ChartOfAccountsTemplate.objects.get_or_create(
            name=name,
            valid_from=valid_from,
            defaults={"source_file": source_file},
        )
        if template.source_file != source_file and source_file:
            template.source_file = source_file
            template.save(update_fields=["source_file"])

        if replace:
            template.nodes.all().delete()

        kontoplan = payload.get("Kontoplan", []) or []

        current_header = None
        created = 0
        updated = 0

        def upsert(node_type, number, node_name, parent):
            nonlocal created, updated
            obj, was_created = ChartOfAccountsNode.objects.update_or_create(
                template=template,
                number=int(number),
                defaults={
                    "node_type": node_type,
                    "name": (node_name or "").strip(),
                    "parent": parent,
                },
            )
            created += int(was_created)
            updated += int(not was_created)
            return obj

        for entry in kontoplan:
            kontotype = (entry.get("kontotype") or "").strip().lower()
            number = entry.get("kontonummer")
            node_name = entry.get("navn")

            if not number:
                continue

            if kontotype == "hovedkonto":
                current_header = upsert(
                    ChartOfAccountsNode.NodeType.HEADER,
                    number,
                    node_name,
                    parent=None,
                )

            elif kontotype == "gruppekonto":
                group_node = upsert(
                    ChartOfAccountsNode.NodeType.GROUP,
                    number,
                    node_name,
                    parent=current_header,
                )

                for acc in (entry.get("konti") or []):
                    acc_no = acc.get("kontonummer")
                    acc_name = acc.get("navn")
                    if not acc_no:
                        continue
                    upsert(
                        ChartOfAccountsNode.NodeType.ACCOUNT,
                        acc_no,
                        acc_name,
                        parent=group_node,
                    )

            else:
                # If there are other node types later, skip safely
                continue

        self.stdout.write(self.style.SUCCESS(
            f"COA template '{template}': nodes created={created}, updated={updated}"
        ))
