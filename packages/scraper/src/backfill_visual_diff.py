"""Backfill visual diff images for existing Change records that have no screenshots.

Finds Change records where beforeScreenshotPath / afterScreenshotPath / visualDiffPath
are all NULL, then attempts to regenerate cropped diff images from the two Snapshots
surrounding the detected change time.

Strategy per Change record:
  1. Find the Snapshot taken immediately BEFORE detectedAt for the same page
     (= the "before" state at the time of detection)
  2. Find the Snapshot taken immediately AFTER (or at) detectedAt
     (= the "after" state)
  3. Download both screenshots from Vercel Blob
  4. Run generate_visual_diff()
  5. If successful, upload crops + diff image, then UPDATE the Change row

Usage:
    # Dry run — show what would be processed
    python backfill_visual_diff.py --dry-run

    # Process up to 50 records
    python backfill_visual_diff.py --limit 50

    # Process only a specific Change ID
    python backfill_visual_diff.py --change-id <id>

    # Verbose: print skip reasons
    python backfill_visual_diff.py --verbose
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import httpx
import psycopg2
import psycopg2.extras

from db import get_connection, release_connection
from storage import upload_screenshot
from visual_diff import generate_visual_diff, VisualDiffResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_changes_without_images(limit: int, change_id: Optional[str]) -> list[dict]:
    """Fetch Change records that have no screenshot paths."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if change_id:
                cur.execute("""
                    SELECT id, "pageId", "detectedAt", "serviceName", "pageType"
                    FROM "Change"
                    WHERE id = %s
                      AND "beforeScreenshotPath" IS NULL
                      AND "afterScreenshotPath" IS NULL
                      AND "visualDiffPath" IS NULL
                """, (change_id,))
            else:
                cur.execute("""
                    SELECT id, "pageId", "detectedAt", "serviceName", "pageType"
                    FROM "Change"
                    WHERE "beforeScreenshotPath" IS NULL
                      AND "afterScreenshotPath" IS NULL
                      AND "visualDiffPath" IS NULL
                    ORDER BY "detectedAt" DESC
                    LIMIT %s
                """, (limit,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        release_connection(conn)


def get_snapshot_pair(page_id: str, detected_at: datetime) -> tuple[Optional[dict], Optional[dict]]:
    """Return (before_snapshot, after_snapshot) around the change detection time.

    before: the latest snapshot captured strictly BEFORE detectedAt
    after:  the earliest snapshot captured AT or AFTER detectedAt
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Snapshot taken before the change
            cur.execute("""
                SELECT id, "screenshotPath", "capturedAt"
                FROM "Snapshot"
                WHERE "pageId" = %s
                  AND "capturedAt" < %s
                  AND "screenshotPath" IS NOT NULL
                ORDER BY "capturedAt" DESC
                LIMIT 1
            """, (page_id, detected_at))
            before = cur.fetchone()

            # Snapshot taken at or after the change (= the "new" state)
            cur.execute("""
                SELECT id, "screenshotPath", "capturedAt"
                FROM "Snapshot"
                WHERE "pageId" = %s
                  AND "capturedAt" >= %s
                  AND "screenshotPath" IS NOT NULL
                ORDER BY "capturedAt" ASC
                LIMIT 1
            """, (page_id, detected_at))
            after = cur.fetchone()

        return (dict(before) if before else None, dict(after) if after else None)
    finally:
        release_connection(conn)


def update_change_screenshots(
    change_id: str,
    before_path: Optional[str],
    after_path: Optional[str],
    diff_path: Optional[str],
) -> None:
    """Update screenshot paths on a Change record."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE "Change"
                SET "beforeScreenshotPath" = %s,
                    "afterScreenshotPath"  = %s,
                    "visualDiffPath"       = %s
                WHERE id = %s
            """, (before_path, after_path, diff_path, change_id))
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


# ---------------------------------------------------------------------------
# Core async worker
# ---------------------------------------------------------------------------

async def _download(client: httpx.AsyncClient, url: str, blob_token: str) -> Optional[bytes]:
    """Download a Vercel Blob image with auth."""
    headers = {"Authorization": f"Bearer {blob_token}"} if blob_token else {}
    try:
        resp = await client.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.content
        logger.warning(f"  Download failed: HTTP {resp.status_code} for {url[:80]}")
        return None
    except Exception as e:
        logger.warning(f"  Download error: {e}")
        return None


async def process_change(
    change: dict,
    client: httpx.AsyncClient,
    blob_token: str,
    dry_run: bool,
    verbose: bool,
) -> str:
    """Process one Change record.  Returns one of: 'updated' | 'skipped' | 'no_snapshots' | 'error'."""
    change_id = change["id"]
    page_id = change["pageId"]
    detected_at = change["detectedAt"]
    label = f"[{change['serviceName']} / {change['pageType']}]"

    before_snap, after_snap = get_snapshot_pair(page_id, detected_at)

    if not before_snap:
        if verbose:
            logger.info(f"  {label} {change_id[:8]}… — no before-snapshot found")
        return "no_snapshots"

    if not after_snap:
        if verbose:
            logger.info(f"  {label} {change_id[:8]}… — no after-snapshot found")
        return "no_snapshots"

    # Download both screenshots
    before_bytes = await _download(client, before_snap["screenshotPath"], blob_token)
    after_bytes  = await _download(client, after_snap["screenshotPath"],  blob_token)

    if not before_bytes or not after_bytes:
        return "error"

    # Run visual diff
    result = generate_visual_diff(before_bytes, after_bytes)

    if not result:
        if verbose:
            logger.info(f"  {label} {change_id[:8]}… — visual diff skipped: {result.reason}")
        return "skipped"

    assert isinstance(result, VisualDiffResult)
    logger.info(
        f"  {label} {change_id[:8]}… — diff OK "
        f"({len(result.regions)} regions, "
        f"before={len(result.before_crop):,}B, after={len(result.after_crop):,}B)"
    )

    if dry_run:
        return "updated"

    # Upload crops + diff image
    device = "sp"  # crops are device-agnostic; use "sp" as folder prefix
    before_path = upload_screenshot(result.before_crop, f"{page_id}/before", device)
    after_path  = upload_screenshot(result.after_crop,  f"{page_id}/after",  device)
    diff_path   = upload_screenshot(result.diff_image,  f"{page_id}/diff",   device)

    if not before_path and not after_path and not diff_path:
        logger.warning(f"  {label} {change_id[:8]}… — all uploads failed")
        return "error"

    update_change_screenshots(change_id, before_path, after_path, diff_path)
    logger.info(f"  {label} {change_id[:8]}… — DB updated")
    return "updated"


async def run(args: argparse.Namespace) -> None:
    blob_token = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
    if not blob_token and not args.dry_run:
        logger.error("BLOB_READ_WRITE_TOKEN is not set. Aborting (use --dry-run to test without uploads).")
        sys.exit(1)

    changes = get_changes_without_images(args.limit, args.change_id)
    logger.info(f"Found {len(changes)} Change records without screenshots")

    if not changes:
        logger.info("Nothing to do.")
        return

    stats = {"updated": 0, "skipped": 0, "no_snapshots": 0, "error": 0}

    async with httpx.AsyncClient() as client:
        for change in changes:
            status = await process_change(
                change, client, blob_token, args.dry_run, args.verbose
            )
            stats[status] = stats.get(status, 0) + 1
            # Small delay to avoid hammering Blob Storage
            await asyncio.sleep(0.5)

    logger.info(
        f"\nResults: updated={stats['updated']}  skipped={stats['skipped']}  "
        f"no_snapshots={stats['no_snapshots']}  error={stats['error']}"
    )
    if args.dry_run:
        logger.info("(dry-run — no DB writes or uploads performed)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill visual diff images for Change records that have no screenshots"
    )
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Max number of Change records to process (default: 100)"
    )
    parser.add_argument(
        "--change-id", type=str, default=None,
        help="Process only this specific Change ID"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run without uploading or updating the DB"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print skip reasons for each skipped record"
    )
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
