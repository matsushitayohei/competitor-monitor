"""Screenshot storage module using Vercel Blob via HTTP API."""

import os
from datetime import datetime, timezone
from typing import Optional

import httpx


def upload_screenshot(screenshot_bytes: bytes, page_id: str, device: str) -> Optional[str]:
    """Upload a screenshot to Vercel Blob and return the URL.

    Args:
        screenshot_bytes: PNG image bytes.
        page_id: MonitoredPage ID for path naming.
        device: Device type (pc/sp).

    Returns:
        The public URL of the uploaded blob, or None on failure.
    """
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pathname = f"screenshots/{page_id}/{device}_{timestamp}.png"

    try:
        response = httpx.put(
            "https://blob.vercel-storage.com",
            content=screenshot_bytes,
            headers={
                "Authorization": f"Bearer {token}",
                "x-api-version": "7",
                "x-content-type": "image/png",
                "x-add-random-suffix": "true",
            },
            params={"pathname": pathname},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("url")
    except Exception as e:
        print(f"    [Storage] Screenshot upload failed: {e}")
        return None
