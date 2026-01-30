import datetime as dt
from decimal import Decimal
from xml.etree import ElementTree as ET
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now

import ssl
import certifi

from core.models import ExchangeRate, IsoCurrencyCodes  # adjust if needed

ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

def fetch_xml(url, timeout=10):
    ctx = ssl.create_default_context(cafile=certifi.where())

    req = Request(
        url,
        headers={"User-Agent": "Kingfisher-ERP/1.0"},
    )

    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read()
    except Exception as e:
        raise RuntimeError(f"ECB connection error: {e}") from e

def parse_ecb(xml_bytes: bytes) -> tuple[dt.date, dict[str, Decimal]]:
    root = ET.fromstring(xml_bytes)

    time_cube = None
    for el in root.iter():
        if el.tag.endswith("Cube") and "time" in el.attrib:
            time_cube = el
            break

    if not time_cube:
        raise RuntimeError("ECB XML: could not find date cube")

    rate_date = dt.date.fromisoformat(time_cube.attrib["time"])

    rates: dict[str, Decimal] = {"EUR": Decimal("1")}
    for cube in time_cube:
        ccy = cube.attrib.get("currency")
        rate = cube.attrib.get("rate")
        if ccy and rate:
            rates[ccy.upper()] = Decimal(rate)

    return rate_date, rates


def convert_base(rates_eur: dict[str, Decimal], base: str) -> dict[str, Decimal]:
    base = base.upper()
    if base not in rates_eur:
        raise ValueError(f"Base currency {base} not found in ECB feed")

    eur_to_base = rates_eur[base]
    base_to_eur = Decimal("1") / eur_to_base

    converted = {}
    for ccy, eur_to_ccy in rates_eur.items():
        converted[ccy] = base_to_eur * eur_to_ccy

    converted[base] = Decimal("1")
    return converted


class Command(BaseCommand):
    help = "Fetch daily ECB exchange rates (stdlib only, no requests)"

    def add_arguments(self, parser):
        parser.add_argument("--base", default="EUR", help="Base currency (default EUR)")
        parser.add_argument("--timeout", type=int, default=30)

    @transaction.atomic
    def handle(self, *args, **opts):
        base = opts["base"].upper()
        timeout = opts["timeout"]

        xml = fetch_xml(ECB_DAILY_URL, timeout=timeout)
        rate_date, rates = parse_ecb(xml)

        if base != "EUR":
            rates = convert_base(rates, base)

        valid = set(IsoCurrencyCodes.objects.values_list("code", flat=True))

        created = updated = 0
        for quote, rate in rates.items():
            if quote == base or quote not in valid:
                continue

            obj, is_created = ExchangeRate.objects.update_or_create(
                date=rate_date,
                base=base,
                quote=quote,
                defaults={
                    "rate": rate,
                    "source": "ECB",
                    "fetched_at": now(),
                },
            )
            created += int(is_created)
            updated += int(not is_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"ECB rates {rate_date} base={base}: created={created}, updated={updated}"
            )
        )
