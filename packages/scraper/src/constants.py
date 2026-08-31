"""Shared constants for the competitor monitor scraper."""

# Realistic browser User-Agent used by all Playwright instances.
# Update the Chrome version here when the bot-detection landscape changes.
# Last updated: 2026-08 → Chrome 151 (stable)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)

# Shared viewport height used by all captures.
VIEWPORT_HEIGHT = 800
