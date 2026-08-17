"""Backfill missing publishedAt dates for existing press articles.

Reads articles where publishedAt IS NULL and attempts to extract dates from:
1. Stored bodyText (using parser date extraction patterns)
2. If bodyText is empty, re-fetches the article page

Usage:
    python backfill_dates.py [--dry-run]
"""

import argparse
import asyncio
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Optional

import psycopg2.extras

from db import get_connection, release_connection
from press_parsers import PressSourceParser, GenericPressParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_articles_without_date() -> list[dict]:
    """Fetch articles where publishedAt is NULL."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    id,
                    title,
                    "articleUrl" as article_url,
                    "bodyText" as body_text,
                    "sourceId" as source_id
                FROM press_article
                WHERE "publishedAt" IS NULL
                  AND "deletedAt" IS NULL
                ORDER BY "createdAt" DESC
            """)
            return [dict(row) for row in cur.fetchall()]
    finally:
        release_connection(conn)


def update_article_date(article_id: str, published_at: str) -> None:
    """Update the publishedAt field for an article."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE press_article
                SET "publishedAt" = %s,
                    "updatedAt" = %s
                WHERE id = %s
            """, (
                published_at,
                datetime.now(timezone.utc),
                article_id,
            ))
            conn.commit()
    finally:
        release_connection(conn)


def try_extract_date_from_body(body_text: str) -> Optional[str]:
    """Try to find a publication date in the body text.

    Looks for date patterns near the beginning of the text,
    which is where dates typically appear in press releases.
    """
    if not body_text:
        return None

    parser = GenericPressParser()

    # Check the first 500 characters for a date pattern
    head = body_text[:500]
    match = re.search(r"\d{4}[年./\-]\d{1,2}[月./\-]\d{1,2}日?", head)
    if match:
        return parser._parse_date_text(match.group(0))

    return None


def try_extract_date_from_html(html: str) -> Optional[str]:
    """Try to extract published date from stored HTML/body using article page strategies."""
    parser = GenericPressParser()
    return parser._extract_date_from_article_page(html)


async def backfill_with_refetch(articles: list[dict]) -> dict:
    """Re-fetch article pages that have no date and no body text to extract from."""
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

    results = {"updated": 0, "failed": 0, "skipped": 0}

    if not articles:
        return results

    logger.info(f"Re-fetching {len(articles)} articles to extract dates...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="ja-JP",
        )
        page = await context.new_page()

        parser = GenericPressParser()

        for article in articles:
            try:
                await page.goto(
                    article["article_url"],
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
                await page.wait_for_timeout(1500)
                html = await page.content()

                date = parser._extract_date_from_article_page(html)
                if date:
                    update_article_date(article["id"], date)
                    results["updated"] += 1
                    logger.info(f"  Updated: {article['title'][:50]} → {date}")
                else:
                    results["failed"] += 1
                    logger.debug(f"  No date found: {article['title'][:50]}")

                await asyncio.sleep(1.5)

            except (PlaywrightTimeout, Exception) as e:
                results["failed"] += 1
                logger.warning(f"  Error fetching {article['article_url']}: {e}")

        await context.close()
        await browser.close()

    return results


def main():
    parser = argparse.ArgumentParser(description="Backfill missing press article dates")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be updated")
    parser.add_argument("--no-refetch", action="store_true", help="Skip re-fetching pages, only use stored body text")
    args = parser.parse_args()

    articles = get_articles_without_date()
    logger.info(f"Found {len(articles)} articles without publishedAt date")

    if not articles:
        logger.info("Nothing to do.")
        return

    updated = 0
    need_refetch = []

    # Phase 1: Try to extract from stored body text
    for article in articles:
        date = try_extract_date_from_body(article.get("body_text", ""))
        if date:
            if args.dry_run:
                logger.info(f"  [DRY-RUN] Would update: {article['title'][:50]} → {date}")
            else:
                update_article_date(article["id"], date)
                logger.info(f"  Updated from body: {article['title'][:50]} → {date}")
            updated += 1
        else:
            need_refetch.append(article)

    logger.info(f"Phase 1 complete: {updated} dates extracted from body text")
    logger.info(f"  {len(need_refetch)} articles still need date extraction")

    if args.dry_run or args.no_refetch or not need_refetch:
        logger.info("Done.")
        return

    # Phase 2: Re-fetch article pages for remaining
    results = asyncio.run(backfill_with_refetch(need_refetch))
    logger.info(
        f"Phase 2 complete: {results['updated']} updated, "
        f"{results['failed']} failed, {results['skipped']} skipped"
    )
    logger.info(f"Total updated: {updated + results['updated']}")


if __name__ == "__main__":
    main()
