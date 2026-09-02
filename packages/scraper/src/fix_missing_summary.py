#!/usr/bin/env python3
"""One-shot script to recover body_text and generate summary for articles
that are stuck with an empty body and no summary, regardless of classification status.

These are articles that:
- Were classified as relevant/irrelevant without a body (edge case), OR
- Have classification="pending" with empty body (normal stuck case)
- Either way, summary is NULL

Usage:
    python packages/scraper/src/fix_missing_summary.py [--dry-run]

For each article with empty bodyText and null summary:
1. Re-fetches the article page via httpx
2. Parses body text with the appropriate parser
3. Runs classification + summarization
4. Updates DB (bodyText, classification, relevanceCategory, summary)
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "analyzer", "src"))

import httpx
from bs4 import BeautifulSoup

from press_db import (
    get_pending_articles,
    update_article_body,
    update_article_classification,
    update_article_summary,
)
from press_parsers import get_parser_for_source
from press_classifier import classify_press_article
from press_summarizer import summarize_press_article
from constants import USER_AGENT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}


def get_articles_needing_summary() -> list[dict]:
    """Fetch articles that have no summary and either empty body or pending status.

    Covers two stuck states:
    1. classification='pending' + empty body  (body fetch failed at scrape time)
    2. Any classification + empty body + null summary  (classified without body, edge case)
    """
    import psycopg2.extras
    from db import get_connection, release_connection

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    pa.id,
                    pa."sourceId" as source_id,
                    pa.title,
                    pa."articleUrl" as article_url,
                    pa."publishedAt" as published_at,
                    pa."bodyText" as body_text,
                    pa.classification,
                    pa."relevanceCategory" as relevance_category,
                    ps.name as source_name
                FROM press_article pa
                JOIN press_source ps ON pa."sourceId" = ps.id
                WHERE pa."deletedAt" IS NULL
                  AND pa.summary IS NULL
                  AND (
                      pa."bodyText" IS NULL
                      OR pa."bodyText" = ''
                  )
                ORDER BY pa."createdAt" ASC
            """)
            return [dict(row) for row in cur.fetchall()]
    finally:
        release_connection(conn)


async def fetch_body_via_httpx(url: str) -> str:
    """Fetch article page HTML via httpx (no JS execution)."""
    async with httpx.AsyncClient(
        headers=_HEADERS,
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        response = await client.get(url)

    if response.status_code >= 400:
        raise Exception(f"HTTP {response.status_code}: {url}")
    return response.text


def extract_body_from_html(html: str, source_name: str) -> str:
    """Extract body text from article HTML using source-specific parser."""
    parser = get_parser_for_source(source_name)
    return parser.parse_article_body(html)


async def recover_article(article: dict, dry_run: bool = False) -> bool:
    """Attempt to recover body_text and generate summary for one article.

    Returns True if recovery succeeded.
    """
    article_id = article["id"]
    title = article.get("title", "")
    url = article.get("article_url", "")
    source_name = article.get("source_name", "")

    logger.info(f"Recovering: '{title[:60]}' ({url})")

    # Step 1: Fetch article page
    try:
        html = await fetch_body_via_httpx(url)
    except Exception as e:
        logger.warning(f"  Fetch failed: {e}")
        return False

    # Step 2: Extract body text
    body_text = extract_body_from_html(html, source_name)
    if not body_text or not body_text.strip():
        logger.warning(f"  Body extraction returned empty text.")
        return False

    logger.info(f"  Body extracted: {len(body_text)} chars")

    if dry_run:
        logger.info(f"  [DRY RUN] Would update body and run classify/summarize.")
        return True

    # Step 3: Persist body_text and reset to pending so normal pipeline picks up
    update_article_body(article_id, body_text)

    # Step 4: Classify
    result = classify_press_article(title, body_text)
    if result.category == "classification_failed":
        logger.warning(f"  Classification failed. Article stays pending.")
        return False

    classification = "relevant" if result.is_relevant else "irrelevant"
    update_article_classification(
        article_id=article_id,
        classification=classification,
        category=result.category,
        needs_manual_review=result.needs_manual_review,
    )
    logger.info(
        f"  Classified: {classification} (category={result.category}, "
        f"needs_review={result.needs_manual_review})"
    )

    # Step 5: Summarize if relevant
    if classification == "relevant":
        summary = summarize_press_article(body_text, result.category or "other")
        if summary:
            update_article_summary(article_id, summary)
            logger.info(f"  Summary saved ({len(summary)} chars): {summary[:80]}...")
            return True
        else:
            logger.warning(f"  Summarizer returned empty string.")
            update_article_classification(
                article_id=article_id,
                classification=classification,
                category=result.category,
                needs_manual_review=True,
            )
            return False
    else:
        logger.info(f"  Article classified as irrelevant. No summary needed.")
        return True


async def main() -> None:
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        logger.info("=== DRY RUN MODE (no DB writes) ===")

    # Fetch articles with empty body and no summary
    target = get_articles_needing_summary()

    logger.info(
        f"Articles with empty body and no summary: {len(target)}"
    )

    if not target:
        logger.info("Nothing to recover.")
        return

    recovered = 0
    failed = 0
    for article in target:
        success = await recover_article(article, dry_run=dry_run)
        if success:
            recovered += 1
        else:
            failed += 1
        await asyncio.sleep(1.0)  # polite delay

    logger.info(
        f"\nRecovery complete: {recovered} succeeded, {failed} failed"
    )


if __name__ == "__main__":
    asyncio.run(main())
