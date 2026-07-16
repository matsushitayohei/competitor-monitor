"""Expired/delisted property page detection module.

Real estate portal sites typically return HTTP 200 for expired property pages,
showing a "this listing has ended" message instead of a 404 error.
This module detects such pages by checking HTML content for known patterns.
"""

import re
from typing import Optional


# Service-specific patterns indicating a property listing has expired.
# Each entry is a list of (pattern, weight) tuples.
# If total matched weight >= threshold, the page is considered expired.
EXPIRED_PATTERNS: dict[str, list[tuple[str, int]]] = {
    "suumo": [
        # Common SUUMO expired page patterns
        (r"掲載期間が終了", 10),
        (r"この物件の掲載は終了しました", 10),
        (r"この物件の掲載期間は終了", 10),
        (r"掲載が終了した物件", 8),
        (r"現在公開されていません", 8),
        (r"公開が終了しています", 8),
        (r"類似物件を探す", 3),
        (r"お探しの物件は見つかりませんでした", 8),
        (r"こちらの物件情報は掲載を終了", 10),
    ],
    "athome": [
        # Common athome expired page patterns
        (r"掲載期間が終了", 10),
        (r"この物件の掲載は終了", 10),
        (r"掲載終了", 6),
        (r"この物件情報は掲載が終了", 10),
        (r"掲載が終了しています", 10),
        (r"物件の掲載期間が終了", 10),
        (r"現在この物件は公開されて", 8),
        (r"類似のおすすめ物件", 3),
        (r"この物件は現在掲載されて", 8),
        (r"お探しの物件情報の掲載は終了", 10),
    ],
    "canary": [
        # Common Canary expired page patterns
        (r"掲載終了", 6),
        (r"この物件は掲載が終了", 10),
        (r"掲載期間が終了", 10),
        (r"募集が終了", 8),
        (r"現在募集していません", 8),
        (r"この部屋の募集は終了", 10),
    ],
}

# Threshold for considering a page as expired
EXPIRED_THRESHOLD = 8

# Generic patterns applicable to all services (lower weight)
GENERIC_EXPIRED_PATTERNS: list[tuple[str, int]] = [
    (r"掲載期間.*?終了", 8),
    (r"掲載.*?終了.*?物件", 6),
    (r"この物件.*?終了", 8),
    (r"物件情報.*?掲載.*?終了", 8),
    (r"募集.*?終了", 5),
    (r"公開.*?終了", 5),
]


def is_expired_page(html: str, service_name: str) -> bool:
    """Detect if the page content indicates an expired/delisted property.

    Args:
        html: The full HTML content of the page.
        service_name: Service identifier (suumo, athome, canary).

    Returns:
        True if the page appears to be an expired listing page.
    """
    service_key = service_name.lower()

    # Get service-specific patterns
    patterns = EXPIRED_PATTERNS.get(service_key, [])

    # Add generic patterns
    all_patterns = patterns + GENERIC_EXPIRED_PATTERNS

    total_weight = 0
    matched_patterns: list[str] = []

    for pattern, weight in all_patterns:
        if re.search(pattern, html):
            total_weight += weight
            matched_patterns.append(pattern)
            # Early exit if threshold already met
            if total_weight >= EXPIRED_THRESHOLD:
                break

    is_expired = total_weight >= EXPIRED_THRESHOLD

    if is_expired:
        print(f"    [Expired Detector] Page detected as expired (score: {total_weight})")
        print(f"    [Expired Detector] Matched patterns: {matched_patterns[:3]}")
    
    return is_expired


def detect_expired_reason(html: str, service_name: str) -> Optional[str]:
    """Extract the expiration reason text from the page, if detectable.

    Args:
        html: The full HTML content of the page.
        service_name: Service identifier.

    Returns:
        A short description of the expiration, or None.
    """
    # Try to find the main expiration message
    common_patterns = [
        r"(この物件[^。「」\n]{0,30}(?:終了|ません))",
        r"(掲載期間[^。「」\n]{0,30}終了)",
        r"(掲載が終了[^。「」\n]{0,20})",
        r"(物件情報[^。「」\n]{0,30}終了)",
    ]

    for pattern in common_patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1).strip()

    return None
