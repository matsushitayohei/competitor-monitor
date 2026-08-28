"""Shared constants for the competitor monitor scraper."""

# Realistic browser User-Agent used by all Playwright instances.
# Update the Chrome version here when the bot-detection landscape changes.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

# Shared viewport height used by all captures.
VIEWPORT_HEIGHT = 800
