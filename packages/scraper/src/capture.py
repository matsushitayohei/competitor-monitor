"""Screenshot capture module using Playwright."""

import asyncio
from playwright.async_api import async_playwright


async def capture_page(url: str, viewport_width: int = 1280) -> bytes:
    """Capture a full-page screenshot of the given URL."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": viewport_width, "height": 800})
        await page.goto(url, wait_until="networkidle")
        screenshot = await page.screenshot(full_page=True)
        await browser.close()
        return screenshot


if __name__ == "__main__":
    # Test capture
    result = asyncio.run(capture_page("https://suumo.jp"))
    print(f"Captured {len(result)} bytes")
