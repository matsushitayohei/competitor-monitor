"""Vercel Blob storage cleanup script.

既存のスクリーンショット（全量 PNG）を削除してストレージ容量を解放する。
スナップショット保存を JPEG 化した新方式に移行するための一回性クリーンアップ。

実行方法:
    BLOB_READ_WRITE_TOKEN=xxx python cleanup_blob.py [--dry-run]
"""

import json
import os
import sys
import time
from typing import Optional

import requests

BLOB_API_BASE = "https://blob.vercel-storage.com"
# 削除対象プレフィックス（screenshots/ 以下を全て対象）
TARGET_PREFIX = "screenshots/"
# 1回の DELETE リクエストで送る URL 数（API 上限に合わせて調整）
DELETE_BATCH_SIZE = 100


def list_blobs(token: str, prefix: str, cursor: Optional[str] = None) -> dict:
    """Blob ストアのファイル一覧を取得する（1ページ分）。"""
    params: dict = {"prefix": prefix, "limit": 1000}
    if cursor:
        params["cursor"] = cursor

    resp = requests.get(
        BLOB_API_BASE + "/",
        params=params,
        headers={
            "Authorization": f"Bearer {token}",
            "x-api-version": "7",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def delete_blobs(token: str, urls: list[str]) -> None:
    """指定した URL の Blob を一括削除する。

    Vercel Blob は DELETE / に JSON body を渡す方式と
    POST /delete に渡す方式の両方を持つ。まず DELETE を試みる。
    """
    body = json.dumps({"urls": urls}).encode()
    headers = {
        "Authorization": f"Bearer {token}",
        "x-api-version": "7",
        "Content-Type": "application/json",
    }

    # POST /delete エンドポイント（より確実）
    resp = requests.post(
        BLOB_API_BASE + "/delete",
        data=body,
        headers=headers,
        timeout=60,
    )
    if not resp.ok:
        print(f"    [delete] POST /delete → {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()


def run(dry_run: bool = False) -> None:
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        print("ERROR: BLOB_READ_WRITE_TOKEN is not set")
        sys.exit(1)

    mode = "[DRY RUN] " if dry_run else ""
    print(f"{mode}Starting Vercel Blob cleanup — prefix: {TARGET_PREFIX!r}")

    all_urls: list[str] = []
    total_size_bytes = 0
    cursor = None
    page = 0

    # --- リスト収集（全ページ） ---
    while True:
        page += 1
        try:
            result = list_blobs(token, TARGET_PREFIX, cursor)
        except requests.HTTPError as e:
            print(f"ERROR listing blobs (page {page}): {e}")
            print(f"  Response: {e.response.text[:500]}")
            sys.exit(1)

        blobs = result.get("blobs", [])
        for b in blobs:
            all_urls.append(b["url"])
            total_size_bytes += b.get("size", 0)

        has_more = result.get("hasMore", False)
        cursor = result.get("cursor")
        print(f"  Page {page}: {len(blobs)} files listed (cumulative: {len(all_urls)})")

        if not has_more or not cursor:
            break

        time.sleep(0.2)  # API レート制限対策

    total_mb = total_size_bytes / 1024 / 1024
    print(f"\nTotal: {len(all_urls)} files, {total_mb:.1f} MB")

    if not all_urls:
        print("Nothing to delete.")
        return

    if dry_run:
        print(f"\n[DRY RUN] Would delete {len(all_urls)} files ({total_mb:.1f} MB).")
        print("  First 10 files:")
        for url in all_urls[:10]:
            print(f"    {url}")
        if len(all_urls) > 10:
            print(f"    ... and {len(all_urls) - 10} more")
        return

    # --- 削除実行（バッチ分割） ---
    print(f"\nDeleting {len(all_urls)} files in batches of {DELETE_BATCH_SIZE}...")
    deleted = 0
    failed = 0

    for i in range(0, len(all_urls), DELETE_BATCH_SIZE):
        batch = all_urls[i : i + DELETE_BATCH_SIZE]
        try:
            delete_blobs(token, batch)
            deleted += len(batch)
            print(f"  Deleted batch {i // DELETE_BATCH_SIZE + 1}: {deleted}/{len(all_urls)} files")
        except requests.HTTPError as e:
            failed += len(batch)
            print(f"  ERROR deleting batch {i // DELETE_BATCH_SIZE + 1}: {e}")
            print(f"    Response: {e.response.text[:300]}")
        except Exception as e:
            failed += len(batch)
            print(f"  ERROR deleting batch {i // DELETE_BATCH_SIZE + 1}: {e}")

        time.sleep(0.3)  # API レート制限対策

    print(f"\nDone. Deleted: {deleted}, Failed: {failed}")
    freed_mb = total_size_bytes / 1024 / 1024
    print(f"Freed approximately {freed_mb:.1f} MB")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run(dry_run=dry_run)
