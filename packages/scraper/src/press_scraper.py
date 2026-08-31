"""Press release scraper main module.

Fetches press release pages from active sources using Playwright,
extracts articles using site-specific parsers, checks for duplicates,
and saves new articles to the database.

Key behaviors:
- 60s timeout per HTTP request (extended from 30s for slow corporate sites)
- 2s inter-request delay between requests
- Errors per source are handled independently (one failure doesn't block others)
- Zero new articles is logged as success, not error
- Stealth mode: playwright-stealth to bypass bot detection (webdriver flag, etc.)
- Retry with alternative wait strategy on timeout
- RSS fallback: sources with known RSS feeds use httpx on Playwright 403
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import xml.etree.ElementTree as ET

import httpx

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeout,
    Page,
    BrowserContext,
)
from playwright_stealth import stealth_async

from press_db import (
    get_active_press_sources,
    article_exists,
    save_press_article,
    get_incomplete_article,
    update_article_body,
)
from press_parsers import get_parser_for_source
from constants import USER_AGENT

logger = logging.getLogger(__name__)

# 60 second timeout per HTTP request (in milliseconds for Playwright)
TIMEOUT_MS = 60_000

# 2 second delay between requests to be polite to target sites
INTER_REQUEST_DELAY = 2.0

# Maximum retries for a source page fetch
MAX_RETRIES = 2

# RSS/Atom feed URLs for sources where Playwright triggers bot detection (403).
# Key: source name substring (lowercase), Value: RSS feed URL.
# When Playwright returns 403 for a source whose name matches a key here,
# the scraper falls back to fetching via httpx + parsing the RSS feed directly.
RSS_FALLBACK_FEEDS: dict[str, str] = {
    "suumo-press": "https://www.recruit.co.jp/newsroom/pressrelease/pressrelease-cat/c-housing/feed/",
    "suumo-data": "https://www.recruit.co.jp/newsroom/data/data-cat/c-housing/feed/",
    "ielove-press": "https://www.ielove-group.jp/news/feed/",
}

# httpx headers to use for RSS / plain HTTP fetching (no bot-detection overhead)
_HTTPX_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml,application/atom+xml,text/xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}


def _rss_feed_url_for_source(source_name: str) -> Optional[str]:
    """Return the RSS fallback feed URL for a source name, or None."""
    name_lower = source_name.lower()
    # Exact match first
    if name_lower in RSS_FALLBACK_FEEDS:
        return RSS_FALLBACK_FEEDS[name_lower]
    # Substring match
    for key, url in RSS_FALLBACK_FEEDS.items():
        if key in name_lower:
            return url
    return None


def _rss_to_html(rss_xml: str) -> str:
    """Convert RSS/Atom XML to a simple HTML structure parseable by existing parsers.

    Generates an HTML page that resembles a news listing with <article> elements
    containing the title, link, and publication date from the feed.

    Args:
        rss_xml: Raw XML content of an RSS or Atom feed.

    Returns:
        HTML string, or empty string if parsing fails.
    """
    try:
        root = ET.fromstring(rss_xml)
    except ET.ParseError as e:
        logger.warning(f"RSS XML parse error: {e}")
        return ""

    # Detect feed type
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    is_atom = root.tag == "{http://www.w3.org/2005/Atom}feed" or root.tag.endswith("}feed")

    items: list[dict] = []

    if is_atom:
        entries = root.findall("{http://www.w3.org/2005/Atom}entry") or root.findall("entry")
        for entry in entries:
            title_el = entry.find("{http://www.w3.org/2005/Atom}title") or entry.find("title")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""

            link_el = entry.find("{http://www.w3.org/2005/Atom}link") or entry.find("link")
            link = ""
            if link_el is not None:
                link = link_el.get("href", "") or link_el.text or ""

            date_el = (
                entry.find("{http://www.w3.org/2005/Atom}published")
                or entry.find("{http://www.w3.org/2005/Atom}updated")
                or entry.find("published")
                or entry.find("updated")
            )
            date = date_el.text.strip() if date_el is not None and date_el.text else ""

            if title and link:
                items.append({"title": title, "link": link.strip(), "date": date})
    else:
        # RSS 2.0
        channel = root.find("channel")
        feed_items = channel.findall("item") if channel is not None else root.findall("item")
        for item in feed_items:
            title_el = item.find("title")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""

            link_el = item.find("link")
            link = link_el.text.strip() if link_el is not None and link_el.text else ""
            if not link:
                guid_el = item.find("guid")
                if guid_el is not None and guid_el.text and guid_el.text.startswith("http"):
                    link = guid_el.text.strip()

            date_el = item.find("pubDate") or item.find("dc:date")
            date = date_el.text.strip() if date_el is not None and date_el.text else ""

            if title and link:
                items.append({"title": title, "link": link, "date": date})

    if not items:
        return ""

    # Build minimal HTML
    article_blocks = []
    for it in items:
        article_blocks.append(
            f'<article class="news-item">'
            f'<time datetime="{it["date"]}">{it["date"]}</time>'
            f'<a href="{it["link"]}">{it["title"]}</a>'
            f"</article>"
        )

    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        "<body>"
        + "\n".join(article_blocks)
        + "</body></html>"
    )
    logger.info(f"RSS feed converted to HTML: {len(items)} items")
    return html


async def _fetch_via_httpx(feed_url: str, source_name: str) -> str:
    """Fetch a URL using httpx (plain HTTP, no JS execution).

    Used as fallback when Playwright is blocked by bot detection.
    Handles both RSS feeds and regular HTML pages.

    Args:
        feed_url: URL to fetch.
        source_name: For logging.

    Returns:
        HTML string ready for parsing, or empty string on failure.

    Raises:
        Exception: If the HTTP request fails (non-2xx, timeout, etc.).
    """
    async with httpx.AsyncClient(
        headers=_HTTPX_HEADERS,
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        response = await client.get(feed_url)

    if response.status_code >= 400:
        raise Exception(
            f"HTTP {response.status_code} from RSS/httpx fallback: {feed_url}"
        )

    content_type = response.headers.get("content-type", "")
    raw = response.text

    # Convert RSS/Atom to HTML if needed
    if (
        "xml" in content_type
        or "rss" in content_type
        or "atom" in content_type
        or raw.lstrip().startswith("<?xml")
        or "<rss" in raw[:500]
        or "<feed" in raw[:500]
    ):
        logger.info(f"  [{source_name}] RSS/Atom feed detected — converting to HTML")
        html = _rss_to_html(raw)
        if not html:
            raise Exception(f"Failed to parse RSS/Atom feed from: {feed_url}")
        return html

    # Plain HTML
    return raw


async def fetch_article_body(page: Page, url: str, parser) -> tuple[str, str | None]:
    """Navigate to an article page and extract body text and date using the parser.

    For sources with known 403 issues (recruit.co.jp, ielove-group.jp), falls back
    to httpx when Playwright receives a 403 response.

    Args:
        page: Playwright page instance.
        url: The article URL to navigate to.
        parser: Site-specific parser with parse_article_body method.

    Returns:
        Tuple of (body_text, published_at_iso_string_or_None).
        Returns ("", None) on failure.
    """
    html = ""
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        if response and response.status == 403:
            # Try httpx fallback for bot-detection-protected sites
            logger.info(f"  Article body 403, trying httpx fallback: {url}")
            try:
                html = await _fetch_article_body_via_httpx(url)
            except Exception as e:
                logger.warning(f"  httpx fallback also failed for article body: {e}")
                return ("", None)
        elif response and response.status >= 400:
            logger.warning(
                f"HTTP {response.status} when fetching article body: {url}"
            )
            return ("", None)
        else:
            # Wait briefly for dynamic content
            await page.wait_for_timeout(2000)
            html = await page.content()

    except PlaywrightTimeout:
        logger.warning(f"Timeout fetching article body: {url}")
        return ("", None)
    except Exception as e:
        logger.warning(f"Error fetching article body {url}: {e}")
        return ("", None)

    if not html:
        return ("", None)

    body_text = parser.parse_article_body(html)
    # Also try to extract date from the article page
    published_at = parser._extract_date_from_article_page(html)
    return (body_text, published_at)


async def _fetch_article_body_via_httpx(url: str) -> str:
    """Fetch an individual article page via httpx (bypasses bot detection).

    Args:
        url: Article URL to fetch.

    Returns:
        HTML string.

    Raises:
        Exception: On HTTP error or network failure.
    """
    article_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }
    async with httpx.AsyncClient(
        headers=article_headers,
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        response = await client.get(url)

    if response.status_code >= 400:
        raise Exception(f"HTTP {response.status_code} from httpx article fetch: {url}")

    return response.text


async def _fetch_source_page(page: Page, source_url: str, source_name: str = "") -> str:
    """Fetch a press source listing page with retry and fallback strategies.

    Tries multiple wait strategies to handle slow-loading corporate sites
    and aggressive bot detection (HTTP 403).

    When all Playwright attempts return 403 and an RSS feed is registered for
    the source, falls back to fetching the feed via httpx and converting it to
    HTML so the existing parsers can process it without changes.

    Args:
        page: Playwright page instance.
        source_url: URL of the press release listing page.
        source_name: Source name for RSS fallback lookup and logging.

    Returns:
        HTML content of the page.

    Raises:
        Exception: If all retry attempts fail.
    """
    wait_strategies = ["domcontentloaded", "load", "networkidle"]

    last_error = None
    got_403 = False
    for attempt, wait_until in enumerate(wait_strategies[:MAX_RETRIES + 1]):
        try:
            if attempt > 0:
                # Add longer delay between retries to appear more human-like
                await asyncio.sleep(5.0 + attempt * 3.0)
                logger.info(
                    f"  Retry {attempt}/{MAX_RETRIES} with wait_until='{wait_until}'"
                )

            response = await page.goto(
                source_url, wait_until=wait_until, timeout=TIMEOUT_MS
            )

            if response and response.status == 403:
                # Wait longer for JS challenge pages (Cloudflare, WAF, etc.)
                logger.warning(
                    f"  HTTP 403 on attempt {attempt + 1}, "
                    f"waiting for JS challenge resolution..."
                )
                got_403 = True
                # Some WAFs set cookies after initial 403, then redirect on reload
                await page.wait_for_timeout(8000)
                # Check if page content loaded after JS challenge
                html = await page.content()
                if len(html) > 1000 and "403" not in html[:200]:
                    logger.info(
                        f"  JS challenge resolved after wait (content: {len(html)} chars)"
                    )
                    return html

                # Try reloading after cookies are set
                if attempt < MAX_RETRIES:
                    logger.info(f"  Attempting page reload after cookie set...")
                    await page.wait_for_timeout(3000)
                    response = await page.reload(wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                    if response and response.status == 200:
                        html = await page.content()
                        if len(html) > 1000:
                            logger.info(f"  Reload successful after cookie set (content: {len(html)} chars)")
                            return html

                last_error = Exception(
                    f"HTTP 403 from press source page: {source_url}"
                )
                continue

            if response and response.status >= 400:
                raise Exception(
                    f"HTTP {response.status} from press source page: {source_url}"
                )

            # Wait for dynamic content to load
            await page.wait_for_timeout(2000)

            html = await page.content()
            # Verify we got actual content (not a blank/error page)
            if len(html) > 500:
                return html

            logger.warning(
                f"  Page content too short ({len(html)} chars) on attempt {attempt + 1}"
            )
            last_error = Exception(
                f"Page content too short from: {source_url}"
            )

        except PlaywrightTimeout:
            last_error = PlaywrightTimeout(
                f"Timeout ({TIMEOUT_MS // 1000}s) accessing {source_url}"
            )
            logger.warning(
                f"  Timeout on attempt {attempt + 1} with wait_until='{wait_until}'"
            )
            continue

    # --- RSS / httpx fallback for persistent 403 ---
    # Some corporate sites (e.g. recruit.co.jp, ielove-group.jp) reject headless
    # browsers but serve their RSS/Atom feeds without bot detection. When all
    # Playwright attempts resulted in 403, try the registered RSS feed URL.
    if got_403 and source_name:
        rss_url = _rss_feed_url_for_source(source_name)
        if rss_url:
            logger.info(
                f"  All Playwright attempts 403 — falling back to RSS feed: {rss_url}"
            )
            try:
                html = await _fetch_via_httpx(rss_url, source_name)
                logger.info(
                    f"  RSS fallback successful for {source_name} "
                    f"(content: {len(html)} chars)"
                )
                return html
            except Exception as rss_err:
                logger.warning(f"  RSS fallback also failed: {rss_err}")
                # Raise RSS error so the Slack notification shows the real cause
                # (e.g. "HTTP 403 from RSS/httpx fallback") instead of the
                # original Playwright 403 which misleads the reader into thinking
                # no fallback was attempted.
                raise Exception(
                    f"Playwright 403 + RSS fallback failed ({rss_url}): {rss_err}"
                ) from rss_err

    # All attempts failed
    raise last_error


async def scrape_press_source(page: Page, source: dict) -> list[dict]:
    """Scrape a single press source, return list of newly saved articles.

    Fetches the source's press release listing page, extracts article metadata,
    checks each article for duplicates, fetches body text for new articles,
    and saves them to the database.

    Args:
        page: Playwright page instance.
        source: Dict with keys: id, name, url.

    Returns:
        List of newly saved article dicts (with keys: id, title, url).
    """
    source_id = source["id"]
    source_name = source["name"]
    source_url = source["url"]

    logger.info(f"Scraping source: {source_name} ({source_url})")

    # Get the appropriate parser for this source
    parser = get_parser_for_source(source_name)

    # Set Referer to the source's top page to mimic natural navigation
    from urllib.parse import urlparse
    parsed = urlparse(source_url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    await page.set_extra_http_headers({"Referer": referer})

    # Fetch the press release listing page with retry logic
    html = await _fetch_source_page(page, source_url, source_name)

    # Extract article list from the listing page
    articles = parser.parse_article_list(html, base_url=source_url)
    logger.info(f"  Found {len(articles)} articles on listing page for {source_name}")

    new_articles: list[dict] = []

    for article in articles:
        article_url = article.get("url", "")
        article_title = article.get("title", "")

        if not article_url or not article_title:
            continue

        # Filter out non-article pages (nav links, static pages, etc.)
        if not parser._is_valid_article(article_title, article_url, source_url):
            logger.debug(f"  Skipped non-article: {article_title[:40]}")
            continue

        # Check for duplicates
        if article_exists(source_id, article_url):
            # An article may already exist but have an empty body (a previous
            # body fetch failed). Recover it by re-fetching the body instead of
            # skipping, so it can be classified/summarized on the next run.
            incomplete = get_incomplete_article(source_id, article_url)
            if incomplete:
                await asyncio.sleep(INTER_REQUEST_DELAY)
                body_text, page_published_at = await fetch_article_body(
                    page, article_url, parser
                )
                if body_text and body_text.strip():
                    published_at = article.get("published_at") or page_published_at
                    update_article_body(
                        incomplete["id"], body_text, published_at
                    )
                    logger.info(
                        f"  Recovered body for existing article: {article_title[:60]}"
                    )
                else:
                    logger.warning(
                        f"  Body still empty on re-fetch, will retry next run: "
                        f"{article_title[:60]}"
                    )
            continue

        # Inter-request delay before fetching article body
        await asyncio.sleep(INTER_REQUEST_DELAY)

        # Fetch article body text and attempt date extraction from article page
        body_text, page_published_at = await fetch_article_body(page, article_url, parser)

        # Use listing page date if available; otherwise use article page date
        published_at = article.get("published_at") or page_published_at

        # Save new article to database
        article_data = {
            "source_id": source_id,
            "title": article_title,
            "article_url": article_url,
            "published_at": published_at,
            "body_text": body_text,
        }

        article_id = save_press_article(article_data)

        new_articles.append({
            "id": article_id,
            "title": article_title,
            "url": article_url,
        })

        logger.info(f"  Saved new article: {article_title[:60]}")

    # Log zero-new-article scrapes as success (not error) per Requirements 2.7
    if not new_articles:
        logger.info(
            f"  No new articles found for {source_name} (successful scrape, no new content)"
        )

    return new_articles


async def run_press_scraper() -> dict:
    """Main entry point: scrape all active sources and return summary stats.

    Processes each source independently - one source failure doesn't block others.

    Returns:
        Dict with keys: total_sources, new_articles, errors (list of error dicts).
    """
    sources = get_active_press_sources()
    results = {
        "total_sources": len(sources),
        "new_articles": 0,
        "errors": [],
    }

    if not sources:
        logger.info("No active press sources found. Skipping scrape.")
        return results

    logger.info(f"Starting press scraper with {len(sources)} active sources")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
            ],
        )
        # Use realistic browser context to avoid bot detection
        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Cache-Control": "no-cache",
                "Sec-Ch-Ua": '"Google Chrome";v="151", "Chromium";v="151", "Not/A)Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        # Create a fresh page per source to avoid cookie/session cross-contamination
        for source in sources:
            page = await context.new_page()
            # Apply playwright-stealth to bypass bot detection comprehensively
            await stealth_async(page)
            try:
                new_articles = await scrape_press_source(page, source)
                results["new_articles"] += len(new_articles)
            except PlaywrightTimeout as e:
                error_msg = f"Timeout ({TIMEOUT_MS // 1000}s) accessing {source['url']}"
                logger.error(f"Failed to scrape {source['name']}: {error_msg}")
                results["errors"].append({
                    "source": source["name"],
                    "url": source["url"],
                    "error": error_msg,
                })
            except Exception as e:
                logger.error(f"Failed to scrape {source['name']}: {e}")
                results["errors"].append({
                    "source": source["name"],
                    "url": source["url"],
                    "error": str(e),
                })
            finally:
                await page.close()

            # Inter-request delay between sources
            await asyncio.sleep(INTER_REQUEST_DELAY)

        await context.close()
        await browser.close()

    logger.info(
        f"Press scraper complete. Sources: {results['total_sources']}, "
        f"New articles: {results['new_articles']}, "
        f"Errors: {len(results['errors'])}"
    )

    return results
