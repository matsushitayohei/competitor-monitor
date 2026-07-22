"""Main orchestrator for the daily competitor scan."""

import asyncio
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Add parent packages to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "analyzer", "src"))

from capture import capture_page
from diff import extract_structure, compute_diff
from db import (
    get_active_pages,
    get_latest_snapshot,
    save_snapshot,
    save_change,
    save_advice,
    update_page_scan_status,
    update_page_url,
    get_list_page_for_service,
)
from url_fallback import find_new_detail_url
from expired_detector import is_expired_page
from storage import upload_screenshot


def compute_dom_hash(structure: str) -> str:
    """Compute a hash of the DOM structure for quick comparison."""
    return hashlib.sha256(structure.encode("utf-8")).hexdigest()


async def scan_page(page_info: dict) -> dict:
    """Scan a single page and return the result."""
    page_id = page_info["page_id"]
    url = page_info["url"]
    device = page_info["device"]
    page_type = page_info["page_type"]
    service_name = page_info["service_name"]
    service_id = page_info["service_id"]

    viewport_width = 1280 if device == "pc" else 375
    result = {
        "page_id": page_id,
        "url": url,
        "device": device,
        "service": service_name,
        "status": "ok",
        "change_detected": False,
        "url_rotated": False,
    }

    try:
        print(f"  Capturing: {url} ({device})...")

        # 1. Capture page HTML and screenshot
        html, screenshot_bytes, http_status = await capture_page_with_html(url, viewport_width)

        # Update scan status
        update_page_scan_status(page_id, http_status)

        if http_status >= 400:
            # Attempt URL fallback for detail pages
            if page_type == "detail" and http_status == 404:
                print(f"    HTTP 404 on detail page - attempting URL fallback...")
                new_url = await _attempt_url_fallback(page_id, service_id, service_name, url, viewport_width)
                if new_url:
                    result["url_rotated"] = True
                    result["new_url"] = new_url
                    # Re-scan with the new URL
                    url = new_url
                    html, screenshot_bytes, http_status = await capture_page_with_html(url, viewport_width)
                    update_page_scan_status(page_id, http_status)
                    if http_status >= 400:
                        result["status"] = f"http_{http_status}"
                        print(f"    New URL also returned HTTP {http_status} - skipping")
                        return result
                    print(f"    URL rotated successfully, continuing scan with new URL")
                else:
                    result["status"] = f"http_{http_status}_no_fallback"
                    print(f"    No fallback URL available - skipping")
                    return result
            else:
                result["status"] = f"http_{http_status}"
                print(f"    HTTP {http_status} - skipping")
                return result

        # 1.5. Check if page content indicates expired listing (HTTP 200 but delisted)
        if page_type == "detail" and is_expired_page(html, service_name):
            print(f"    Expired listing detected (HTTP 200 but delisted) - attempting URL fallback...")
            new_url = await _attempt_url_fallback(page_id, service_id, service_name, url, viewport_width)
            if new_url:
                result["url_rotated"] = True
                result["new_url"] = new_url
                # Re-scan with the new URL
                url = new_url
                html, screenshot_bytes, http_status = await capture_page_with_html(url, viewport_width)
                update_page_scan_status(page_id, http_status)
                if http_status >= 400 or is_expired_page(html, service_name):
                    result["status"] = "expired_no_valid_fallback"
                    print(f"    New URL also expired or errored - skipping")
                    return result
                print(f"    URL rotated successfully, continuing scan with new URL")
            else:
                result["status"] = "expired_no_fallback"
                print(f"    No fallback URL available for expired page - skipping")
                return result

        # 2. Extract DOM structure (removing property-specific content)
        dom_structure = extract_structure(html)
        dom_hash = compute_dom_hash(dom_structure)

        # 3. Get previous snapshot
        prev_snapshot = get_latest_snapshot(page_id)

        # 4. Save new snapshot (always, for archiving)
        screenshot_path = upload_screenshot(screenshot_bytes, page_id, device)
        save_snapshot(page_id, dom_hash, dom_structure, screenshot_path)

        # 5. Compare with previous
        if prev_snapshot is None:
            # First scan - no comparison possible
            print(f"    First scan - snapshot saved")
            result["status"] = "first_scan"
            return result

        prev_hash = prev_snapshot.get("domHash")
        if prev_hash == dom_hash:
            print(f"    No changes detected")
            return result

        # 6. Change detected! Compute detailed diff
        print(f"    Change detected!")
        result["change_detected"] = True

        prev_structure = prev_snapshot.get("domStructure", "")
        diff_result = compute_diff(prev_structure, dom_structure)

        if not diff_result:
            # Hash mismatch but no structural diff (unlikely, but possible)
            print(f"    Hash changed but no structural diff")
            return result

        diff_text = diff_result.get("diff_text", "")

        # 7. Classify and summarize using rule-based analysis
        category = None
        summary = None
        advice_data = None

        try:
            from classify import classify_change
            from summarize import summarize_change
            from advice import generate_advice

            # Summarize
            summary = summarize_change(diff_text[:8000])
            print(f"    Summary: {summary[:100]}...")

            # Classify
            classify_result = classify_change(diff_text[:8000])
            try:
                classify_json = json.loads(classify_result)
                category = classify_json.get("category", "OTHER")
            except (json.JSONDecodeError, TypeError):
                category = "OTHER"

            # Generate placeholder advice (detailed analysis via MCP + Kiro)
            advice_response = generate_advice(
                service_name=service_name,
                page_type=page_type,
                category=category or "OTHER",
                diff_summary=summary or diff_text[:2000],
            )
            try:
                advice_data = json.loads(advice_response)
            except (json.JSONDecodeError, TypeError):
                advice_data = {"proposal": "MCP経由でKiroに分析を依頼してください", "priority": "medium"}

        except Exception as e:
            print(f"    Analysis error: {e}")
            category = "OTHER"
            summary = "DOM構造に変更を検知しました"

        # 8. Save change to DB
        change_id = save_change(
            page_id=page_id,
            service_name=service_name,
            page_type=page_type,
            category=category,
            summary=summary,
            diff_text=diff_text[:10000],  # Limit diff text size
        )

        # 9. Save advice if available
        if advice_data:
            save_advice(change_id, advice_data)

        print(f"    Change saved: {change_id}")

    except Exception as e:
        result["status"] = f"error: {str(e)}"
        print(f"    Error: {e}")
        traceback.print_exc()

    return result


