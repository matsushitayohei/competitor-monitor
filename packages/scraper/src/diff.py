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
    '.searchitem-list-value',   # SUUMO: station listing counts e.g. "(328)" — change daily
    # SUUMO detail page: property-specific info blocks
    '.detailPage-priceInfo',
    '.detailPage-roomInfo',
    '.detailPage-mainInfo',
    '.bukken-detail-main-info',
    # SUUMO search/top: property cassette cards (content rotates daily)
    # NOTE: Using specific class names only — [class*="cassette"] is intentionally avoided
    # because cassetteitem_header / cassetteitem_label contain structural UI info worth detecting.
    '.cassette',
    '.p-cassette',
    # athome specific
    '.price',
    '.detail-price',
    # Canary (React component naming) — detail property info
    '[class*="PropertyDetail_price"]',
    '[class*="PropertyDetail_address"]',
    '[class*="PropertyDetail_room"]',
    '[class*="PropertyDetail_floor"]',
    # Canary search/top: recommend item cards
    '[class*="RecommendItem"]',
    '[class*="PickupItem"]',
    '[class*="FeaturedItem"]',
    # Homes detail page: property-specific info blocks
    '.property-detail__price',
    '.property-detail__floor-plan',
    '.property-detail__address',
    # Homes search/top: search result item content (property names/prices inside cards)
    '.search-result-item-content',
    # Recommend / pickup sections across all services (content rotates daily)
    '.recommend-item',
    '.pickup-item',
    '[class*="recommend-item"]',
    '[class*="pickup-item"]',
    # Campaign and ad banners (content changes frequently, not structural)
    '.campaign-banner',
    '.p-campaign',
    '[class*="campaign-banner"]',
    '[class*="CampaignBanner"]',
    '[class*="ad-area"]',
    '[class*="AdArea"]',
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

# Pattern to normalize property IDs embedded in URLs
# e.g., /property/12345678/ → /property/[PROP_ID]/
# Covers SUUMO, Homes, Canary, athome URL patterns.
# Minimum 7 digits to avoid false-positives on short category IDs.
_PROPERTY_ID_IN_URL = re.compile(
    r'(/(?:property|bukken|room|chintai|mansion|kodate|tochi|bld|jnc|nc)/)\d{7,}([/?#]|$)'
)

# Patterns identifying recommend/related property sections (class or id)
_RECOMMEND_SECTION_PATTERNS = re.compile(
    r'recommend|おすすめ|関連|人気|ランキング|新着|pickup|similar|related|suggest',
    re.IGNORECASE,
)

# Normalization version marker — bumped each time extract_structure logic changes.
# main.py uses this to detect old snapshots and skip comparison (baseline_reset).
# V4 changes vs V3:
#   - EXCLUDE_SELECTORS: added SUUMO cassette cards, Canary React component selectors,
#     Homes detail blocks, recommend/pickup/campaign/ad-area selectors across all services
#   - _PROPERTY_NOISE_PATTERNS: added comma-price (85,000円), X万円 standalone, 万千円 form,
#     decimal area (0.5㎡)
#   - _normalize_asset_url: added property ID normalization (/property/12345678/ → [PROP_ID])
# V3 changes vs V2:
#   - meta[name="description"] / og:description content → [META_DESCRIPTION]
#   - meta[name="keywords"] content → [META_KEYWORDS]
#   - .searchitem-list-value (SUUMO station counts) → removed from DOM
NORM_VERSION_MARKER = "<!-- NORM_V4 -->"


