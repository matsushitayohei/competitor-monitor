"""URL fallback module for expired property detail pages.

When a detail page returns 404, this module fetches a new property detail URL
from the corresponding listing page of the same service.
"""

import re
from urllib.parse import urljoin, urlparse
from typing import Optional

from playwright.async_api import async_playwright


# Service-specific selectors for property detail links on listing pages
SERVICE_DETAIL_LINK_SELECTORS = {
    "suumo": [
        'a.cassetteitem_other-linktext',
        'a[href*="/chintai/jnc_"]',
        'a[href*="/ms/jnc_"]',
        'a[href*="/chukoikkodate/"]',
        '.cassetteitem a[href*="/jnc_"]',
        '.property_unit a[href*="nc_"]',
    ],
    "athome": [
        'a[href*="/chintai/"]',
        'a[href*="/mansion/"]',
        '.property-list a[href*="/detail/"]',
        '.item a[href*="/detail/"]',
        '.p-property a[href]',
    ],
    "canary": [
        'a[href*="/rooms/"]',
        'a[href*="/room/"]',
        'a[href*="/property/"]',
        '.room-card a[href]',
        '.property-card a[href]',
    ],
}

# URL patterns that indicate a property detail page (not list, not top)
DETAIL_URL_PATTERNS = {
    "suumo": [
        r"/chintai/jnc_\d+",
        r"/ms/jnc_\d+",
        r"/chukoikkodate/.+/nc_",
        r"/library/.+/sc_",
    ],
    "athome": [
        r"/chintai/\d+",
        r"/mansion/\d+",
        r"/detail/\d+",
    ],
    "canary": [
        r"/rooms/[a-zA-Z0-9\-]+",
        r"/room/[a-zA-Z0-9\-]+",
        r"/property/[a-zA-Z0-9\-]+",
    ],
}


def _identify_service(url: str) -> Optional[str]:
    """Identify the service from a URL."""
    domain = urlparse(url).netloc.lower()
    if "suumo" in domain:
        return "suumo"
    elif "athome" in domain:
        return "athome"
    elif "canary" in domain or "カナリー" in domain:
        return "canary"
    return None


def _is_detail_url(url: str, service: str) -> bool:
    """Check if a URL looks like a property detail page for the service."""
    patterns = DETAIL_URL_PATTERNS.get(service, [])
    for pattern in patterns:
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
        service_name: Service identifier (suumo, athome, canary).
        old_detail_url: The expired URL (to avoid returning the same one).
        viewport_width: Browser viewport width.

    Returns:
        A new detail page URL, or None if no suitable URL was found.
    """
    service_key = service_name.lower()
    selectors = SERVICE_DETAIL_LINK_SELECTORS.get(service_key, [])

    if not selectors:
        print(f"    [URL Fallback] No selectors configured for service: {service_name}")
        return None

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Use realistic User-Agent to avoid bot detection
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        page = await browser.new_page(viewport={"width": viewport_width, "height": 800}, user_agent=user_agent)

        try:
            response = await page.goto(list_page_url, wait_until="networkidle", timeout=30000)
            if not response or response.status >= 400:
                print(f"    [URL Fallback] Listing page returned HTTP {response.status if response else 'N/A'}")
                await browser.close()
                return None

            await page.wait_for_timeout(2000)

            # Try each selector to find detail links
            found_urls: list[str] = []
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

            await browser.close()

        except Exception as e:
            print(f"    [URL Fallback] Error fetching listing page: {e}")
            await browser.close()
            return None

    if not found_urls:
        print(f"    [URL Fallback] No detail URLs found on listing page")
        return None

    # Remove duplicates, exclude the old URL
    old_path = urlparse(old_detail_url).path
    unique_urls = []
    seen_paths = set()
    for url in found_urls:
        path = urlparse(url).path
        if path != old_path and path not in seen_paths:
            unique_urls.append(url)
            seen_paths.add(path)

    if not unique_urls:
        print(f"    [URL Fallback] All found URLs match the expired URL")
        return None

    # Return the first unique detail URL found
    new_url = unique_urls[0]
    print(f"    [URL Fallback] Found new detail URL: {new_url}")
    return new_url
