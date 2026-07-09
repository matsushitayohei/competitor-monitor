"""DOM diff detection module."""

import difflib
from bs4 import BeautifulSoup
from typing import Optional


# Elements to exclude from diff (property-specific content)
EXCLUDE_SELECTORS = [
    # Price, address, property name etc.
    '[data-property-price]',
    '[data-property-address]',
    '.property-price',
    '.property-name',
    '.property-address',
    '.bukken-price',
    '.bukken-name',
    # SUUMO specific
    '.cassetteitem_price',
    '.cassetteitem_detail-col3',
    # athome specific
    '.price',
    '.detail-price',
    # Dynamic elements
    '.ad-banner',
    '.ranking-position',
    'time',
    '[datetime]',
    # Cookie banners, popups
    '.cookie-consent',
    '.modal-overlay',
    '#cookie-banner',
]


def extract_structure(html: str, exclude_selectors: Optional[list] = None) -> str:
    """Extract DOM structure, removing property-specific content."""
    soup = BeautifulSoup(html, 'lxml')

    # Remove script and style elements entirely
    for tag in soup.find_all(['script', 'style', 'noscript', 'iframe']):
        tag.decompose()

    selectors = exclude_selectors or EXCLUDE_SELECTORS
    for selector in selectors:
        try:
            for el in soup.select(selector):
                el.decompose()
        except Exception:
            pass  # Skip invalid selectors

    # Remove text content, keep structure only
    for text_node in soup.find_all(string=True):
        if text_node.parent and text_node.parent.name not in ['script', 'style']:
            text_node.replace_with('[TEXT]')

    return str(soup)


def compute_diff(old_structure: str, new_structure: str) -> Optional[dict]:
    """Compute structural diff between two HTML snapshots."""
    if old_structure == new_structure:
        return None

    # Split into lines for difflib comparison
    old_lines = old_structure.splitlines()
    new_lines = new_structure.splitlines()

    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile="before", tofile="after",
        lineterm="",
        n=3,  # context lines
    ))

    if not diff_lines:
        return None

    diff_text = "\n".join(diff_lines[:500])  # Limit to first 500 lines

    # Count changes
    additions = sum(1 for l in diff_lines if l.startswith('+') and not l.startswith('+++'))
    deletions = sum(1 for l in diff_lines if l.startswith('-') and not l.startswith('---'))

    return {
        "has_changes": True,
        "diff_text": diff_text,
        "additions": additions,
        "deletions": deletions,
        "old_length": len(old_structure),
        "new_length": len(new_structure),
    }
