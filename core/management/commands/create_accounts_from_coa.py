from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Entity, ChartOfAccountsTemplate, ChartOfAccountsNode, Account


def infer_account_type(account_no: int) -> str:
    """
    Simple heuristic. Adjust to your chart.
    """
    if 1000 <= account_no < 2000:
        return Account.AccountType.ASSET
    if 2000 <= account_no < 3000:
        return Account.AccountType.LIABILITY
    if 3000 <= account_no < 4000:
        return Account.AccountType.EQUITY
    if 4000 <= account_no < 8000:
        return Account.AccountType.INCOME
    return Account.AccountType.EXPENSE


class Command(BaseCommand):
    help = "Create Entity accounts from a chart of accounts template (COA)."

    def add_arguments(self, parser):
        parser.add_argument("--entity", required=True, help="Entity UUID")
        parser.add_argument("--template-id", type=int, required=True, help="ChartOfAccountsTemplate ID")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be created/updated")
        parser.add_argument("--overwrite-names", action="store_true", help="Update existing account names from template")

    @transaction.atomic
    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        overwrite_names = opts["overwrite_names"]

        try:
            entity = Entity.objects.get(id=opts["entity"])
        except Entity.DoesNotExist:
            raise CommandError(f"Entity not found: {opts['entity']}")

        try:
            template = ChartOfAccountsTemplate.objects.get(id=opts["template_id"])
        except ChartOfAccountsTemplate.DoesNotExist:
            raise CommandError(f"Template not found: {opts['template_id']}")

        nodes = ChartOfAccountsNode.objects.filter(
            template=template,
            node_type=ChartOfAccountsNode.NodeType.ACCOUNT,
        ).order_by("number")

        created = 0
        updated = 0

        for node in nodes:
            acc_no = str(node.number)  # Account.number is CharField
            acc_type = infer_account_type(node.number)

            defaults = {
                "name": node.name,
                "type": acc_type,
                "is_active": True,
                "template_node": node,
            }

            existing = Account.objects.filter(entity=entity, number=acc_no).first()

            if existing:
                if overwrite_names and existing.name != node.name:
                    if not dry_run:
                        existing.name = node.name
                        existing.template_node = node
                        existing.save(update_fields=["name", "template_node"])
                    updated += 1
                continue

            if dry_run:
                created += 1
                continue

            Account.objects.create(entity=entity, number=acc_no, **defaults)
            created += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN (no changes written)"))

        self.stdout.write(self.style.SUCCESS(
            f"Entity={entity} Template={template} -> created={created}, updated={updated}"
        ))
