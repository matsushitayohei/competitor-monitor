"""DOM diff detection module."""

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
    # Dynamic elements
    '.ad-banner',
    '.ranking-position',
    'time',
    '[datetime]',
]


def extract_structure(html: str, exclude_selectors: Optional[list] = None) -> str:
    """Extract DOM structure, removing property-specific content."""
    soup = BeautifulSoup(html, 'lxml')
    
    selectors = exclude_selectors or EXCLUDE_SELECTORS
    for selector in selectors:
        for el in soup.select(selector):
            el.decompose()
    
    # Remove text content, keep structure only
    for text_node in soup.find_all(string=True):
        # Keep class names and attributes, remove actual text
        if text_node.parent.name not in ['script', 'style']:
            text_node.replace_with('[TEXT]')
    
    return str(soup)


def compute_diff(old_html: str, new_html: str) -> Optional[dict]:
    """Compute structural diff between two HTML snapshots."""
    old_structure = extract_structure(old_html)
    new_structure = extract_structure(new_html)
    
    if old_structure == new_structure:
        return None
    
    # TODO: Implement detailed diff using difflib
    return {
        "has_changes": True,
        "old_length": len(old_structure),
        "new_length": len(new_structure),
    }
