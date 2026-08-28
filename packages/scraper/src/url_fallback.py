"""URL fallback module for expired property detail pages.

When a detail page returns 404, this module fetches a new property detail URL
from the corresponding listing page of the same service.

Service configuration is centralised in SERVICE_CONFIG so that adding a new
service requires editing only one place instead of three.
"""

import re
from urllib.parse import urljoin, urlparse
from typing import Optional

from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

from constants import USER_AGENT, VIEWPORT_HEIGHT


# ---------------------------------------------------------------------------
# Centralised service configuration
# Each entry contains:
#   domain      : substring matched against the URL host to identify the service
#   selectors   : CSS selectors for detail links on listing pages
#   patterns    : regex patterns that identify a detail-page URL
# ---------------------------------------------------------------------------
SERVICE_CONFIG: dict[str, dict] = {
    "suumo": {
        "domain": "suumo",
        "selectors": [
            "a.cassetteitem_other-linktext",
            'a[href*="/chintai/jnc_"]',
            'a[href*="/ms/jnc_"]',
            'a[href*="/chukoikkodate/"]',
            '.cassetteitem a[href*="/jnc_"]',
            '.property_unit a[href*="nc_"]',
        ],
        "patterns": [
            r"/chintai/jnc_\d+",
            r"/ms/jnc_\d+",
            r"/chukoikkodate/.+/nc_",
            r"/library/.+/sc_",
        ],
    },
    "athome": {
        "domain": "athome",
        "selectors": [
            'a[href*="/chintai/"]',
            'a[href*="/mansion/"]',
            '.property-list a[href*="/detail/"]',
            '.item a[href*="/detail/"]',
            '.p-property a[href]',
        ],
        "patterns": [
            r"/chintai/\d+",
            r"/mansion/\d+",
            r"/detail/\d+",
        ],
    },
    "canary": {
        "domain": "canary",
        "selectors": [
            'a[href*="/rooms/"]',
            'a[href*="/room/"]',
            'a[href*="/property/"]',
            '.room-card a[href]',
            '.property-card a[href]',
        ],
        "patterns": [
            r"/rooms/[a-zA-Z0-9\-]+",
            r"/room/[a-zA-Z0-9\-]+",
            r"/property/[a-zA-Z0-9\-]+",
        ],
    },
    "carsensor": {
        "domain": "carsensor",
        "selectors": [
            'a[href*="/usedcar/detail/"]',
            '.cassetteitem a[href*="/usedcar/detail/"]',
            '.car-card a[href*="/detail/"]',
            'a[href*="/usedcar/detail/VU"]',
            '.list_item a[href*="/detail/"]',
            'a[href*="/usedcar/detail/"][href$="/index.html"]',
            '.mod-cassette a[href*="/usedcar/detail/"]',
            '.cassette_list a[href*="/usedcar/detail/"]',
        ],
        "patterns": [
            r"/usedcar/detail/[A-Z0-9]+/",
            r"/usedcar/detail/VU\d+",
            r"/usedcar/detail/[A-Z]{2}\d+/index\.html",
        ],
    },
    "goo-net": {
        "domain": "goo-net",
        "selectors": [
            'a[href*="/usedcar/detail/"]',
            'a[href*="/usedcar/spread/"]',
            '.car-card a[href*="/detail/"]',
            '.list-item a[href*="/detail/"]',
            'a[href*="/usedcar/detail/7"]',
            '.car_list a[href*="/usedcar/detail/"]',
            '.search_list a[href*="/usedcar/detail/"]',
            'a[href*="/usedcar/detail/"][href$="/"]',
        ],
        "patterns": [
            r"/usedcar/detail/\d+/",
            r"/usedcar/detail/7\d+",
            r"/usedcar/spread/goo/\d+/\d+\.html",
        ],
    },
    "eheya": {
        "domain": "eheya",
        "selectors": [
            'a[href*="/detail/"]',
            'a[href*="/line/detail/"]',
            '.property-item a[href]',
            '.room-item a[href*="/detail/"]',
        ],
        "patterns": [
            r"/line/detail/\d+",
            r"/detail/\d+",
        ],
    },
    "sumaity": {
        "domain": "sumaity",
        "selectors": [
            'a[href*="_bldg/bldg_"]',
            'a[href*="/chintai/"][href*="_bldg/"]',
            ".property-item a[href]",
        ],
        "patterns": [
            r"_bldg/bldg_\d+",
            r"/chintai/[a-z]+_bldg/bldg_\d+",
        ],
    },
    "smocca": {
        "domain": "smocca",
        "selectors": [
            'a[href*="/bukken/detail/"]',
            '.property-item a[href*="/bukken/detail/"]',
            '.room-card a[href*="/bukken/"]',
        ],
        "patterns": [
            r"/bukken/detail/[a-z0-9_]+",
        ],
    },
    "door": {
        "domain": "door.ac",
        "selectors": [
            'a[href*="/detail/"]',
            '.property-list a[href*="/detail/"]',
            ".room-card a[href]",
        ],
        "patterns": [
            r"/[a-z]+/city-\d+/detail/\d+",
            r"/detail/\d+",
        ],
    },
    "airdoor": {
        "domain": "airdoor",
        "selectors": [
            'a[href*="/detail/"]',
            '.property-card a[href*="/detail/"]',
            'a[href*="/detail/"][href*="/"]',
        ],
        "patterns": [
            r"/detail/\d+/\d+",
        ],
    },
}


