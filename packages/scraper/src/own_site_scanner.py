"""HOME'S (own site) structure scanner.

Scans LIFULL HOME'S pages and extracts UI/UX structure
in the same format as competitor pages, enabling direct comparison.
"""

import asyncio
import sys
import os
import traceback
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from structure_extractor import extract_page_structure
from form_analyzer import analyze_forms
from cv_detector import detect_cv_elements
from structure_db import (
    get_active_own_pages,
    save_own_page_structure,
    update_own_page_scan_status,
)


async def capture_page_html(url: str, viewport_width: int) -> tuple[str, int]:
    """Capture page HTML using Playwright.

    Returns (html_content, http_status).
    """
    from playwright.async_api import async_playwright

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": viewport_width, "height": 812},
            user_agent=user_agent,
        )

        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        http_status = response.status if response else 0

        # Wait for dynamic content to load
        await page.wait_for_timeout(2000)

        html = await page.content()
        await browser.close()

    return html, http_status


async def scan_own_page(page_info: dict) -> dict:
    """Scan a single HOME'S page and extract its structure."""
    page_id = page_info["id"]
    url = page_info["url"]
    device = page_info["device"]
    page_type = page_info["pageType"]
    name = page_info["name"]

    viewport_width = 1280 if device == "pc" else 375

    result = {
        "page_id": page_id,
        "name": name,
        "url": url,
        "device": device,
        "status": "ok",
        "structure_saved": False,
    }

    try:
        print(f"  Scanning HOME'S: {name} ({device})...")
        print(f"    URL: {url}")

        # 1. Capture HTML
        html, http_status = await capture_page_html(url, viewport_width)

        if http_status >= 400:
            result["status"] = f"http_{http_status}"
            print(f"    HTTP {http_status} - skipping")
            return result

        # 2. Extract page structure
        structure_data = extract_page_structure(html)

        # 3. Analyze forms (if form page or has forms)
        form_analysis = None
        if page_type == "form" or structure_data["summary"]["formCount"] > 0:
            form_result = analyze_forms(html)
            if form_result["forms"]:
                form_analysis = form_result

        # 4. Detect CV elements
        cv_data = detect_cv_elements(html)

        # 5. Save to DB (only if changed)
        metadata = {
            "url": url,
            "device": device,
            "pageType": page_type,
            "viewport": {"width": viewport_width, "height": 812},
            "httpStatus": http_status,
        }

        structure_id = save_own_page_structure(
            own_page_id=page_id,
            structure_data=structure_data,
            cv_points=cv_data,
            form_analysis=form_analysis,
            metadata=metadata,
        )

        if structure_id:
            result["structure_saved"] = True
            print(f"    Structure saved (new): {structure_id}")
            print(f"    Components: {structure_data['summary']['componentCount']}, "
                  f"CTAs: {cv_data['summary']['totalCtaCount']}, "
                  f"Forms: {structure_data['summary']['formCount']}")
        else:
            print(f"    Structure unchanged - skipped")

        # Update scan status
        update_own_page_scan_status(page_id)

    except Exception as e:
        result["status"] = f"error: {str(e)}"
        print(f"    Error: {e}")
        traceback.print_exc()

    return result


async def main():
    """Run HOME'S structure scan."""
    print(f"[{datetime.now().isoformat()}] Starting HOME'S structure scan...")

    # Fetch active own pages
    pages = get_active_own_pages()
    print(f"Found {len(pages)} HOME'S pages to scan")

    if not pages:
        print("No HOME'S pages configured. Register pages in OwnPage table first.")
        return

    # Scan sequentially
    results = []
    for page_info in pages:
        result = await scan_own_page(page_info)
        results.append(result)
        await asyncio.sleep(2)  # Be polite

    # Summary
    total = len(results)
    saved = sum(1 for r in results if r["structure_saved"])
    errors = sum(1 for r in results if r["status"].startswith("error"))

    print(f"\n[{datetime.now().isoformat()}] HOME'S scan complete.")
    print(f"  Total: {total}, Saved: {saved}, Errors: {errors}")

    if errors > 0:
        print("\nPages with errors:")
        for r in results:
            if r["status"].startswith("error"):
                print(f"  - {r['name']}: {r['status']}")


if __name__ == "__main__":
    asyncio.run(main())
