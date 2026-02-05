from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP
import random
import re

from core.models import Entity
from masterdata.models import Item, ItemGroup


def money(x: float) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def slugify_code(text: str, max_len: int = 3) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "", text).upper()
    return (s[:max_len] or "ITM")


def ean13_with_checksum(prefix12: str) -> str:
    if not re.fullmatch(r"\d{12}", prefix12):
        raise ValueError("prefix12 must be exactly 12 digits")

    digits = [int(c) for c in prefix12]
    odd_sum = sum(digits[0::2])
    even_sum = sum(digits[1::2])
    total = odd_sum + 3 * even_sum
    check = (10 - (total % 10)) % 10
    return prefix12 + str(check)


GADGETS = [
    ("Wireless Noise-Canceling Headphones", "Audio & Media"),
    ("Bone Conduction Headset", "Audio & Media"),
    ("Smart Soundbar", "Audio & Media"),
    ("Portable Hi-Fi Radio", "Audio & Media"),
    ("Clip-On Lavalier Microphone", "Audio & Media"),
    ("Digital Voice Recorder", "Audio & Media"),
    ("FM Transmitter for Car", "Audio & Media"),
    ("Smart Alarm Clock with Speaker", "Audio & Media"),
    ("Bluetooth Party Speaker", "Audio & Media"),
    ("Pocket MP3 Player", "Audio & Media"),
    ("High-Capacity Power Bank", "Power & Charging"),
    ("Solar USB Charger", "Power & Charging"),
    ("Wireless Charging Pad", "Power & Charging"),
    ("USB-C GaN Wall Charger", "Power & Charging"),
    ("Car Fast-Charge Adapter", "Power & Charging"),
    ("Laptop Power Hub", "Power & Charging"),
    ("Multi-Outlet Smart Plug", "Power & Charging"),
    ("Emergency Hand-Crank Charger", "Power & Charging"),
    ("Magnetic Charging Dock", "Power & Charging"),
    ("Battery Health Tester", "Power & Charging"),
    ("Adjustable Phone Stand", "Mobile & Accessories"),
    ("Foldable Tablet Holder", "Mobile & Accessories"),
    ("Magnetic Phone Mount", "Mobile & Accessories"),
    ("Waterproof Phone Pouch", "Mobile & Accessories"),
    ("Stylus Pen for Touchscreens", "Mobile & Accessories"),
    ("Phone Camera Lens Kit", "Mobile & Accessories"),
    ("Anti-Spy Screen Protector", "Mobile & Accessories"),
    ("Bluetooth Camera Shutter", "Mobile & Accessories"),
    ("Phone Cooling Fan", "Mobile & Accessories"),
    ("Smart SIM Card Organizer", "Mobile & Accessories"),
    ("Ergonomic Wireless Mouse", "Computer & Office"),
    ("Mechanical Keyboard", "Computer & Office"),
    ("USB-C Docking Station", "Computer & Office"),
    ("Laptop Cooling Pad", "Computer & Office"),
    ("Webcam with Privacy Shutter", "Computer & Office"),
    ("Noise-Reducing Conference Mic", "Computer & Office"),
    ("Smart Desk Lamp", "Computer & Office"),
    ("Digital Note-Taking Pad", "Computer & Office"),
    ("Fingerprint USB Security Key", "Computer & Office"),
    ("Cable Management Box", "Computer & Office"),
    ("Smart Wi-Fi Light Bulb", "Smart Home"),
    ("Motion Sensor Alarm", "Smart Home"),
    ("Smart Door Sensor", "Smart Home"),
    ("Indoor Air Quality Monitor", "Smart Home"),
    ("Smart Plug with Energy Meter", "Smart Home"),
    ("Wi-Fi Temperature Sensor", "Smart Home"),
    ("Smart IR Remote Controller", "Smart Home"),
    ("Leak Detection Sensor", "Smart Home"),
    ("Smart Smoke Detector", "Smart Home"),
    ("Voice-Controlled Power Strip", "Smart Home"),
    ("Fitness Activity Tracker", "Wearables & Health"),
    ("Smart Body Scale", "Wearables & Health"),
    ("Blood Pressure Monitor", "Wearables & Health"),
    ("Posture Correction Wearable", "Wearables & Health"),
    ("Smart Sleep Monitor", "Wearables & Health"),
    ("UV Exposure Tracker", "Wearables & Health"),
    ("Digital Thermometer", "Wearables & Health"),
    ("Smart Hydration Reminder", "Wearables & Health"),
    ("Pulse Oximeter", "Wearables & Health"),
    ("Smart Ring", "Wearables & Health"),
    ("Game Controller for PC", "Gaming & Entertainment"),
    ("Retro Mini Game Console", "Gaming & Entertainment"),
    ("VR Headset", "Gaming & Entertainment"),
    ("Gaming Headset Stand", "Gaming & Entertainment"),
    ("USB Racing Wheel", "Gaming & Entertainment"),
    ("Streaming Capture Card", "Gaming & Entertainment"),
    ("LED Gaming Light Bar", "Gaming & Entertainment"),
    ("Mobile Gaming Grip", "Gaming & Entertainment"),
    ("Arcade Joystick Controller", "Gaming & Entertainment"),
    ("Handheld Emulator Console", "Gaming & Entertainment"),
    ("Dash Camera", "Car Gadgets"),
    ("GPS Tracker", "Car Gadgets"),
    ("Car Tire Pressure Monitor", "Car Gadgets"),
    ("Smart Parking Sensor", "Car Gadgets"),
    ("OBD-II Diagnostic Scanner", "Car Gadgets"),
    ("Heated Seat Cushion", "Car Gadgets"),
    ("Car Air Purifier", "Car Gadgets"),
    ("Heads-Up Display Unit", "Car Gadgets"),
    ("Rear-Seat Tablet Holder", "Car Gadgets"),
    ("Car Jump Starter", "Car Gadgets"),
    ("Laser Distance Meter", "Tools & Misc Tech"),
    ("Digital Spirit Level", "Tools & Misc Tech"),
    ("Smart Stud Finder", "Tools & Misc Tech"),
    ("Thermal Imaging Camera", "Tools & Misc Tech"),
    ("USB Endoscope Camera", "Tools & Misc Tech"),
    ("Electronic Screwdriver", "Tools & Misc Tech"),
    ("Smart Measuring Tape", "Tools & Misc Tech"),
    ("Digital Caliper", "Tools & Misc Tech"),
    ("RFID Card Reader", "Tools & Misc Tech"),
    ("Smart Tool Organizer", "Tools & Misc Tech"),
    ("GPS Hiking Watch", "Travel & Outdoor"),
    ("Smart Luggage Tracker", "Travel & Outdoor"),
    ("Portable Water Purifier", "Travel & Outdoor"),
    ("Travel Power Adapter", "Travel & Outdoor"),
    ("Smart Camping Lantern", "Travel & Outdoor"),
    ("Noise-Canceling Sleep Buds", "Travel & Outdoor"),
    ("Electronic Luggage Scale", "Travel & Outdoor"),
    ("Solar Camping Radio", "Travel & Outdoor"),
    ("Emergency SOS Beacon", "Travel & Outdoor"),
    ("Smart Bike Tracker", "Travel & Outdoor"),
]

