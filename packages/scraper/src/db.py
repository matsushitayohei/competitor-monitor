"""Database access module for Neon PostgreSQL."""

import os
import json
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras


def get_connection():
    """Get a PostgreSQL connection using the DATABASE_URL environment variable."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(url, sslmode="require")


def get_active_pages() -> list[dict]:
    """Fetch all active monitored pages with their service info."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    mp.id as page_id,
                    mp.url,
                    mp."pageType" as page_type,
                    mp.device,
                    s.id as service_id,
                    s.name as service_name,
                    s."displayName" as service_display_name
                FROM "MonitoredPage" mp
                JOIN "Service" s ON mp."serviceId" = s.id
                WHERE mp."isActive" = true
                  AND mp."deletedAt" IS NULL
                  AND s."isActive" = true
                  AND s."deletedAt" IS NULL
                ORDER BY s.name, mp."pageType", mp.device
            """)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_latest_snapshot(page_id: str) -> Optional[dict]:
    """Get the most recent snapshot for a page."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, "pageId", "screenshotPath", "domHash", "domStructure", "capturedAt"
                FROM "Snapshot"
                WHERE "pageId" = %s
                ORDER BY "capturedAt" DESC
                LIMIT 1
            """, (page_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def save_snapshot(page_id: str, dom_hash: str, dom_structure: str, screenshot_path: Optional[str] = None) -> str:
    """Save a new snapshot and return its ID."""
    import cuid2
    snapshot_id = cuid2.cuid()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "Snapshot" (id, "pageId", "screenshotPath", "domHash", "domStructure", "capturedAt")
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (snapshot_id, page_id, screenshot_path, dom_hash, dom_structure, datetime.now(timezone.utc)))
            conn.commit()
        return snapshot_id
    finally:
        conn.close()


def save_change(page_id: str, service_name: str, page_type: str, category: Optional[str],
                summary: Optional[str], diff_text: Optional[str]) -> str:
    """Save a detected change and return its ID."""
    import cuid2
    change_id = cuid2.cuid()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "Change" (id, "pageId", "serviceName", "pageType", category, summary, "diffText", "detectedAt")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (change_id, page_id, service_name, page_type, category, summary, diff_text, datetime.now(timezone.utc)))
            conn.commit()
        return change_id
    finally:
        conn.close()


def save_advice(change_id: str, advice_data: dict) -> str:
    """Save AI-generated advice for a change."""
    import cuid2
    advice_id = cuid2.cuid()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "Advice" (id, "changeId", summary, intent, proposal, priority, "expectedEffect", risks, "rawResponse", "createdAt")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                advice_id, change_id,
                advice_data.get("summary"),
                advice_data.get("intent"),
                advice_data.get("proposal"),
                advice_data.get("priority"),
                advice_data.get("expected_effect"),
                advice_data.get("risks"),
                json.dumps(advice_data),
                datetime.now(timezone.utc),
            ))
            conn.commit()
        return advice_id
    finally:
        conn.close()


def update_page_scan_status(page_id: str, status: int):
    """Update the last scanned time and status for a page."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE "MonitoredPage"
                SET "lastScannedAt" = %s, "lastStatus" = %s, "updatedAt" = %s
                WHERE id = %s
            """, (datetime.now(timezone.utc), status, datetime.now(timezone.utc), page_id))
            conn.commit()
    finally:
        conn.close()
