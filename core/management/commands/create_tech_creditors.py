from django.core.management.base import BaseCommand  # Import BaseCommand
from core.models import Entity
from masterdata.models import CreditorGroup, Creditor

class Command(BaseCommand):
    help = "Create creditors for the 10 largest tech companies"

    def handle(self, *args, **options):
        tech_companies = [
            "Apple", "Microsoft", "Alphabet", "Amazon", "NVIDIA",
            "Meta", "Tesla", "Broadcom", "Cisco", "Oracle"
        ]
        
        entity = Entity.objects.first()  # Adjust as needed
        group, _ = CreditorGroup.objects.get_or_create(
            entity=entity, code="TECH", defaults={"name": "Technology"}
        )
        
        for idx, company in enumerate(tech_companies, 1):
            Creditor.objects.get_or_create(
                entity=entity,
                number=f"TECH{idx:03d}",
                defaults={"name": company, "group": group}
            )
        
        self.stdout.write(self.style.SUCCESS("Successfully created tech company creditors"))