from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.ft.dk/-/media/cv/foto/2022/kf/mette-abildgaard/mette_abildgaard_500.jpg"
OUT = Path("mette_abildgaard_500.jpg")



with sync_playwright() as p:
    #browser = p.chromium.launch(headless=True)
    browser = p.chromium.launch(headless=False, slow_mo=50)
    context = browser.new_context(
        locale="da-DK",
        extra_http_headers={
            "Referer": "https://www.ft.dk/",
            "Accept-Language": "da-DK,da;q=0.9,en;q=0.8",
        },
    )

    page = context.new_page()

    response = page.goto(URL, wait_until="networkidle")

    if response is None or response.status != 200:
        raise RuntimeError(f"Failed to fetch image (status={response.status if response else 'no response'})")

    OUT.write_bytes(response.body())

    browser.close()

print(f"Downloaded to {OUT.resolve()}")
