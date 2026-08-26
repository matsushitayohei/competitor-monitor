"""Screenshot storage module using Vercel Blob via HTTP API."""

import os
from datetime import datetime, timezone
from typing import Optional

import httpx


def _detect_content_type(image_bytes: bytes) -> tuple[str, str]:
    """Detect image format from magic bytes and return (content_type, extension)."""
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png"
    # デフォルトは JPEG (クロップ画像はJPEG変換済み)
    return "image/jpeg", "jpg"


def upload_screenshot(image_bytes: bytes, page_id: str, device: str) -> Optional[str]:
    """Upload a screenshot or cropped image to Vercel Blob and return the URL.

    フォーマットはマジックバイトで自動判定（PNG / JPEG）。
    クロップ画像は visual_diff.py で JPEG に変換済みのため、
    PNGより大幅にサイズが小さい状態でアップロードされる。

    Args:
        image_bytes: PNG または JPEG の画像バイト列。
        page_id: MonitoredPage ID（パス名に使用）。
        device: デバイス種別（pc / sp）。

    Returns:
        アップロードされた Blob の URL。失敗時は None。
    """
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        print(f"    [Storage] BLOB_READ_WRITE_TOKEN is not set, skipping screenshot upload")
        return None

    content_type, ext = _detect_content_type(image_bytes)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pathname = f"screenshots/{page_id}/{device}_{timestamp}.{ext}"

    print(f"    [Storage] Uploading {ext.upper()} ({len(image_bytes):,} bytes) → {pathname}")

    try:
        url = f"https://blob.vercel-storage.com/{pathname}"

        headers = {
            "Authorization": f"Bearer {token}",
            "x-api-version": "7",
            "x-content-type": content_type,
            "x-add-random-suffix": "1",
        }

        response = httpx.put(
            url,
            content=image_bytes,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        result_url = data.get("url")
        print(f"    [Storage] Upload success: {result_url[:80] if result_url else 'no url in response'}...")
        return result_url
    except httpx.HTTPStatusError as e:
        print(f"    [Storage] Upload failed: {e}")
        print(f"    [Storage] Response body: {e.response.text[:500]}")
        return None
    except Exception as e:
        print(f"    [Storage] Upload failed: {e}")
        return None
