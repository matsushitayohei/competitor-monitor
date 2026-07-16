#!/usr/bin/env python3
"""Press release monitoring pipeline main entry point.

Orchestrates: scrape → classify → summarize → notify
Run via: python packages/scraper/src/press_main.py

Pipeline flow for each source:
1. Scraper fetches page, extracts articles, saves new ones with classification="pending"
2. For each pending article: classify → update DB
3. If classified as relevant: summarize → update DB
4. If summarized: notify via Slack

Each source is processed independently - one failure does not stop others.
"""

import asyncio
import logging
import os
import sys

# Add paths for imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "analyzer", "src"))

from press_scraper import run_press_scraper
from press_classifier import classify_press_article
from press_summarizer import summarize_press_article
from press_notifier import notify_press_article
from press_db import (
    get_pending_articles,
    update_article_classification,
    update_article_summary,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def notify_source_failure(error: dict) -> None:
    """Send a Slack notification for a source scraping failure.

    Args:
        error: Dict with keys: source (name), url, error (reason).
    """
    from press_notifier import get_webhook_url, _post_to_slack

    webhook_url = get_webhook_url()
    if not webhook_url:
        logger.warning(
            "PRESS_SLACK_WEBHOOK_URL not configured. Cannot send source failure notification."
        )
        return

    source_name = error.get("source", "不明")
    source_url = error.get("url", "")
    error_reason = error.get("error", "不明なエラー")

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ プレスリリース取得失敗",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*ソース:* {source_name}\n"
                        f"*URL:* {source_url}\n"
                        f"*原因:* {error_reason}"
                    ),
                },
            },
        ]
    }

    success = await _post_to_slack(webhook_url, payload)
    if success:
        logger.info(f"Source failure notification sent for: {source_name}")
    else:
        logger.error(f"Failed to send source failure notification for: {source_name}")


async def process_pending_articles() -> dict:
    """Process all pending articles: classify → summarize → notify.

    Returns:
        Dict with stats: classified, summarized, notified, errors.
    """
    stats = {
        "classified": 0,
        "summarized": 0,
        "notified": 0,
        "errors": 0,
    }

    pending_articles = get_pending_articles()
    logger.info(f"Processing {len(pending_articles)} pending articles")

    for article in pending_articles:
        article_id = article["id"]
        title = article.get("title", "")
        body = article.get("body_text", "") or ""

        try:
            # Step 1: Classify
            result = classify_press_article(title, body)

            classification = "relevant" if result.is_relevant else "irrelevant"
            if result.category == "classification_failed":
                classification = "classification_failed"

            update_article_classification(
                article_id=article_id,
                classification=classification,
                category=result.category,
                needs_manual_review=result.needs_manual_review,
            )
            stats["classified"] += 1
            logger.info(
                f"  Classified '{title[:50]}' → {classification}"
                f" (category={result.category})"
            )

            # Step 2: Summarize (only if relevant)
            if classification == "relevant":
                summary = summarize_press_article(body, result.category or "other")
                if summary:
                    update_article_summary(article_id, summary)
                    stats["summarized"] += 1
                    logger.info(f"  Summarized '{title[:50]}' ({len(summary)} chars)")

                    # Step 3: Notify (only if summarized)
                    notification_data = {
                        "id": article_id,
                        "title": title,
                        "article_url": article.get("article_url", ""),
                        "source_name": article.get("source_name", ""),
                        "published_at": article.get("published_at"),
                        "relevance_category": result.category,
                        "summary": summary,
                    }
                    notified = await notify_press_article(notification_data)
                    if notified:
                        stats["notified"] += 1
                else:
                    # Summarization produced empty result - mark for manual review
                    logger.warning(
                        f"  Empty summary for '{title[:50]}'. "
                        "Marking for manual review."
                    )
                    update_article_classification(
                        article_id=article_id,
                        classification=classification,
                        category=result.category,
                        needs_manual_review=True,
                    )

        except Exception as e:
            stats["errors"] += 1
            logger.error(
                f"  Error processing article '{title[:50]}' (id={article_id}): {e}"
            )
            continue

    return stats


async def main() -> None:
    """Main pipeline entry point.

    Flow:
    1. Run scraper → saves new articles with classification="pending"
    2. Process all pending articles (classify → summarize → notify)
    3. Send failure notifications for sources that failed to scrape
    4. Print summary
    """
    logger.info("=" * 60)
    logger.info("Press Release Monitor Pipeline - Starting")
    logger.info("=" * 60)

    # Step 1: Run scraper
    logger.info("Step 1: Running press release scraper...")
    scraper_results = await run_press_scraper()

    total_sources = scraper_results["total_sources"]
    new_articles = scraper_results["new_articles"]
    scraper_errors = scraper_results["errors"]

    logger.info(
        f"Scraper complete: {total_sources} sources, "
        f"{new_articles} new articles, "
        f"{len(scraper_errors)} errors"
    )

    # Step 2: Process pending articles (classify → summarize → notify)
    logger.info("Step 2: Processing pending articles...")
    process_stats = await process_pending_articles()

    # Step 3: Send failure notifications for sources that failed to scrape
    if scraper_errors:
        logger.info(
            f"Step 3: Sending failure notifications for {len(scraper_errors)} failed sources..."
        )
        for error in scraper_errors:
            try:
                await notify_source_failure(error)
            except Exception as e:
                logger.error(
                    f"Failed to send failure notification for "
                    f"'{error.get('source', 'unknown')}': {e}"
                )
    else:
        logger.info("Step 3: No source failures to report.")

    # Step 4: Print summary
    total_errors = len(scraper_errors) + process_stats["errors"]
    logger.info("=" * 60)
    logger.info("Press Release Monitor Pipeline - Complete")
    logger.info(f"  Total sources processed: {total_sources}")
    logger.info(f"  New articles scraped:    {new_articles}")
    logger.info(f"  Articles classified:     {process_stats['classified']}")
    logger.info(f"  Articles summarized:     {process_stats['summarized']}")
    logger.info(f"  Notifications sent:      {process_stats['notified']}")
    logger.info(f"  Total errors:            {total_errors}")
    logger.info("=" * 60)

    print(
        f"\nPress Release Monitor Complete: "
        f"{total_sources} sources, "
        f"{new_articles} new articles, "
        f"{total_errors} errors"
    )


if __name__ == "__main__":
    asyncio.run(main())
