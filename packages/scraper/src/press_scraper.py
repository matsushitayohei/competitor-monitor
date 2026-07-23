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
"""

import asyncio
import logging
from datetime import datetime, timezone

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeout,
    Page,
    BrowserContext,
)
from playwright_stealth import stealth_async

from press_db import get_active_press_sources, article_exists, save_press_article
from press_parsers import get_parser_for_source

logger = logging.getLogger(__name__)

# 60 second timeout per HTTP request (in milliseconds for Playwright)
TIMEOUT_MS = 60_000

# 2 second delay between requests to be polite to target sites
INTER_REQUEST_DELAY = 2.0

# Maximum retries for a source page fetch
MAX_RETRIES = 2


async def fetch_article_body(page: Page, url: str, parser) -> str:
    """Navigate to an article page and extract body text using the parser.

    Args:
        page: Playwright page instance.
        url: The article URL to navigate to.
        parser: Site-specific parser with parse_article_body method.

    Returns:
        Extracted body text string. Returns empty string on failure.
    """
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        if response and response.status >= 400:
            logger.warning(
                f"HTTP {response.status} when fetching article body: {url}"
            )
            return ""

        # Wait briefly for dynamic content
        await page.wait_for_timeout(2000)

        html = await page.content()
        body_text = parser.parse_article_body(html)
        return body_text

    except PlaywrightTimeout:
        logger.warning(f"Timeout fetching article body: {url}")
        return ""
    except Exception as e:
        logger.warning(f"Error fetching article body {url}: {e}")
        return ""


async def _fetch_source_page(page: Page, source_url: str) -> str:
    """Fetch a press source listing page with retry and fallback strategies.

    Tries multiple wait strategies to handle slow-loading corporate sites
    and aggressive bot detection (HTTP 403).

    Args:
        page: Playwright page instance.
        source_url: URL of the press release listing page.

    Returns:
        HTML content of the page.

    Raises:
        Exception: If all retry attempts fail.
    """
    wait_strategies = ["domcontentloaded", "load", "networkidle"]

    last_error = None
    for attempt, wait_until in enumerate(wait_strategies[:MAX_RETRIES + 1]):
        try:
            if attempt > 0:
                # Add longer delay between retries to appear more human-like
                await asyncio.sleep(5.0 + attempt * 2.0)
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
                await page.wait_for_timeout(5000)
                # Check if page content loaded after JS challenge
                html = await page.content()
                if len(html) > 1000 and "403" not in html[:200]:
                    logger.info(
                        f"  JS challenge resolved after wait (content: {len(html)} chars)"
                    )
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

    # Fetch the press release listing page with retry logic
    html = await _fetch_source_page(page, source_url)

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
            continue

        # Inter-request delay before fetching article body
        await asyncio.sleep(INTER_REQUEST_DELAY)

        # Fetch article body text
        body_text = await fetch_article_body(page, article_url, parser)

        # Save new article to database
        article_data = {
            "source_id": source_id,
            "title": article_title,
            "article_url": article_url,
            "published_at": article.get("published_at"),
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
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Sec-Ch-Ua": '"Chromium";v="126", "Not A(Brand";v="8", "Google Chrome";v="126"',
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
            # Apply stealth scripts to bypass bot detection (webdriver flag, etc.)
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
