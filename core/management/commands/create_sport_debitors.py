from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from masterdata.models import Debtor, DebtorGroup
from core.models import Entity

class Command(BaseCommand):
    help = "Create 20 debtors for famous soccer players"



    def handle(self, *args, **options):

        entity = Entity.objects.first()
        debtor_group = DebtorGroup.objects.first()

        if not debtor_group:
            self.stdout.write(self.style.ERROR("No DebtorGroup found"))
            return

        players = [
            ("001", "Cristiano Ronaldo"),
            ("002", "Lionel Messi"),
            ("003", "Pelé"),
            ("004", "Diego Maradona"),
            ("005", "Johan Cruyff"),
            ("006", "Zinedine Zidane"),
            ("007", "Ronaldinho"),
            ("008", "Gianluigi Buffon"),
            ("009", "Mia Hamm"),
            ("010", "Pele dos Santos"),
            ("011", "Franz Beckenbauer"),
            ("012", "Bobby Fischer"),
            ("013", "Giuseppe Meazza"),
            ("014", "Alfredo Di Stéfano"),
            ("015", "Garrincha"),
            ("016", "Bobby Charlton"),
            ("017", "George Best"),
            ("018", "Eusébio"),
            ("019", "Ferenc Puskás"),
            ("020", "Kaká"),
        ]

        for number, name in players:
            Debtor.objects.get_or_create(
                entity=entity,
                number=number,
                defaults={
                    "name": name,
                    "group": debtor_group,
                    "vat_area": Debtor.VatArea.DK,
                },
            )

        self.stdout.write(
            self.style.SUCCESS("Successfully created 20 soccer player debtors")
        )