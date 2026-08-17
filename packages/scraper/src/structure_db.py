"""Database access module for PageStructure / OwnPageStructure tables."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from db import get_connection, release_connection


def save_page_structure(
    page_id: str,
    structure_data: dict,
    cv_points: Optional[dict] = None,
    form_analysis: Optional[dict] = None,
    metadata: Optional[dict] = None,
) -> Optional[str]:
    """Save page structure snapshot. Only saves if structure hash has changed.

    Returns the structure ID if saved, None if unchanged.
    """
    from structure_extractor import compute_structure_hash

    structure_hash = compute_structure_hash(structure_data)

    # Check if latest snapshot has same hash
    latest = get_latest_page_structure(page_id)
    if latest and latest.get("hash") == structure_hash:
        return None  # No change

    # Compute component count
    component_count = sum(
        len(s.get("components", []))
        for s in structure_data.get("sections", [])
    )

    structure_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "PageStructure" 
                    (id, "pageId", "capturedAt", "structureSummary", sections, 
                     "cvPoints", "formAnalysis", "componentCount", hash, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                structure_id,
                page_id,
                datetime.now(timezone.utc),
                json.dumps(structure_data.get("summary", {})),
                json.dumps(structure_data.get("sections", [])),
                json.dumps(cv_points) if cv_points else None,
                json.dumps(form_analysis) if form_analysis else None,
                component_count,
                structure_hash,
                json.dumps(metadata) if metadata else None,
            ))
            conn.commit()
        return structure_id
    except Exception as e:
        conn.rollback()
        print(f"    [Structure DB] Error saving page structure: {e}")
        return None
    finally:
        release_connection(conn)


def get_latest_page_structure(page_id: str) -> Optional[dict]:
    """Get the most recent structure snapshot for a monitored page."""
    conn = get_connection()
    try:
        import psycopg2.extras
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, "pageId", "capturedAt", "structureSummary", sections, 
                       "cvPoints", "formAnalysis", "componentCount", hash, metadata
                FROM "PageStructure"
                WHERE "pageId" = %s
                ORDER BY "capturedAt" DESC
                LIMIT 1
            """, (page_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)


def save_own_page_structure(
    own_page_id: str,
    structure_data: dict,
    cv_points: Optional[dict] = None,
    form_analysis: Optional[dict] = None,
    metadata: Optional[dict] = None,
) -> Optional[str]:
    """Save HOME'S page structure snapshot. Only saves if structure hash has changed.

    Returns the structure ID if saved, None if unchanged.
    """
    from structure_extractor import compute_structure_hash

    structure_hash = compute_structure_hash(structure_data)

    # Check if latest snapshot has same hash
    latest = get_latest_own_page_structure(own_page_id)
    if latest and latest.get("hash") == structure_hash:
        return None  # No change

    component_count = sum(
        len(s.get("components", []))
        for s in structure_data.get("sections", [])
    )

    structure_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "OwnPageStructure" 
                    (id, "ownPageId", "capturedAt", "structureSummary", sections, 
                     "cvPoints", "formAnalysis", "componentCount", hash, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                structure_id,
                own_page_id,
                datetime.now(timezone.utc),
                json.dumps(structure_data.get("summary", {})),
                json.dumps(structure_data.get("sections", [])),
                json.dumps(cv_points) if cv_points else None,
                json.dumps(form_analysis) if form_analysis else None,
                component_count,
                structure_hash,
                json.dumps(metadata) if metadata else None,
            ))
            conn.commit()
        return structure_id
    except Exception as e:
        conn.rollback()
        print(f"    [Structure DB] Error saving own page structure: {e}")
        return None
    finally:
        release_connection(conn)


def get_latest_own_page_structure(own_page_id: str) -> Optional[dict]:
    """Get the most recent structure snapshot for a HOME'S page."""
    conn = get_connection()
    try:
        import psycopg2.extras
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, "ownPageId", "capturedAt", "structureSummary", sections, 
                       "cvPoints", "formAnalysis", "componentCount", hash, metadata
                FROM "OwnPageStructure"
                WHERE "ownPageId" = %s
                ORDER BY "capturedAt" DESC
                LIMIT 1
            """, (own_page_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_connection(conn)


def get_active_own_pages() -> list[dict]:
    """Fetch all active HOME'S pages to scan."""
    conn = get_connection()
    try:
        import psycopg2.extras
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, "pageType", url, device, category
                FROM "OwnPage"
                WHERE "isActive" = true
                  AND "deletedAt" IS NULL
                ORDER BY "pageType", device
            """)
            return [dict(row) for row in cur.fetchall()]
    finally:
        release_connection(conn)


def update_own_page_scan_status(own_page_id: str):
    """Update lastScannedAt for a HOME'S page."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE "OwnPage"
                SET "lastScannedAt" = %s, "updatedAt" = %s
                WHERE id = %s
            """, (datetime.now(timezone.utc), datetime.now(timezone.utc), own_page_id))
            conn.commit()
    finally:
        release_connection(conn)