PRICE_BANDS = {
    "Audio & Media": (80, 450, 0.35),
    "Power & Charging": (15, 200, 0.40),
    "Mobile & Accessories": (10, 160, 0.45),
    "Computer & Office": (20, 300, 0.38),
    "Smart Home": (15, 250, 0.40),
    "Wearables & Health": (20, 350, 0.33),
    "Gaming & Entertainment": (25, 500, 0.32),
    "Car Gadgets": (25, 400, 0.35),
    "Tools & Misc Tech": (20, 600, 0.30),
    "Travel & Outdoor": (15, 350, 0.37),
}


class Command(BaseCommand):
    help = "Seed 100 unique gadget Items using the first Entity and first ItemGroup. Generates SKU + EAN-13."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--sku-prefix", type=str, default="GAD")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        seed = options["seed"]
        sku_prefix = (options["sku_prefix"] or "GAD").upper().strip()
        dry_run = options["dry_run"]

        entity = Entity.objects.first()
        if not entity:
            self.stdout.write(self.style.ERROR("No Entity found"))
            return

        item_group = ItemGroup.objects.first()
        if not item_group:
            self.stdout.write(self.style.ERROR("No ItemGroup found"))
            return

        rng = random.Random(seed)

        existing_numbers = set(Item.objects.filter(entity=entity).values_list("number", flat=True))
        existing_eans = set(
            Item.objects.filter(entity=entity)
            .exclude(ean__isnull=True)
            .values_list("ean", flat=True)
        )

        def next_unique_number(i: int, category: str) -> str:
            code = slugify_code(category, 3)
            candidate = f"{sku_prefix}-{code}-{i+1:04d}"
            j = 0
            while candidate in existing_numbers:
                j += 1
                candidate = f"{sku_prefix}-{code}-{i+1:04d}-{j}"
            existing_numbers.add(candidate)
            return candidate

        def next_unique_ean(i: int) -> str:
            # Internal dev/test EAN series: 200 + entity(3 digits) + index(6 digits) = 12 digits
            ent = int(entity.id) % 1000
            j = i
            while True:
                prefix12 = f"200{ent:03d}{j+1:06d}"
                ean = ean13_with_checksum(prefix12)
                if ean not in existing_eans:
                    existing_eans.add(ean)
                    return ean
                j += 1

        items = []
        for i, (name, category) in enumerate(GADGETS):
            sales_min, sales_max, margin_min = PRICE_BANDS[category]
            sales = money(rng.uniform(sales_min, sales_max))
            margin = rng.uniform(margin_min, min(margin_min + 0.20, 0.80))
            purchase = money(float(sales) * (1 - margin) * rng.uniform(0.96, 1.02))
            if purchase >= sales:
                purchase = sales - money(0.01)

            items.append(
                Item(
                    entity=entity,
                    group=item_group,            # ✅ always first group
                    number=next_unique_number(i, category),
                    name=name,
                    is_stock_item=True,
                    sales_price=sales,
                    purchase_cost=purchase,
                    ean=next_unique_ean(i),
                )
            )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY RUN: would create {len(items)} items for Entity={entity.id} using ItemGroup={item_group.id}"
                )
            )
            return

        with transaction.atomic():
            Item.objects.bulk_create(items, batch_size=200)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(items)} items for Entity={entity.id} using ItemGroup={item_group.id}"
            )
        )
