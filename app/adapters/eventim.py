import json
from datetime import datetime
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from .base import ConcertResult

# eventim.de's own site-search API. It's behind Akamai Bot Manager, so a plain HTTP
# client gets 403'd. We drive a real headless Chromium to establish a browser session,
# then call the JSON API via an in-page fetch() — the request carries the browser's
# fingerprint and Akamai cookies, which is what gets it through. All Eventim quirks
# (and the heavy browser dependency) are contained in this one file.
API_URL = "https://public-api.eventim.com/websearch/search/api/exploration/v1/products"
HOME_URL = "https://www.eventim.de/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# On Linux/containers headless Chromium needs --no-sandbox to launch at all, and the
# rest silence the GPU/dbus/rasterizer noise it otherwise floods into stderr.
LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-software-rasterizer",
    "--log-level=3",
]

_FETCH_JS = """
async (url) => {
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
    return { status: r.status, body: await r.text() };
}
"""


class EventimBlockedError(RuntimeError):
    """Akamai refused the request even from the browser context."""


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize(value: str | None) -> str:
    return "".join((value or "").lower().split())


class EventimAdapter:
    name = "eventim"

    def fetch_concerts(self, artist_name: str) -> list[ConcertResult]:
        concerts: list[ConcertResult] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=LAUNCH_ARGS)
            try:
                context = browser.new_context(locale="de-DE", user_agent=USER_AGENT)
                page = context.new_page()
                self._establish_session(page)

                page_num = 1
                while True:
                    payload = self._fetch_page(page, artist_name, page_num)
                    for product in payload.get("products", []):
                        if not self._features_artist(product, artist_name):
                            continue  # fuzzy search hit; artist not actually in the lineup
                        concert = self._to_concert(product)
                        if concert:
                            concerts.append(concert)
                    if page_num >= payload.get("totalPages", 1):
                        break
                    page_num += 1
            finally:
                browser.close()
        return concerts

    def _features_artist(self, product: dict, artist_name: str) -> bool:
        target = _normalize(artist_name)
        attractions = product.get("attractions") or []
        return any(_normalize(a.get("name")) == target for a in attractions)

    def _establish_session(self, page) -> None:
        try:
            page.goto(HOME_URL, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            pass  # a partial load still seeds enough state for the in-page fetch
        page.wait_for_timeout(1500)

    def _fetch_page(self, page, artist_name: str, page_num: int) -> dict:
        url = (
            f"{API_URL}?webId=web__eventim-de&language=de"
            f"&search_term={quote(artist_name)}&sort=DateAsc&page={page_num}&top=50"
        )
        status = None
        for attempt in range(4):
            result = page.evaluate(_FETCH_JS, url)
            status = result["status"]
            if status == 200:
                return json.loads(result["body"])
            page.wait_for_timeout(1000 * (attempt + 1))  # back off, then re-warm the session
            self._establish_session(page)
        raise EventimBlockedError(
            f"Eventim kept returning {status} for '{artist_name}' after retries. "
            "Akamai may have tightened — see README."
        )

    def _to_concert(self, product: dict) -> ConcertResult | None:
        live = product.get("typeAttributes", {}).get("liveEntertainment")
        if not live:
            return None  # non-concert product (e.g. merch, package)

        location = live.get("location") or {}
        # Eventim reports status as Available / SoldOut / Cancelled, and only carries
        # `price` (the "ab X €" figure) while tickets are actually in stock.
        return ConcertResult(
            product_id=str(product["productId"]),
            name=product.get("name", ""),
            start_date=_parse_date(live.get("startDate")),
            city=location.get("city"),
            venue=location.get("name"),
            link=product.get("link"),
            status=product.get("status"),
            in_stock=product.get("inStock"),
            price=product.get("price"),
            currency=product.get("currency"),
        )
