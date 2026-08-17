"""CV (Conversion) Element Detector - Identifies conversion-related UI elements.

Detects:
- CTAs (primary, secondary, LINE, telephone)
- Social proof (view counts, review counts, inquiry counts)
- Urgency indicators (remaining count, limited time)
- Sticky/fixed CTAs
- Micro-copy (reassurance text near CTAs)
"""

import re
from bs4 import BeautifulSoup, Tag


# --- CTA Detection ---

_CTA_CLASS_PATTERNS = re.compile(
    r"btn-primary|btn-main|cta-primary|cta-main|button-primary"
    r"|btn-secondary|btn-sub|cta-secondary"
    r"|btn-line|line-btn|line-button"
    r"|btn-tel|tel-btn|phone-btn",
    re.IGNORECASE,
)

_CTA_TEXT_PATTERNS = re.compile(
    r"問い合わせ|お問合せ|資料請求|見学予約|内見予約|内覧予約"
    r"|申し込[みむ]|申込|予約する|相談する|無料相談"
    r"|今すぐ|LINEで|電話で|メールで"
    r"|お気に入り|保存する|比較する",
)

# --- Social Proof Patterns ---

_SOCIAL_PROOF_CLASS = re.compile(
    r"review|rating|star|score|count|popular|favorite|bookmark",
    re.IGNORECASE,
)

_SOCIAL_PROOF_TEXT = re.compile(
    r"(\d+)人が(閲覧|問い合わせ|お気に入り|検討|保存)"
    r"|閲覧数\s*(\d+)|お気に入り\s*(\d+)"
    r"|レビュー\s*(\d+)|★\s*[\d.]+"
    r"|満足度\s*[\d.]+|評価\s*[\d.]+"
    r"|本日(\d+)人|今日(\d+)人",
)

# --- Urgency Patterns ---

_URGENCY_TEXT = re.compile(
    r"残り\s*(\d+)|あと\s*(\d+)"
    r"|期間限定|本日限り|今だけ|お早めに"
    r"|急募|即入居|すぐ入居|即日"
    r"|人気物件|注目|おすすめ"
    r"|(\d+)日以内|本日中",
)

# --- Micro-copy Patterns ---

_MICRO_COPY_TEXT = re.compile(
    r"無料で|しつこい.*ません|営業.*ません"
    r"|安心.*ください|ご安心|簡単|かんたん"
    r"|\d+分で完了|\d+秒で完了|すぐ終わ"
    r"|個人情報.*保護|プライバシー|SSL"
    r"|無理な勧誘.*ません|迷惑.*ません"
    r"|いつでもキャンセル|気軽に",
)

# --- Sticky/Fixed Detection ---

_STICKY_STYLE_RE = re.compile(r"position\s*:\s*(fixed|sticky)", re.IGNORECASE)
_STICKY_CLASS_RE = re.compile(r"fixed|sticky|float|pin|dock", re.IGNORECASE)