async def _attempt_url_fallback(
    page_id: str, service_id: str, service_name: str, old_url: str, viewport_width: int
) -> Optional[str]:
    """Attempt to find a new detail URL from the listing page when 404 is encountered.

    Returns the new URL if found and DB updated, None otherwise.
    """
    list_page = get_list_page_for_service(service_id)
    if not list_page:
        print(f"    [URL Fallback] No listing page found for service {service_name}")
        return None

    list_url = list_page["url"]
    print(f"    [URL Fallback] Searching listing page: {list_url}")

    new_url = await find_new_detail_url(
        list_page_url=list_url,
        service_name=service_name,
        old_detail_url=old_url,
        viewport_width=viewport_width,
    )

    if new_url:
        update_page_url(page_id, new_url)
        print(f"    [URL Fallback] Updated page URL: {old_url} -> {new_url}")
        return new_url

    return None


async def capture_page_with_html(url: str, viewport_width: int, max_retries: int = 2) -> tuple[str, bytes, int]:
    """Capture page HTML content and screenshot with retry on transient failures."""
    from playwright.async_api import async_playwright

    # Use a realistic User-Agent to avoid bot detection (e.g. at home returns HTTP 405)
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page(
                    viewport={"width": viewport_width, "height": 800},
                    user_agent=user_agent,
                )

                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                http_status = response.status if response else 0

                # Wait for dynamic content
                await page.wait_for_timeout(2000)

                html = await page.content()
                screenshot = await page.screenshot(full_page=True)
                await browser.close()

            return html, screenshot, http_status
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = (attempt + 1) * 3
                print(f"    Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
            else:
                raise last_error


async def main():
    """Run the daily scan pipeline."""
    print(f"[{datetime.now().isoformat()}] Starting daily competitor scan...")

    # Fetch all active monitored pages
    pages = get_active_pages()
    print(f"Found {len(pages)} active pages to scan")

    if not pages:
        print("No pages to scan. Exiting.")
        return

    # Scan pages sequentially to avoid overwhelming target sites
    results = []
    for page_info in pages:
        result = await scan_page(page_info)
        results.append(result)
        # Be polite - wait between requests
        await asyncio.sleep(2)

    # Summary
    total = len(results)
    changes = sum(1 for r in results if r["change_detected"])
    errors = sum(1 for r in results if r["status"].startswith("error"))
    first_scans = sum(1 for r in results if r["status"] == "first_scan")

    print(f"\n[{datetime.now().isoformat()}] Scan complete.")
    print(f"  Total: {total}, Changes: {changes}, First scans: {first_scans}, Errors: {errors}")

    # Fail the job if majority of pages errored (so GitHub Actions shows failure)
    if errors > 0 and errors >= total * 0.5:
        print(f"\n  ERROR: {errors}/{total} pages failed. Exiting with error.")
        # Send notification before exiting
        if os.environ.get("SLACK_WEBHOOK_URL"):
            await send_slack_notification(results)
        sys.exit(1)

    # Send Slack notification if changes or URL issues detected
    has_notifications = (
        changes > 0
        or any(r.get("url_rotated") for r in results)
        or any(r["status"].endswith("_no_fallback") for r in results)
        or any(r["status"] == "expired_no_valid_fallback" for r in results)
    )
    if has_notifications and os.environ.get("SLACK_WEBHOOK_URL"):
        await send_slack_notification(results)


async def send_slack_notification(results: list[dict]):
    """Send a Slack notification about detected changes and URL rotations."""
    import httpx

    changes = [r for r in results if r["change_detected"]]
    rotations = [r for r in results if r.get("url_rotated")]
    no_fallback = [r for r in results if r["status"].endswith("_no_fallback") or r["status"] == "expired_no_valid_fallback"]

    text = ""

    if changes:
        text += f":mag: 競合サイト変更検知: {len(changes)}件\n"
        for r in changes:
            text += f"• {r['service']} ({r['device']}): {r['url']}\n"

    if rotations:
        text += f"\n:arrows_counterclockwise: 物件URL自動切替: {len(rotations)}件\n"
        for r in rotations:
            text += f"• {r['service']} ({r['device']}): {r.get('new_url', 'N/A')}\n"

    if no_fallback:
        text += f"\n:warning: URL切替失敗（要手動対応）: {len(no_fallback)}件\n"
        for r in no_fallback:
            text += f"• {r['service']} ({r['device']}): {r['url']}\n"

    if not text:
        return

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                os.environ["SLACK_WEBHOOK_URL"],
                json={"text": text.strip()},
                timeout=10,
            )
    except Exception as e:
        print(f"Slack notification error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
