"""Press release scraper main module.

Fetches press release pages from active sources using Playwright,
extracts articles using site-specific parsers, checks for duplicates,
and saves new articles to the database.

Key behaviors:
- 30s timeout per HTTP request
- 2s inter-request delay between requests
- Errors per source are handled independently (one failure doesn't block others)
- Zero new articles is logged as success, not error
"""

import asyncio
import logging
from datetime import datetime, timezone

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeout,
    Page,
)

from press_db import get_active_press_sources, article_exists, save_press_article
from press_parsers import get_parser_for_source

logger = logging.getLogger(__name__)

# 30 second timeout per HTTP request (in milliseconds for Playwright)
TIMEOUT_MS = 30_000

# 2 second delay between requests to be polite to target sites
INTER_REQUEST_DELAY = 2.0


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
        response = await page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
        if response and response.status >= 400:
            logger.warning(
                f"HTTP {response.status} when fetching article body: {url}"
            )
            return ""

        # Wait briefly for dynamic content
        await page.wait_for_timeout(1000)

        html = await page.content()
        body_text = parser.parse_article_body(html)
        return body_text

    except PlaywrightTimeout:
        logger.warning(f"Timeout fetching article body: {url}")
        return ""
    except Exception as e:
        logger.warning(f"Error fetching article body {url}: {e}")
        return ""


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

    # Fetch the press release listing page
    response = await page.goto(
        source_url, wait_until="networkidle", timeout=TIMEOUT_MS
    )

    if response and response.status >= 400:
        raise Exception(
            f"HTTP {response.status} from press source page: {source_url}"
        )

    # Wait for dynamic content to load
    await page.wait_for_timeout(1000)

    html = await page.content()

    # Extract article list from the listing page
    articles = parser.parse_article_list(html, base_url=source_url)
    logger.info(f"  Found {len(articles)} articles on listing page for {source_name}")

    new_articles: list[dict] = []

    for article in articles:
        article_url = article.get("url", "")
        article_title = article.get("title", "")

        if not article_url or not article_title:
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
        browser = await p.chromium.launch(headless=True)
        # Use realistic User-Agent to avoid bot detection (e.g. athome returns HTTP 405)
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
        page = await browser.new_page(user_agent=user_agent)

        for source in sources:
            try:
                new_articles = await scrape_press_source(page, source)
                results["new_articles"] += len(new_articles)
            except PlaywrightTimeout as e:
                error_msg = f"Timeout (30s) accessing {source['url']}"
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

            # Inter-request delay between sources
            await asyncio.sleep(INTER_REQUEST_DELAY)

        await browser.close()

    logger.info(
        f"Press scraper complete. Sources: {results['total_sources']}, "
        f"New articles: {results['new_articles']}, "
        f"Errors: {len(results['errors'])}"
    )

    return results
