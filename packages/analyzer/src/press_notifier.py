"""Slack notification module for press release articles.

Sends formatted Block Kit messages to a designated Slack channel via webhook.
Uses SLACK_WEBHOOK_URL environment variable (shared with UI/UX change notifications).
"""

import os
import logging
import asyncio
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

RETRY_DELAY = 30  # seconds


def get_webhook_url() -> Optional[str]:
    """Get the Slack webhook URL from environment variable.
    
    Uses SLACK_WEBHOOK_URL (shared with UI/UX change notifications).
    """
    return os.environ.get("SLACK_WEBHOOK_URL")


def format_slack_message(article: dict) -> dict:
    """Format a Slack Block Kit message for a press article notification.

    Args:
        article: Dict with keys: title, article_url (or articleUrl),
                 source_name (or sourceName), published_at (or publishedAt),
                 relevance_category (or relevanceCategory), summary

    Returns:
        Slack Block Kit message payload as dict.
    """
    title = article.get("title", "タイトル不明")
    article_url = article.get("article_url") or article.get("articleUrl", "")
    source_name = article.get("source_name") or article.get("sourceName", "不明")
    published_at = article.get("published_at") or article.get("publishedAt", "不明")
    category = article.get("relevance_category") or article.get("relevanceCategory", "other")
    summary = article.get("summary", "")

    # Format date for display (handle datetime objects and strings)
    if hasattr(published_at, "strftime"):
        date_str = published_at.strftime("%Y-%m-%d")
    else:
        date_str = str(published_at)[:10] if published_at else "不明"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📰 競合プレスリリース検知",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<{article_url}|{title}>*\nソース: {source_name} | 日付: {date_str} | カテゴリ: {category}",
            },
        },
    ]

    if summary:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"> {summary}",
                },
            }
        )

    return {"blocks": blocks}


async def notify_press_article(article: dict) -> bool:
    """Send notification for a press article to Slack.

    Implements retry logic: on failure, waits 30 seconds and retries once.
    If retry also fails, logs error and returns False without blocking.

    Args:
        article: Dict with article data (title, article_url, source_name, etc.)

    Returns:
        True if notification was sent successfully, False otherwise.
    """
    webhook_url = get_webhook_url()
    if not webhook_url:
        logger.error(
            "PRESS_SLACK_WEBHOOK_URL is not configured. Skipping all press notifications."
        )
        return False

    payload = format_slack_message(article)
    title = article.get("title", "unknown")

    # First attempt
    success = await _post_to_slack(webhook_url, payload)
    if success:
        logger.info(f"Press notification sent successfully: {title}")
        return True

    # Retry after delay
    logger.warning(
        f"Press notification failed for '{title}'. Retrying in {RETRY_DELAY}s..."
    )
    await asyncio.sleep(RETRY_DELAY)

    success = await _post_to_slack(webhook_url, payload)
    if success:
        logger.info(f"Press notification sent successfully on retry: {title}")
        return True

    # Final failure - log and skip
    article_id = article.get("id", "unknown")
    logger.error(
        f"Press notification failed after retry for article '{title}' (id={article_id}). "
        "Skipping notification for this article."
    )
    return False


async def notify_press_articles(articles: list[dict]) -> dict:
    """Send notifications for multiple articles.

    Each article is notified independently - one failure does not block others.

    Args:
        articles: List of article dicts.

    Returns:
        Dict with stats: {"total": int, "success": int, "failed": int, "skipped": int}
    """
    webhook_url = get_webhook_url()
    if not webhook_url:
        logger.error(
            "PRESS_SLACK_WEBHOOK_URL is not configured. Skipping all press notifications."
        )
        return {
            "total": len(articles),
            "success": 0,
            "failed": 0,
            "skipped": len(articles),
        }

    success_count = 0
    failed_count = 0

    for article in articles:
        result = await notify_press_article(article)
        if result:
            success_count += 1
        else:
            failed_count += 1

    return {
        "total": len(articles),
        "success": success_count,
        "failed": failed_count,
        "skipped": 0,
    }


async def _post_to_slack(webhook_url: str, payload: dict) -> bool:
    """Post a payload to the Slack webhook URL.

    Args:
        webhook_url: Slack incoming webhook URL.
        payload: JSON payload to send.

    Returns:
        True if the request succeeded (HTTP 200), False otherwise.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=10,
            )
            if response.status_code == 200:
                return True
            else:
                logger.warning(
                    f"Slack webhook returned status {response.status_code}: {response.text}"
                )
                return False
    except httpx.TimeoutException:
        logger.warning("Slack webhook request timed out")
        return False
    except Exception as e:
        logger.warning(f"Slack webhook request failed: {e}")
        return False
