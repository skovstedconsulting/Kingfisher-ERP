from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    Entity,
    ChartOfAccountsTemplate,
    ChartOfAccountsNode,
    Account,
)


class Command(BaseCommand):
    help = "Create/update entity Account tree from a ChartOfAccountsTemplate"

    def add_arguments(self, parser):
        parser.add_argument("--entity-id", type=int, required=True)
        parser.add_argument(
            "--template-id",
            type=int,
            default=None,
            help="Template ID. If omitted, uses the most recent (valid_from desc).",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete all accounts for entity before recreating.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        entity = Entity.objects.get(id=opts["entity_id"])
        template_id = opts["template_id"]
        replace = bool(opts["replace"])

        if template_id:
            template = ChartOfAccountsTemplate.objects.get(id=template_id)
        else:
            template = ChartOfAccountsTemplate.objects.order_by("-valid_from", "-id").first()
            if not template:
                raise RuntimeError("No ChartOfAccountsTemplate found. Import COA template first.")

        if replace:
            Account.objects.filter(entity=entity).delete()

        # Preload nodes for deterministic creation: parents first
        nodes = (
            ChartOfAccountsNode.objects
            .filter(template=template)
            .select_related("parent")
            .order_by("number")
        )

        # Create/update accounts in parent-first order using the node.parent mapping.
        created = 0
        updated = 0
        map_node_to_account = {}

        # We may need multiple passes if ordering isn't strictly parent-first (safe)
        remaining = list(nodes)
        max_passes = 10

        for _ in range(max_passes):
            if not remaining:
                break

            next_remaining = []
            progressed = False

            for node in remaining:
                parent_acc = None
                if node.parent_id:
                    parent_acc = map_node_to_account.get(node.parent_id)
                    if parent_acc is None:
                        next_remaining.append(node)
                        continue

                is_postable = node.node_type == ChartOfAccountsNode.NodeType.ACCOUNT
                number = str(node.number)

                acc, was_created = Account.objects.update_or_create(
                    entity=entity,
                    number=number,
                    defaults={
                        "name": node.name,
                        "parent": parent_acc,
                        "is_postable": is_postable,
                    },
                )
                map_node_to_account[node.id] = acc
                created += int(was_created)
                updated += int(not was_created)
                progressed = True

            if not progressed and next_remaining:
                # If we cannot resolve parents, template data has an issue.
                unresolved = ", ".join(str(n.number) for n in next_remaining[:20])
                raise RuntimeError(f"Could not resolve parent chain for nodes: {unresolved}")

            remaining = next_remaining

        if remaining:
            unresolved = ", ".join(str(n.number) for n in remaining[:20])
            raise RuntimeError(f"Still had unresolved nodes after passes: {unresolved}")

        # Ensure MPTT fields are correct (safe after mass update/create)
        Account.objects.rebuild()

        self.stdout.write(self.style.SUCCESS(
            f"Accounts created/updated for entity={entity.id} from template={template.id}: "
            f"created={created}, updated={updated}"
        ))
