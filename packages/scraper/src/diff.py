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

# Pattern to normalize numeric counts in meta content (e.g., "8,526件", "541,874台")
_META_NUMERIC_PATTERN = re.compile(
    r'[\d,]+(?:\.\d+)?\s*(?:件|棟|戸|台|室|区画|物件|軒|人|万|円|m²|㎡)'
)

# Patterns identifying recommend/related property sections (class or id)
_RECOMMEND_SECTION_PATTERNS = re.compile(
    r'recommend|おすすめ|関連|人気|ランキング|新着|pickup|similar|related|suggest',
    re.IGNORECASE,
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
    - Appends a normalization version marker for compatibility detection
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

    # Normalize meta tag content: replace numeric counts (e.g., "8,526件" → "[NUM]件")
    for meta in soup.find_all('meta'):
        content = meta.get('content', '')
        if content and isinstance(content, str):
            normalized_content = _META_NUMERIC_PATTERN.sub('[NUM]', content)
            if normalized_content != content:
                meta['content'] = normalized_content

    # Normalize links inside recommend/related sections
    # (property IDs in hrefs change daily as listings rotate)
    for tag in soup.find_all(True, attrs={'class': True}):
        classes = tag.get('class', [])
        if isinstance(classes, list):
            class_str = ' '.join(classes)
        else:
            class_str = str(classes)
        # Also check id attribute
        tag_id = tag.get('id', '') or ''
        combined = f"{class_str} {tag_id}"
        if _RECOMMEND_SECTION_PATTERNS.search(combined):
            # Normalize all hrefs within this section
            for link in tag.find_all('a', href=True):
                link['href'] = '[RECOMMEND_LINK]'
            # Also normalize image srcs (property thumbnails)
            for img in tag.find_all('img', src=True):
                img['src'] = '[RECOMMEND_IMG]'

    # Selectively normalize text content:
    # - Keep text in CRO-significant elements (buttons, headings, links, labels)
    # - Replace text in property-specific / noise elements with [TEXT]
    for text_node in soup.find_all(string=True):
        if text_node.parent and text_node.parent.name not in ['script', 'style']:
            if _should_preserve_text(text_node.parent):
                # Check if preserved text contains property-specific noise
                text_content = str(text_node).strip()
                if text_content and _PROPERTY_NOISE_RE.search(text_content):
                    # Property-specific text even in CRO element → normalize
                    text_node.replace_with('[PROPERTY_TEXT]')
                # else: Keep the text as-is (CRO-significant)
            else:
                text_node.replace_with('[TEXT]')

    # Append normalization version marker for future compatibility detection
    result = str(soup)
    result += "\n<!-- NORM_V2 -->"
    return result


# Normalization version marker used to detect snapshots saved with current logic
NORM_VERSION_MARKER = "<!-- NORM_V2 -->"


# Tags whose text content is CRO-significant and should be preserved for diff
_CRO_SIGNIFICANT_TAGS = frozenset([
    'button', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'label', 'legend', 'th', 'caption', 'summary',
    'nav',  # Navigation text changes matter
])

# class/role patterns indicating CRO-significant interactive elements
_CRO_SIGNIFICANT_PATTERNS = [
    'btn', 'button', 'cta', 'submit', 'action',
    'tab', 'nav', 'menu', 'breadcrumb',
    'badge', 'tag', 'chip', 'alert', 'toast',
]

# Patterns in text content that indicate property-specific noise
# (even if inside a CRO-significant tag like a link)
_PROPERTY_NOISE_PATTERNS = [
    r'\d{1,4}万円',         # 価格 (e.g., 1500万円)
    r'\d+\.\d+万円',       # 価格 (e.g., 5.5万円)
    r'\d+円',              # 価格 (e.g., 85000円)
    r'築\d+年',            # 築年数
    r'\d+階建',            # 階数
    r'\d+[LDK]+',          # 間取り
    r'\d+\.\d+m²',         # 面積
    r'\d+㎡',              # 面積
    r'20\d{2}/\d{1,2}/\d{1,2}',  # 日付
    r'20\d{2}年\d{1,2}月',       # 日付
]

_PROPERTY_NOISE_RE = re.compile('|'.join(_PROPERTY_NOISE_PATTERNS))


def _should_preserve_text(tag: Tag) -> bool:
    """Determine if text content within this tag is CRO-significant.

    Returns True if the text should be preserved for diff comparison
    (buttons, headings, links, etc.), False if it should be replaced with [TEXT].
    """
    if not tag or not tag.name:
        return False

    # Direct match on tag name
    if tag.name in _CRO_SIGNIFICANT_TAGS:
        return True

    # Check role attribute
    role = tag.get('role', '')
    if role in ('button', 'tab', 'menuitem', 'link', 'heading', 'navigation'):
        return True

    # Check if any ancestor is a CRO-significant tag (e.g., span inside a button)
    for parent in tag.parents:
        if parent.name in _CRO_SIGNIFICANT_TAGS:
            return True
        # Stop at reasonable depth to avoid performance issues
        if parent.name in ('body', 'html', '[document]'):
            break

    # Check class names for CRO-significant patterns
    classes = tag.get('class', [])
    if isinstance(classes, list):
        class_str = ' '.join(classes).lower()
    else:
        class_str = str(classes).lower()

    if any(pattern in class_str for pattern in _CRO_SIGNIFICANT_PATTERNS):
        return True

    return False


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

    # SPA rendering timing mitigation:
    # If the diff is purely deletions (no additions) and the deleted portion is small
    # relative to the total structure, it's likely a SPA section that didn't render in time.
    # Threshold: <3% of total lines and only deletions → treat as no change.
    total_lines = max(len(old_lines), 1)
    if additions == 0 and deletions > 0 and (deletions / total_lines) < 0.03:
        return None
    # Similarly, pure additions of <3% may be a section that rendered extra this time
    if deletions == 0 and additions > 0 and (additions / total_lines) < 0.03:
        return None

    return {
        "has_changes": True,
        "diff_text": diff_text,
        "additions": additions,
        "deletions": deletions,
        "old_length": len(old_structure),
        "new_length": len(new_structure),
    }
