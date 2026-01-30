from __future__ import annotations

from datetime import date
from decimal import Decimal
import ssl
import certifi
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET

ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def fetch_ecb_daily_rates(timeout: int = 20) -> tuple[date, dict[str, Decimal]]:
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = Request(ECB_DAILY_URL, headers={"User-Agent": "Kingfisher-ERP/1.0"})

    with urlopen(req, timeout=timeout, context=ctx) as resp:
        xml = resp.read()

    root = ET.fromstring(xml)
    ns = {"def": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}

    cube_time = root.find(".//def:Cube/def:Cube", ns)
    if cube_time is None or "time" not in cube_time.attrib:
        raise ValueError("ECB XML did not contain a date")

    as_of = date.fromisoformat(cube_time.attrib["time"])

    rates: dict[str, Decimal] = {"EUR": Decimal("1")}
    for c in cube_time.findall("def:Cube", ns):
        cur = c.attrib.get("currency")
        rate = c.attrib.get("rate")
        if cur and rate:
            rates[cur] = Decimal(rate)

    return as_of, rates