def detect_cv_elements(html: str) -> dict:
    """Detect all conversion-related elements on a page.

    Returns:
        {
            "cvPoints": [...],
            "summary": {
                "totalCtaCount": int,
                "stickyCtaCount": int,
                "socialProofCount": int,
                "urgencyCount": int,
                "microCopyCount": int,
                "hasMicroCopy": bool,
            }
        }
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove non-visual elements
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    cv_points = []

    # 1. Detect CTAs
    cv_points.extend(_detect_ctas(soup))

    # 2. Detect social proof
    cv_points.extend(_detect_social_proof(soup))

    # 3. Detect urgency
    cv_points.extend(_detect_urgency(soup))

    # 4. Detect micro-copy
    cv_points.extend(_detect_micro_copy(soup))

    # Build summary
    cta_count = sum(1 for p in cv_points if p["type"].startswith("cta_") or p["type"] == "button_submit")
    sticky_cta_count = sum(1 for p in cv_points if p.get("isSticky", False))
    social_proof_count = sum(1 for p in cv_points if p["type"] == "social_proof")
    urgency_count = sum(1 for p in cv_points if p["type"] == "urgency")
    micro_copy_count = sum(1 for p in cv_points if p["type"] == "micro_copy")

    return {
        "cvPoints": cv_points,
        "summary": {
            "totalCtaCount": cta_count,
            "stickyCtaCount": sticky_cta_count,
            "socialProofCount": social_proof_count,
            "urgencyCount": urgency_count,
            "microCopyCount": micro_copy_count,
            "hasMicroCopy": micro_copy_count > 0,
        },
    }


def _detect_ctas(soup: BeautifulSoup) -> list[dict]:
    """Detect CTA elements (buttons, links with action intent)."""
    ctas = []
    seen_labels = set()

    # Submit buttons
    for btn in soup.find_all(["button", "input"], attrs={"type": "submit"}):
        label = _get_element_label(btn)
        if label and label not in seen_labels:
            seen_labels.add(label)
            ctas.append(_build_cta(btn, "primary_cta", label))

    # Button elements (non-submit)
    for btn in soup.find_all("button"):
        if btn.get("type") == "submit":
            continue
        label = btn.get_text(strip=True)[:50]
        if label and _CTA_TEXT_PATTERNS.search(label) and label not in seen_labels:
            seen_labels.add(label)
            ctas.append(_build_cta(btn, "secondary_cta", label))

    # Links that look like CTAs
    for a in soup.find_all("a"):
        href = a.get("href", "")
        label = a.get_text(strip=True)[:50]
        classes = " ".join(a.get("class", []))

        if not label:
            continue

        # LINE CTA
        if href and "line.me" in href:
            if label not in seen_labels:
                seen_labels.add(label)
                ctas.append(_build_cta(a, "line_cta", label))
            continue

        # Tel CTA
        if href and href.startswith("tel:"):
            if label not in seen_labels:
                seen_labels.add(label)
                ctas.append(_build_cta(a, "tel_cta", label))
            continue

        # CTA by class
        if _CTA_CLASS_PATTERNS.search(classes):
            if label not in seen_labels:
                seen_labels.add(label)
                cta_type = "primary_cta" if "primary" in classes.lower() else "secondary_cta"
                ctas.append(_build_cta(a, cta_type, label))
            continue

        # CTA by text
        if _CTA_TEXT_PATTERNS.search(label):
            if label not in seen_labels:
                seen_labels.add(label)
                ctas.append(_build_cta(a, "secondary_cta", label))

    return ctas


def _build_cta(tag: Tag, cta_type: str, label: str) -> dict:
    """Build a CTA cv_point dict."""
    is_sticky = _is_sticky(tag)
    position = _determine_position(tag)

    # Try to get associated micro-copy
    micro_copy = _find_nearby_micro_copy(tag)

    # Try to get associated social proof
    social_proof = _find_nearby_social_proof(tag)

    # Extract basic style info from class
    classes = tag.get("class", [])
    class_str = " ".join(classes) if isinstance(classes, list) else str(classes or "")

    return {
        "type": cta_type,
        "element": tag.name,
        "label": label,
        "position": position,
        "isSticky": is_sticky,
        "className": class_str[:100],
        "microCopy": micro_copy,
        "socialProof": social_proof,
    }


def _detect_social_proof(soup: BeautifulSoup) -> list[dict]:
    """Detect social proof elements."""
    proofs = []
    seen_texts = set()

    # By class
    for tag in soup.find_all(True):
        classes = tag.get("class", [])
        class_str = " ".join(classes) if isinstance(classes, list) else str(classes or "")
        if _SOCIAL_PROOF_CLASS.search(class_str):
            text = tag.get_text(strip=True)[:100]
            if text and text not in seen_texts:
                seen_texts.add(text)
                proofs.append({
                    "type": "social_proof",
                    "element": tag.name,
                    "text": text,
                    "position": _determine_position(tag),
                    "isSticky": _is_sticky(tag),
                })

    # By text content
    for tag in soup.find_all(["span", "p", "div", "strong", "em", "small"]):
        text = tag.get_text(strip=True)
        if text and _SOCIAL_PROOF_TEXT.search(text) and text not in seen_texts:
            seen_texts.add(text[:100])
            proofs.append({
                "type": "social_proof",
                "element": tag.name,
                "text": text[:100],
                "position": _determine_position(tag),
                "isSticky": False,
            })

    return proofs[:10]  # Limit


def _detect_urgency(soup: BeautifulSoup) -> list[dict]:
    """Detect urgency/scarcity indicators."""
    urgencies = []
    seen_texts = set()

    for tag in soup.find_all(["span", "p", "div", "strong", "em", "small", "li"]):
        text = tag.get_text(strip=True)
        if text and _URGENCY_TEXT.search(text) and text[:80] not in seen_texts:
            # Avoid nested duplicates
            parent = tag.parent
            if parent and isinstance(parent, Tag):
                parent_text = parent.get_text(strip=True)
                if parent_text[:80] in seen_texts:
                    continue

            seen_texts.add(text[:80])
            urgencies.append({
                "type": "urgency",
                "element": tag.name,
                "text": text[:100],
                "position": _determine_position(tag),
                "isSticky": _is_sticky(tag),
            })

    return urgencies[:10]


def _detect_micro_copy(soup: BeautifulSoup) -> list[dict]:
    """Detect micro-copy (reassurance text near CTAs/forms)."""
    copies = []
    seen_texts = set()

    for tag in soup.find_all(["p", "span", "small", "div", "em", "strong"]):
        text = tag.get_text(strip=True)
        if text and _MICRO_COPY_TEXT.search(text) and text[:80] not in seen_texts:
            seen_texts.add(text[:80])
            copies.append({
                "type": "micro_copy",
                "element": tag.name,
                "text": text[:100],
                "position": _determine_position(tag),
                "isSticky": False,
            })

    return copies[:10]


def _is_sticky(tag: Tag) -> bool:
    """Check if element or its container is sticky/fixed."""
    # Check inline style
    style = tag.get("style", "")
    if isinstance(style, str) and _STICKY_STYLE_RE.search(style):
        return True

    # Check class
    classes = tag.get("class", [])
    class_str = " ".join(classes) if isinstance(classes, list) else str(classes or "")
    if _STICKY_CLASS_RE.search(class_str):
        return True

    # Check ancestors (up to 3 levels)
    depth = 0
    for parent in tag.parents:
        if depth >= 3:
            break
        if not isinstance(parent, Tag):
            continue
        parent_style = parent.get("style", "")
        if isinstance(parent_style, str) and _STICKY_STYLE_RE.search(parent_style):
            return True
        parent_classes = parent.get("class", [])
        parent_class_str = " ".join(parent_classes) if isinstance(parent_classes, list) else str(parent_classes or "")
        if _STICKY_CLASS_RE.search(parent_class_str):
            return True
        depth += 1

    return False


def _determine_position(tag: Tag) -> str:
    """Determine the position context of an element."""
    # Check if in fixed bottom bar
    if _is_sticky(tag):
        # Check if bottom-positioned
        style = tag.get("style", "")
        for parent in [tag] + list(tag.parents)[:3]:
            if not isinstance(parent, Tag):
                continue
            p_style = parent.get("style", "")
            p_classes = " ".join(parent.get("class", []))
            if "bottom" in str(p_style).lower() or "bottom" in p_classes.lower():
                return "fixed_bottom"
            if "top" in str(p_style).lower() or "header" in p_classes.lower():
                return "fixed_top"
        return "fixed"

    # Check if inside form
    if tag.find_parent("form"):
        return "in_form"

    # Check if in header
    if tag.find_parent("header"):
        return "header"

    # Check if in footer
    if tag.find_parent("footer"):
        return "footer"

    # Check if in nav
    if tag.find_parent("nav"):
        return "navigation"

    return "body"


def _get_element_label(tag: Tag) -> str:
    """Get the label/text of an element."""
    if tag.name == "input":
        return tag.get("value", "送信")[:50]
    return tag.get_text(strip=True)[:50]


def _find_nearby_micro_copy(tag: Tag) -> str:
    """Find micro-copy text near a CTA element."""
    # Check next siblings
    for sibling in tag.find_next_siblings(limit=3):
        if isinstance(sibling, Tag):
            text = sibling.get_text(strip=True)
            if text and _MICRO_COPY_TEXT.search(text):
                return text[:100]

    # Check parent's children
    parent = tag.parent
    if parent:
        for child in parent.find_all(["small", "span", "p"], recursive=False):
            text = child.get_text(strip=True)
            if text and _MICRO_COPY_TEXT.search(text):
                return text[:100]

    return ""


def _find_nearby_social_proof(tag: Tag) -> str:
    """Find social proof text near a CTA element."""
    parent = tag.parent
    if parent:
        for child in parent.find_all(["span", "p", "div", "small"], recursive=False):
            text = child.get_text(strip=True)
            if text and _SOCIAL_PROOF_TEXT.search(text):
                return text[:100]
    return ""
