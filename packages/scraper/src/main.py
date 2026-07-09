"""Main orchestrator for the daily competitor scan."""

import asyncio
import hashlib
import json
import os
import sys
import traceback
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Add parent packages to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "analyzer", "src"))

from capture import capture_page
from diff import extract_structure, compute_diff
from db import get_active_pages, get_latest_snapshot, save_snapshot, save_change, save_advice, update_page_scan_status


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

    viewport_width = 1280 if device == "pc" else 375
    result = {
        "page_id": page_id,
        "url": url,
        "device": device,
        "service": service_name,
        "status": "ok",
        "change_detected": False,
    }

    try:
        print(f"  Capturing: {url} ({device})...")

        # 1. Capture page HTML and screenshot
        html, screenshot_bytes, http_status = await capture_page_with_html(url, viewport_width)

        # Update scan status
        update_page_scan_status(page_id, http_status)

        if http_status >= 400:
            result["status"] = f"http_{http_status}"
            print(f"    HTTP {http_status} - skipping")
            return result

        # 2. Extract DOM structure (removing property-specific content)
        dom_structure = extract_structure(html)
        dom_hash = compute_dom_hash(dom_structure)

        # 3. Get previous snapshot
        prev_snapshot = get_latest_snapshot(page_id)

        # 4. Save new snapshot (always, for archiving)
        save_snapshot(page_id, dom_hash, dom_structure)

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

        # 7. Classify and summarize using AI (if API key available)
        category = None
        summary = None
        advice_data = None

        if os.environ.get("GOOGLE_AI_API_KEY"):
            try:
                from classify import classify_change
                from summarize import summarize_change
                from advice import generate_advice

                # Summarize
                summary = summarize_change(diff_text[:4000])
                print(f"    Summary: {summary[:100]}...")

                # Classify
                classify_result = classify_change(diff_text[:4000])
                try:
                    classify_json = json.loads(classify_result)
                    category = classify_json.get("category", "OTHER")
                except (json.JSONDecodeError, TypeError):
                    category = "OTHER"

                # Generate advice
                advice_response = generate_advice(
                    service_name=service_name,
                    page_type=page_type,
                    category=category or "OTHER",
                    diff_summary=summary or diff_text[:2000],
                )
                try:
                    advice_data = json.loads(advice_response)
                except (json.JSONDecodeError, TypeError):
                    advice_data = {"proposal": advice_response, "priority": "medium"}

            except Exception as e:
                print(f"    AI analysis error: {e}")
                category = "OTHER"
                summary = "AI分析中にエラーが発生しました"
        else:
            summary = "DOM構造に変更を検知しました"
            category = "OTHER"

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


async def capture_page_with_html(url: str, viewport_width: int) -> tuple[str, bytes, int]:
    """Capture page HTML content and screenshot."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": viewport_width, "height": 800})

        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        http_status = response.status if response else 0

        # Wait for dynamic content
        await page.wait_for_timeout(2000)

        html = await page.content()
        screenshot = await page.screenshot(full_page=True)
        await browser.close()

    return html, screenshot, http_status


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

    # Send Slack notification if changes detected
    if changes > 0 and os.environ.get("SLACK_WEBHOOK_URL"):
        await send_slack_notification(results)


async def send_slack_notification(results: list[dict]):
    """Send a Slack notification about detected changes."""
    import httpx

    changes = [r for r in results if r["change_detected"]]
    text = f":mag: 競合サイト変更検知: {len(changes)}件\n"
    for r in changes:
        text += f"• {r['service']} ({r['device']}): {r['url']}\n"

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                os.environ["SLACK_WEBHOOK_URL"],
                json={"text": text},
                timeout=10,
            )
    except Exception as e:
        print(f"Slack notification error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
