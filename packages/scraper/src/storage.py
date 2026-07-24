"""Screenshot storage module using Vercel Blob via HTTP API."""

import os
from datetime import datetime, timezone
from typing import Optional

import httpx


def upload_screenshot(screenshot_bytes: bytes, page_id: str, device: str) -> Optional[str]:
    """Upload a screenshot to Vercel Blob and return the URL.

    Uses the Vercel Blob REST API. Supports both public and private stores.
    For private stores, the token determines access and the API returns a
    private URL that requires authentication to read.

    Args:
        screenshot_bytes: PNG image bytes.
        page_id: MonitoredPage ID for path naming.
        device: Device type (pc/sp).

    Returns:
        The URL of the uploaded blob, or None on failure.
    """
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        print(f"    [Storage] BLOB_READ_WRITE_TOKEN is not set, skipping screenshot upload")
        return None

    print(f"    [Storage] Uploading screenshot ({len(screenshot_bytes)} bytes)...")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pathname = f"screenshots/{page_id}/{device}_{timestamp}.png"

    try:
        # Vercel Blob REST API requires the pathname in the URL path
        # and the token as Bearer auth. The x-api-version header is required.
        # For private stores, must also pass x-access: "private".
        url = f"https://blob.vercel-storage.com/{pathname}"

        headers = {
            "Authorization": f"Bearer {token}",
            "x-api-version": "7",
            "x-content-type": "image/png",
            "x-add-random-suffix": "1",
        }

        # Private store requires x-access: "private"
        headers["x-access"] = "private"

        response = httpx.put(
            url,
            content=screenshot_bytes,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        result_url = data.get("url")
        print(f"    [Storage] Upload success: {result_url[:80] if result_url else 'no url in response'}...")
        return result_url
    except httpx.HTTPStatusError as e:
        print(f"    [Storage] Screenshot upload failed: {e}")
        print(f"    [Storage] Response body: {e.response.text[:500]}")
        return None
    except Exception as e:
        print(f"    [Storage] Screenshot upload failed: {e}")
        return None
