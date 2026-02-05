from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Entity, UserProfile
from core.models import IsoCountryCodes, IsoCurrencyCodes
import json
import random
from pathlib import Path

User = get_user_model()

class Command(BaseCommand):
    help = "Create 3 entities: Danish, German, and English"

    def handle(self, *args, **options):
        entities_data = [
            {"name": "Danish Entity", "country_code": "DK", "currency_code": "DKK"},
            {"name": "German Entity", "country_code": "DE", "currency_code": "EUR"},
            {"name": "English Entity", "country_code": "GB", "currency_code": "GBP"},
        ]

        for data in entities_data:
            country = IsoCountryCodes.objects.get(code=data["country_code"])
            currency = IsoCurrencyCodes.objects.get(code=data["currency_code"])

            entity, created = Entity.objects.get_or_create(
                name=data["name"],
                defaults={
                    "country": country,
                    "base_currency": currency,
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created entity: {entity.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Entity already exists: {entity.name}")
                )

        self.stdout.write(
            self.style.SUCCESS("\n✓ All entities created successfully!")
        )


        # Read the JSON file
        json_file = Path("external_files/folketinget.json")
        with open(json_file, "r", encoding="utf-8") as f:
            records = json.load(f)

        # Get all entities
        entities = list(Entity.objects.all())
        if not entities:
            self.stdout.write(self.style.ERROR("No entities found!"))
            return

        # Create users and profiles
        for record in records:
            # Parse name into first and last name
            full_name = record.get("name", "")
            name_parts = full_name.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            username = record.get("username") or record.get("email", "").split("@")[0]
            email = record.get("email", f"{username}@example.com")

            user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            },
            )

            if created:
                # Create user profile with random entity, image_url, and address
                entity = random.choice(entities)
                UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "entity": entity,
                        "image_url": record.get("image_url", ""),
                        "address": record.get("address", ""),
                    },
                )
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created user: {username} (Entity: {entity.name})")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ User already exists: {username}")
                )

        self.stdout.write(
            self.style.SUCCESS("\n✓ All users created successfully!")
        )