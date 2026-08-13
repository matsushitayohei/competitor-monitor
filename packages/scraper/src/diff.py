"""DOM diff detection module."""

import difflib
import re
from bs4 import BeautifulSoup, Tag
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

# Patterns for dynamic URL segments to normalize
_ASSET_HASH_PATTERN = re.compile(
    r'(/(_next|static|assets|webpack|chunks)/[^"\']*?)[a-f0-9]{8,}([^"\']*)',
    re.IGNORECASE,
)
_BUILD_ID_PATTERN = re.compile(
    r'/_next/data/[a-zA-Z0-9_-]+/',
)
_CACHE_BUSTER_PATTERN = re.compile(
    r'[?&](v|ver|version|hash|t|ts|cb|_)=[^&"\']+',
)


def _normalize_asset_url(tag: Tag, val: str) -> str:
    """Normalize dynamic segments in asset URLs (build hashes, cache busters)."""
    if not val:
        return val

    # Skip data: URIs (base64 images etc.) - replace entirely
    if val.startswith('data:'):
        return '[DATA_URI]'

    # Normalize Next.js build IDs: /_next/data/BUILD_ID/...
    result = _BUILD_ID_PATTERN.sub('/_next/data/[BUILD_ID]/', val)

    # Normalize hash segments in asset paths
    result = _ASSET_HASH_PATTERN.sub(r'\1[HASH]\3', result)

    # Remove cache buster query params
    result = _CACHE_BUSTER_PATTERN.sub('', result)

    return result


def extract_structure(html: str, exclude_selectors: Optional[list] = None) -> str:
    """Extract DOM structure, removing property-specific and dynamic content.

    This function normalizes the HTML to focus on structural changes:
    - Removes script, style, noscript, iframe elements
    - Removes property-specific elements (prices, addresses, etc.)
    - Replaces text content with [TEXT] placeholder
    - Normalizes dynamic attributes (CSRF tokens, build hashes, tracking IDs)
    """
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

    # Normalize dynamic attributes to reduce noise
    for tag in soup.find_all(True):  # All tags
        _normalize_tag_attrs(tag)

    # Remove text content, keep structure only
    for text_node in soup.find_all(string=True):
        if text_node.parent and text_node.parent.name not in ['script', 'style']:
            text_node.replace_with('[TEXT]')

    return str(soup)


def _normalize_tag_attrs(tag: Tag) -> None:
    """Normalize dynamic attributes on a single tag to reduce noise."""
    if not hasattr(tag, 'attrs'):
        return

    # Handle hidden inputs (CSRF tokens, nonces)
    if tag.name == 'input' and tag.get('type') == 'hidden':
        if 'value' in tag.attrs:
            tag['value'] = '[HIDDEN_VALUE]'

    # Normalize src/href for assets
    for attr in ('src', 'href'):
        val = tag.get(attr)
        if val and isinstance(val, str):
            tag[attr] = _normalize_asset_url(tag, val)

    # Remove common dynamic/tracking attributes entirely
    dynamic_attrs_to_remove = [
        'data-tracking-id', 'data-session', 'data-csrf', 'data-nonce',
        'data-request-id', 'data-impression-id', 'data-ab-test',
        'data-gtm-vis-*',
    ]
    attrs_to_remove = []
    for attr_name in list(tag.attrs.keys()):
        # Remove attributes matching dynamic patterns
        if any(attr_name.startswith(prefix.rstrip('*')) for prefix in dynamic_attrs_to_remove):
            attrs_to_remove.append(attr_name)
        # Remove inline event handlers (often have dynamic values)
        elif attr_name.startswith('on'):
            attrs_to_remove.append(attr_name)

    for attr_name in attrs_to_remove:
        del tag[attr_name]

    # Normalize tracking pixel src (1x1 images with session params)
    if tag.name == 'img':
        src = tag.get('src', '')
        if isinstance(src, str) and ('pixel' in src or 'beacon' in src or '1x1' in src
                                      or 'tracking' in src or 'impression' in src):
            tag['src'] = '[TRACKING_PIXEL]'
        # Also normalize very small width/height images (likely tracking pixels)
        width = tag.get('width', '')
        height = tag.get('height', '')
        if (str(width) in ('0', '1') and str(height) in ('0', '1')):
            tag['src'] = '[TRACKING_PIXEL]'

    # Normalize link[rel=preconnect/prefetch/preload] - order changes are noise
    if tag.name == 'link' and tag.get('rel'):
        rel_values = tag.get('rel', [])
        if isinstance(rel_values, list):
            rel_str = ' '.join(rel_values)
        else:
            rel_str = str(rel_values)
        if any(r in rel_str for r in ['preconnect', 'prefetch', 'preload', 'dns-prefetch']):
            # Keep the tag structure but normalize the href
            if 'href' in tag.attrs:
                tag['href'] = '[PRELOAD_URL]'


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