def _identify_service(url: str) -> Optional[str]:
    """Identify the service name from a URL by matching domain substrings."""
    domain = urlparse(url).netloc.lower()
    for service_name, cfg in SERVICE_CONFIG.items():
        if cfg["domain"] in domain:
            return service_name
    return None


def _is_detail_url(url: str, service: str) -> bool:
    """Return True if the URL matches a detail-page pattern for the service."""
    for pattern in SERVICE_CONFIG.get(service, {}).get("patterns", []):
        if re.search(pattern, url):
            return True
    return False


async def find_new_detail_url(
    list_page_url: str,
    service_name: str,
    old_detail_url: str,
    viewport_width: int = 1280,
) -> Optional[str]:
    """Fetch the listing page and extract a new property detail URL.

    Args:
        list_page_url: URL of the listing page to scrape for detail links.
        service_name: Service identifier (suumo, athome, canary, …).
        old_detail_url: The expired URL (to avoid returning the same one).
        viewport_width: Browser viewport width.

    Returns:
        A new detail page URL, or None if no suitable URL was found.
    """
    service_key = service_name.lower()
    selectors = SERVICE_CONFIG.get(service_key, {}).get("selectors", [])

    if not selectors:
        print(f"    [URL Fallback] No selectors configured for service: {service_name}")
        return None

    found_urls: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        try:
            page = await browser.new_page(
                viewport={"width": viewport_width, "height": VIEWPORT_HEIGHT},
                user_agent=USER_AGENT,
                locale="ja-JP",
            )
            # Apply playwright-stealth for comprehensive bot detection bypass
            await stealth_async(page)

            response = await page.goto(
                list_page_url, wait_until="networkidle", timeout=30000
            )
            if not response or response.status >= 400:
                print(
                    f"    [URL Fallback] Listing page returned HTTP "
                    f"{response.status if response else 'N/A'}"
                )
                return None

            # Wait longer for JS-rendered content
            await page.wait_for_timeout(3000)

            for selector in selectors:
                try:
                    links = await page.query_selector_all(selector)
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            absolute_url = urljoin(list_page_url, href)
                            if _is_detail_url(absolute_url, service_key):
                                found_urls.append(absolute_url)
                except Exception:
                    continue

            if not found_urls:
                html = await page.content()
                print(
                    f"    [URL Fallback] No detail URLs found on listing page "
                    f"(page content: {len(html)} chars, selectors tried: {len(selectors)})"
                )

        except Exception as e:
            print(f"    [URL Fallback] Error fetching listing page: {e}")
            return None
        finally:
            # Always close the browser, even when an exception occurred
            await browser.close()

    if not found_urls:
        return None

    # Remove duplicates, exclude the expired URL
    old_path = urlparse(old_detail_url).path
    unique_urls: list[str] = []
    seen_paths: set[str] = set()
    for url in found_urls:
        path = urlparse(url).path
        if path != old_path and path not in seen_paths:
            unique_urls.append(url)
            seen_paths.add(path)

    if not unique_urls:
        print("    [URL Fallback] All found URLs match the expired URL")
        return None

    new_url = unique_urls[0]
    print(f"    [URL Fallback] Found new detail URL: {new_url}")
    return new_url
