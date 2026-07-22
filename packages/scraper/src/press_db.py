"""Database access module for press release monitoring."""

from datetime import datetime, timezone
from typing import Optional

import uuid

import psycopg2.extras

from db import get_connection, release_connection


def get_active_press_sources() -> list[dict]:
    """Fetch all active press sources (isActive=true AND deletedAt IS NULL)."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    id,
                    name,
                    url,
                    "isActive",
                    "createdAt",
                    "updatedAt"
                FROM press_source
                WHERE "isActive" = true
                  AND "deletedAt" IS NULL
                ORDER BY "createdAt" ASC
            """)
            return [dict(row) for row in cur.fetchall()]
    finally:
        release_connection(conn)


def article_exists(source_id: str, article_url: str) -> bool:
    """Check if an article with the given URL already exists for the source."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1
                FROM press_article
                WHERE "sourceId" = %s
                  AND "articleUrl" = %s
                  AND "deletedAt" IS NULL
                LIMIT 1
            """, (source_id, article_url))
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def save_press_article(data: dict) -> str:
    """Insert a new press_article record with status=pending.

    Args:
        data: dict with keys: source_id, title, article_url, published_at (optional),
              body_text (optional)

    Returns:
        The generated article ID.
    """
    article_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO press_article (
                    id, "sourceId", title, "articleUrl", "publishedAt",
                    "bodyText", classification, "scrapedAt", "createdAt", "updatedAt"
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                article_id,
                data["source_id"],
                data["title"],
                data["article_url"],
                data.get("published_at"),
                data.get("body_text"),
                "pending",
                now,
                now,
                now,
            ))
            conn.commit()
        return article_id
    finally:
        release_connection(conn)


def get_pending_articles(source_id: Optional[str] = None) -> list[dict]:
    """Fetch articles with classification='pending' that need processing.

    Args:
        source_id: If provided, only fetch pending articles for this source.

    Returns:
        List of article dicts with keys: id, source_id, title, article_url,
        published_at, body_text.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if source_id:
                cur.execute("""
                    SELECT
                        pa.id,
                        pa."sourceId" as source_id,
                        pa.title,
                        pa."articleUrl" as article_url,
                        pa."publishedAt" as published_at,
                        pa."bodyText" as body_text,
                        ps.name as source_name
                    FROM press_article pa
                    JOIN press_source ps ON pa."sourceId" = ps.id
                    WHERE pa.classification = 'pending'
                      AND pa."sourceId" = %s
                      AND pa."deletedAt" IS NULL
                    ORDER BY pa."createdAt" ASC
                """, (source_id,))
            else:
                cur.execute("""
                    SELECT
                        pa.id,
                        pa."sourceId" as source_id,
                        pa.title,
                        pa."articleUrl" as article_url,
                        pa."publishedAt" as published_at,
                        pa."bodyText" as body_text,
                        ps.name as source_name
                    FROM press_article pa
                    JOIN press_source ps ON pa."sourceId" = ps.id
                    WHERE pa.classification = 'pending'
                      AND pa."deletedAt" IS NULL
                    ORDER BY pa."createdAt" ASC
                """)
            return [dict(row) for row in cur.fetchall()]
    finally:
        release_connection(conn)


def update_article_classification(
    article_id: str,
    classification: str,
    category: Optional[str],
    needs_manual_review: bool,
) -> None:
    """Update the classification result for a press article.

    Args:
        article_id: The article ID to update.
        classification: "relevant", "irrelevant", or "classification_failed".
        category: Relevance category (e.g. "service_feature") or None.
        needs_manual_review: Whether manual review is needed.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE press_article
                SET classification = %s,
                    "relevanceCategory" = %s,
                    "needsManualReview" = %s,
                    "updatedAt" = %s
                WHERE id = %s
            """, (
                classification,
                category,
                needs_manual_review,
                datetime.now(timezone.utc),
                article_id,
            ))
            conn.commit()
    finally:
        release_connection(conn)


def update_article_summary(article_id: str, summary: str) -> None:
    """Update the AI-generated summary for a press article.

    Args:
        article_id: The article ID to update.
        summary: The generated summary text.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE press_article
                SET summary = %s,
                    "updatedAt" = %s
                WHERE id = %s
            """, (
                summary,
                datetime.now(timezone.utc),
                article_id,
            ))
            conn.commit()
    finally:
        release_connection(conn)