def _normalize_asset_url(tag: Tag, val: str) -> str:
    """Normalize dynamic segments in asset URLs (build hashes, cache busters, property IDs)."""
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

    # Normalize property IDs in URLs (listing-specific numeric IDs change daily)
    result = _PROPERTY_ID_IN_URL.sub(r'\1[PROP_ID]\2', result)

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

    # Normalize meta tag content
    for meta in soup.find_all('meta'):
        content = meta.get('content', '')
        if not content or not isinstance(content, str):
            continue
        meta_name = meta.get('name', '').lower()
        meta_prop = meta.get('property', '').lower()

        # description / og:description contain property-specific text (room names,
        # addresses, area info) that changes whenever the monitored URL rotates to a
        # new listing.  Replace entirely to avoid spurious daily diffs.
        if meta_name in ('description', 'og:description') or meta_prop in ('og:description',):
            meta['content'] = '[META_DESCRIPTION]'
            continue

        # keywords: may contain property-specific terms, normalize to suppress noise
        if meta_name == 'keywords':
            meta['content'] = '[META_KEYWORDS]'
            continue

        # For all other meta content: normalize numeric counts (e.g., "8,526件" → "[NUM]件")
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
    result += f"\n{NORM_VERSION_MARKER}"
    return result


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
    r'\d{1,4}万円',              # 価格 (e.g., 1500万円)
    r'\d+\.\d+万円',             # 価格 (e.g., 5.5万円)
    r'\d+万\d+千円',             # 価格 (e.g., 12万5千円)
    r'\d+,\d+円',                # コンマ区切り価格 (e.g., 85,000円)
    r'\d+円',                    # 価格 (e.g., 85000円)
    r'[0-9.]+万円',              # X万円 単体 (e.g., 8.5万円) — 「万件」等は除外
    r'築\d+年',                  # 築年数
    r'\d+階建',                  # 階数
    r'\d+[LDK]+',                # 間取り
    r'\d+\.\d+m²',               # 面積
    r'\d+㎡',                    # 面積
    r'\d+\.\d+㎡',               # 面積 (小数点あり)
    r'20\d{2}/\d{1,2}/\d{1,2}', # 日付
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


# ──────────────────────────────────────────────────────────────────
# Access-blocked page detection
# ──────────────────────────────────────────────────────────────────

# GeeTest / reCAPTCHA / Cloudflare challenge の指紋
_CAPTCHA_PATTERNS = [
    # GeeTest（athome で確認）
    r'geetest_holder',
    r'geetest_radar',
    r'static\.geetest\.com',
    # reCAPTCHA
    r'<div[^>]*class="g-recaptcha"',
    r'www\.google\.com/recaptcha',
    # hCaptcha
    r'<div[^>]*class="h-captcha"',
    r'hcaptcha\.com',
    # Cloudflare challenge
    r'cf-browser-verification',
    r'cf_clearance',
    r'Checking your browser',
    r'cf-challenge',
    # 汎用：認証要求の日本語メッセージ
    r'認証にご協力ください',
    r'ロボットによるアクセスと判断',
    r'アクセスが一時的に制限',
]

_CAPTCHA_RE = re.compile('|'.join(_CAPTCHA_PATTERNS), re.IGNORECASE)


def detect_access_blocked_page(html: str) -> str | None:
    """Detect CAPTCHA / bot-challenge pages that return HTTP 200 but no real content.

    Returns a short reason string when a challenge page is detected, or None if
    the page appears to contain genuine content.

    This prevents saving CAPTCHA snapshots as baseline and issuing spurious
    "no change" verdicts when the site is always blocking the scraper.

    Args:
        html: Raw HTML of the fetched page.

    Returns:
        A reason string (e.g. 'GeeTest CAPTCHA') or None.
    """
    match = _CAPTCHA_RE.search(html)
    if match:
        matched_text = match.group(0)
        if 'geetest' in matched_text.lower():
            return 'GeeTest CAPTCHA'
        if 'recaptcha' in matched_text.lower():
            return 'reCAPTCHA'
        if 'hcaptcha' in matched_text.lower():
            return 'hCaptcha'
        if 'cf-' in matched_text.lower() or 'Checking' in matched_text:
            return 'Cloudflare challenge'
        return f'access challenge ({matched_text[:40]})'
    return None
