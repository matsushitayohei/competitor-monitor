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

from diff import extract_structure, compute_diff, NORM_VERSION_MARKER, detect_access_blocked_page
from constants import USER_AGENT, VIEWPORT_HEIGHT
from db import (
    get_active_pages,
    get_latest_snapshot,
    save_snapshot,
    save_change,
    save_advice,
    update_page_scan_status,
    update_page_url,
    get_list_page_for_service,
    is_duplicate_change,
)
from url_fallback import find_new_detail_url
from expired_detector import is_expired_page
from storage import upload_screenshot, png_to_jpeg
from visual_diff import generate_visual_diff
from slack_notifier import send_slack_notification

# Structure extraction modules
from structure_extractor import extract_page_structure
from form_analyzer import analyze_forms
from cv_detector import detect_cv_elements
from structure_db import save_page_structure, get_latest_page_structure


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

        # 1.6. Check for CAPTCHA / bot-challenge pages (HTTP 200 but real content not delivered)
        # These pages have identical structure every time (same hash), so they silently
        # suppress change detection for the service. Skip snapshot/diff and report the block.
        blocked_reason = detect_access_blocked_page(html)
        if blocked_reason:
            print(f"    ⚠️ Access blocked ({blocked_reason}) — skipping snapshot to avoid polluting baseline")
            result["status"] = f"captcha_blocked: {blocked_reason}"
            return result

        # 2. Extract DOM structure (removing property-specific content)
        dom_structure = extract_structure(html)
        dom_hash = compute_dom_hash(dom_structure)

        # 2.5. Extract UIUX component structure (independent of diff detection)
        structure_id_after = None
        structure_id_before = None
        try:
            # Get previous structure ID BEFORE saving new one
            prev_structure_record = get_latest_page_structure(page_id)
            if prev_structure_record:
                structure_id_before = prev_structure_record["id"]

            structure_data = extract_page_structure(html)

            # Form analysis for form pages or pages with forms
            form_analysis = None
            if page_type == "form" or structure_data["summary"]["formCount"] > 0:
                form_result = analyze_forms(html)
                if form_result["forms"]:
                    form_analysis = form_result

            # CV element detection
            cv_data = detect_cv_elements(html)

            # Save structure (only if changed from previous)
            structure_metadata = {
                "url": url,
                "device": device,
                "pageType": page_type,
                "serviceName": service_name,
                "viewport": {"width": viewport_width, "height": 800},
            }
            structure_id_after = save_page_structure(
                page_id=page_id,
                structure_data=structure_data,
                cv_points=cv_data,
                form_analysis=form_analysis,
                metadata=structure_metadata,
            )
            if structure_id_after:
                print(f"    Structure saved: {structure_data['summary']['componentCount']} components, "
                      f"{cv_data['summary']['totalCtaCount']} CTAs")
            else:
                # No change — before and after are the same
                structure_id_before = None
        except Exception as e:
            print(f"    Structure extraction error (non-fatal): {e}")
            traceback.print_exc()

        # 3. Get previous snapshot
        prev_snapshot = get_latest_snapshot(page_id)

        # 4. Save new snapshot (always, for archiving)
        # フルページスクショは JPEG に変換して Blob 保存（PNG比 60〜80% 削減）。
        # screenshotPath は次回スキャン時の visual diff 比較に必要なため継続保存する。
        snapshot_jpeg = png_to_jpeg(screenshot_bytes, quality=60)
        screenshot_path = upload_screenshot(snapshot_jpeg, page_id, device)
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

        # 5.5. Check for rendering failure (DOM drastically smaller than previous)
        prev_structure = prev_snapshot.get("domStructure", "")
        current_size = len(dom_structure)
        prev_size = len(prev_structure)

        if prev_size > 0 and current_size < prev_size * 0.1:
            print(f"    ⚠️ Rendering failure detected: DOM size dropped to {current_size}/{prev_size} "
                  f"({current_size * 100 // prev_size}%). Skipping as false positive.")
            result["status"] = "rendering_failure"
            return result

        # 5.6. Re-normalize previous structure if it was saved with old logic
        # (handles transition period after diff.py normalization improvements)
        if prev_structure and NORM_VERSION_MARKER not in prev_structure:
            # Previous snapshot was saved without current normalization version
            # The new snapshot has already been saved (step 4) with current normalization,
            # so next run will have a valid comparison baseline. Skip this comparison only.
            print(f"    ⚠️ Previous snapshot uses old normalization format - treating as baseline reset (next run will compare normally)")
            result["status"] = "baseline_reset"
            return result

        # 6. Change detected! Compute detailed diff
        print(f"    Change detected!")
        result["change_detected"] = True

        diff_result = compute_diff(prev_structure, dom_structure)

        if not diff_result:
            # Hash mismatch but no structural diff (unlikely, but possible)
            print(f"    Hash changed but no structural diff")
            return result

        diff_text = diff_result.get("diff_text", "")

        # 6.5. Duplicate diff guard: skip if the diff is identical to the most recent
        # recorded change for this page. This prevents repeated storage of the same
        # transient rendering inconsistency (e.g. an SPA section toggling on/off daily).
        if is_duplicate_change(page_id, diff_text[:10000]):
            print(f"    Duplicate diff — identical to previous change, skipping")
            result["change_detected"] = False
            result["status"] = "duplicate_diff"
            return result

        # 7. Classify and summarize using rule-based analysis
        category = None
        summary = None
        advice_data = None

        # 7a. Summarize — extract human/AI-readable description from diff
        try:
            from summarize import summarize_change
            summary = summarize_change(diff_text[:8000])
            print(f"    Summary: {summary[:100]}...")
        except Exception as e:
            print(f"    Summarize error (non-fatal): {e}")
            summary = "DOM構造に変更を検知しました"

        # 7b. Classify — assign category using rule-based pattern matching
        try:
            from classify import classify_change
            classify_result = classify_change(diff_text[:8000])
            try:
                classify_json = json.loads(classify_result)
                category = classify_json.get("category", "OTHER")
            except (json.JSONDecodeError, TypeError):
                category = "OTHER"
        except Exception as e:
            print(f"    Classify error (non-fatal): {e}")
            category = "OTHER"

        # 7c. Generate structured advice (placeholder + priority/scale heuristics)
        try:
            from advice import generate_advice
            advice_response = generate_advice(
                service_name=service_name,
                page_type=page_type,
                category=category or "OTHER",
                diff_summary=summary or diff_text[:2000],
                additions=diff_result.get("additions", 0),
                deletions=diff_result.get("deletions", 0),
            )
            try:
                advice_data = json.loads(advice_response)
            except (json.JSONDecodeError, TypeError):
                advice_data = {"proposal": "MCP経由でKiroに分析を依頼してください", "priority": "medium"}
        except Exception as e:
            print(f"    Advice error (non-fatal): {e}")
            advice_data = {"proposal": "MCP経由でKiroに分析を依頼してください", "priority": "low"}

        # Store analysis results in the result dict for notification
        result["category"] = category
        result["summary"] = summary
        result["page_type"] = page_type
        result["priority"] = advice_data.get("priority", "low") if advice_data else "low"

        # 8. Save change to DB (with before/after cropped screenshots)
        before_screenshot_path = prev_snapshot.get("screenshotPath") if prev_snapshot else None

        # 8.5 Generate visual diff + cropped before/after images
        # generate_visual_diff() returns VisualDiffResult when structural changes are clear,
        # or None when changes are too noisy (dynamic content).
        visual_diff_path = None
        before_crop_path = None
        after_crop_path = None

        if before_screenshot_path:
            try:
                import httpx as _httpx
                # Vercel Blob URLs require the same token used for upload
                _blob_token = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
                _auth_headers = {"Authorization": f"Bearer {_blob_token}"} if _blob_token else {}
                async with _httpx.AsyncClient() as _client:
                    before_response = await _client.get(
                        before_screenshot_path, timeout=30, headers=_auth_headers
                    )
                if before_response.status_code == 200:
                    diff_result_obj = generate_visual_diff(
                        before_response.content,
                        screenshot_bytes,
                    )
                    if diff_result_obj:
                        # Upload cropped before/after (変更箇所のみ — 数十KBに抑えられる)
                        before_crop_path = upload_screenshot(
                            diff_result_obj.before_crop, f"{page_id}/before", device
                        )
                        after_crop_path = upload_screenshot(
                            diff_result_obj.after_crop, f"{page_id}/after", device
                        )
                        visual_diff_path = upload_screenshot(
                            diff_result_obj.diff_image, f"{page_id}/diff", device
                        )
                        if visual_diff_path:
                            print(f"    Visual diff generated ({len(diff_result_obj.regions)} regions, crops: before={before_crop_path is not None}, after={after_crop_path is not None})")
                    else:
                        print(f"    Visual diff skipped: {diff_result_obj.reason}")
            except Exception as e:
                print(f"    Visual diff generation failed: {e}")

        change_id = save_change(
            page_id=page_id,
            service_name=service_name,
            page_type=page_type,
            category=category,
            summary=summary,
            diff_text=diff_text[:10000],  # Limit diff text size
            before_screenshot_path=before_crop_path,   # 変更箇所クロップ（before）
            after_screenshot_path=after_crop_path,     # 変更箇所クロップ（after）
            visual_diff_path=visual_diff_path,
            structure_before_id=structure_id_before,
            structure_after_id=structure_id_after,
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
    user_agent = USER_AGENT

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                html = ""
                screenshot = b""
                http_status = 0
                try:
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
                finally:
                    # ブラウザプロセスを確実に終了（例外時のリーク防止）
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
    rendering_failures = sum(1 for r in results if r["status"] == "rendering_failure")
    baseline_resets = sum(1 for r in results if r["status"] == "baseline_reset")
    captcha_blocked = sum(1 for r in results if r["status"].startswith("captcha_blocked"))
    duplicate_diffs = sum(1 for r in results if r["status"] == "duplicate_diff")

    print(f"\n[{datetime.now().isoformat()}] Scan complete.")
    print(f"  Total: {total}, Changes: {changes}, First scans: {first_scans}, "
          f"Baseline resets: {baseline_resets}, "
          f"Duplicate diffs: {duplicate_diffs}, "
          f"CAPTCHA blocked: {captcha_blocked}, "
          f"Errors: {errors}, Rendering failures: {rendering_failures}")

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
        or rendering_failures >= total * 0.3  # Alert if 30%+ pages had rendering failures
        or captcha_blocked >= total * 0.1     # Alert if 10%+ pages are CAPTCHA-blocked
    )
    if has_notifications and os.environ.get("SLACK_WEBHOOK_URL"):
        await send_slack_notification(results)




if __name__ == "__main__":
    asyncio.run(main())
