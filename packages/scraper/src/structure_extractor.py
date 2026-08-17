"""UIUX Structure Extractor - Extracts component-level page structure from HTML.

Produces a hierarchical JSON representation:
- Level 1 (summary): Section count, component count, CTA count, etc.
- Level 2 (sections): Each section with its components
- Level 3 (components): Individual UI components with attributes
"""

import hashlib
import re
from typing import Optional
from bs4 import BeautifulSoup, Tag


# --- Section Detection ---

# Tags that naturally define sections
SECTION_TAGS = frozenset([
    "header", "footer", "nav", "main", "aside", "section", "article", "form",
])

# Class patterns that indicate a logical section (when tag is div)
SECTION_CLASS_PATTERNS = [
    r"hero", r"banner", r"sidebar", r"content", r"wrapper",
    r"container", r"panel", r"block", r"module", r"widget",
    r"modal", r"drawer", r"overlay", r"toolbar", r"bottom-bar",
    r"fixed-(?:top|bottom)", r"sticky",
]

_SECTION_CLASS_RE = re.compile("|".join(SECTION_CLASS_PATTERNS), re.IGNORECASE)


# --- Component Classification ---

COMPONENT_RULES: dict[str, list[str]] = {
    # Form elements (CV-critical)
    "input_text": [
        "input[type=text]", "input[type=email]", "input[type=name]",
        "input:not([type])",  # default type is text
    ],
    "input_tel": ["input[type=tel]"],
    "input_number": ["input[type=number]"],
    "input_password": ["input[type=password]"],
    "input_date": ["input[type=date]", "input[type=datetime-local]"],
    "input_hidden": ["input[type=hidden]"],
    "textarea": ["textarea"],
    "select": ["select"],
    "checkbox": ["input[type=checkbox]"],
    "radio": ["input[type=radio]"],
    "button_submit": ["button[type=submit]", "input[type=submit]"],
    "button_action": ["button:not([type=submit]):not([type=reset])"],

    # CTA elements
    "cta_link": [],  # Detected by heuristic (see _classify_link)

    # Media
    "image_carousel": [],  # Detected by class pattern
    "image_single": ["img"],
    "video": ["video"],

    # Navigation
    "breadcrumb": [],  # Detected by class/aria
    "pagination": [],  # Detected by class
    "tab_nav": [],  # Detected by role/class

    # Sticky/Fixed elements
    "sticky_element": [],  # Detected by computed style in class

    # Information display
    "table": ["table"],
    "accordion": ["details"],
    "list": ["ul", "ol"],

    # Social proof / urgency (detected by text/class heuristics)
    "social_proof": [],
    "urgency": [],
    "micro_copy": [],
}

# Class patterns for carousel/slider detection
_CAROUSEL_PATTERNS = re.compile(
    r"carousel|slider|swiper|gallery|lightbox|slide-show",
    re.IGNORECASE,
)

# Class patterns for CTA detection
_CTA_CLASS_PATTERNS = re.compile(
    r"btn|button|cta|action|submit|inquiry|contact|apply|register|signup",
    re.IGNORECASE,
)

# Class patterns for sticky/fixed detection
_STICKY_CLASS_PATTERNS = re.compile(
    r"sticky|fixed|float|pin",
    re.IGNORECASE,
)

# Class patterns for social proof
_SOCIAL_PROOF_PATTERNS = re.compile(
    r"review.count|view.count|favorite.count|popular|rating|star|score",
    re.IGNORECASE,
)

# Text patterns for urgency
_URGENCY_TEXT_PATTERNS = re.compile(
    r"残り\d|あと\d|期間限定|本日限り|急いで|お早めに|人気|即入居|すぐ",
)

# Text patterns for micro-copy (reassurance)
_MICRO_COPY_PATTERNS = re.compile(
    r"無料|しつこい.*ません|営業.*ません|安心|簡単|かんたん|\d+分で|すぐに|今すぐ",
)

# Elements to skip entirely
_SKIP_TAGS = frozenset(["script", "style", "noscript", "iframe", "svg", "path"])


def extract_page_structure(html: str) -> dict:
    """Extract hierarchical page structure from HTML.

    Returns:
        {
            "summary": {...},
            "sections": [...],
        }
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove non-visual elements
    for tag in soup.find_all(_SKIP_TAGS):
        tag.decompose()

    body = soup.find("body")
    if not body:
        body = soup

    # Extract sections
    sections = _extract_sections(body)

    # Build summary
    total_components = sum(len(s.get("components", [])) for s in sections)
    form_count = sum(1 for s in sections if s["type"] == "form")
    cta_count = sum(
        1 for s in sections
        for c in s.get("components", [])
        if c["type"].startswith("cta_") or c["type"] == "button_submit"
    )
    has_sticky = any(
        c["type"] == "sticky_element" or c.get("isSticky", False)
        for s in sections
        for c in s.get("components", [])
    )

    summary = {
        "sectionCount": len(sections),
        "componentCount": total_components,
        "formCount": form_count,
        "ctaCount": cta_count,
        "hasStickyElements": has_sticky,
    }

    return {
        "summary": summary,
        "sections": sections,
    }


def compute_structure_hash(structure: dict) -> str:
    """Compute a stable hash of the structure for change detection."""
    import json
    # Sort keys for stability
    canonical = json.dumps(structure, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _extract_sections(body: Tag) -> list[dict]:
    """Extract logical sections from the page body."""
    sections = []
    section_index = 0

    # First, find explicit section elements
    for child in body.children:
        if not isinstance(child, Tag):
            continue

        if child.name in _SKIP_TAGS:
            continue

        section = _tag_to_section(child, section_index)
        if section:
            sections.append(section)
            section_index += 1

    # If no sections found (flat structure), treat top-level divs as sections
    if not sections:
        for child in body.find_all(True, recursive=False):
            if child.name in _SKIP_TAGS:
                continue
            section = _tag_to_section(child, section_index)
            if section:
                sections.append(section)
                section_index += 1

    return sections


def _tag_to_section(tag: Tag, index: int) -> Optional[dict]:
    """Convert a top-level tag to a section dict."""
    if tag.name in _SKIP_TAGS:
        return None

    # Determine section type
    section_type = _classify_section(tag)

    # Extract components within this section
    components = _extract_components(tag)

    # Skip empty sections (no meaningful components)
    if not components and section_type == "div":
        # Check if it has child sections (nested structure)
        child_sections = tag.find_all(SECTION_TAGS, recursive=False)
        if not child_sections:
            return None

    section = {
        "id": f"section-{index}",
        "type": section_type,
        "tagName": tag.name,
        "position": index,
        "components": components,
    }

    # Add class info for identification
    classes = tag.get("class", [])
    if classes:
        section["className"] = " ".join(classes) if isinstance(classes, list) else classes

    # Check for sticky/fixed positioning
    style = tag.get("style", "")
    if isinstance(style, str) and ("position: fixed" in style or "position: sticky" in style):
        section["isSticky"] = True

    return section


def _classify_section(tag: Tag) -> str:
    """Classify what type of section this tag represents."""
    if tag.name in SECTION_TAGS:
        return tag.name

    # Check role attribute
    role = tag.get("role", "")
    if role in ("banner", "navigation", "main", "contentinfo", "complementary"):
        role_map = {
            "banner": "header",
            "navigation": "nav",
            "main": "main",
            "contentinfo": "footer",
            "complementary": "aside",
        }
        return role_map.get(role, "div")

    # Check class patterns
    classes = tag.get("class", [])
    class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
    if _SECTION_CLASS_RE.search(class_str):
        # Return more specific type based on class
        class_lower = class_str.lower()
        if "hero" in class_lower or "banner" in class_lower:
            return "hero"
        if "sidebar" in class_lower:
            return "aside"
        if "modal" in class_lower or "drawer" in class_lower or "overlay" in class_lower:
            return "modal"
        if "toolbar" in class_lower or "bottom-bar" in class_lower:
            return "toolbar"
        if "fixed" in class_lower or "sticky" in class_lower:
            return "fixed_element"

    return "div"


def _extract_components(section_tag: Tag) -> list[dict]:
    """Extract all classifiable components from a section."""
    components = []
    comp_index = 0

    # Process all descendant elements
    for tag in section_tag.find_all(True):
        if tag.name in _SKIP_TAGS:
            continue

        component = _classify_component(tag)
        if component:
            component["position"] = comp_index
            components.append(component)
            comp_index += 1

    return components


def _classify_component(tag: Tag) -> Optional[dict]:
    """Classify a single DOM element as a component. Returns None if not classifiable."""
    tag_name = tag.name
    classes = tag.get("class", [])
    class_str = " ".join(classes) if isinstance(classes, list) else str(classes or "")

    # --- Form elements ---
    if tag_name == "input":
        input_type = tag.get("type", "text").lower()
        if input_type == "hidden":
            return None  # Skip hidden inputs
        type_map = {
            "text": "input_text",
            "email": "input_text",
            "tel": "input_tel",
            "number": "input_number",
            "password": "input_password",
            "date": "input_date",
            "datetime-local": "input_date",
            "checkbox": "checkbox",
            "radio": "radio",
            "submit": "button_submit",
        }
        comp_type = type_map.get(input_type, "input_text")
        return _build_form_component(tag, comp_type)

    if tag_name == "textarea":
        return _build_form_component(tag, "textarea")

    if tag_name == "select":
        return _build_form_component(tag, "select")

    if tag_name == "button":
        btn_type = tag.get("type", "").lower()
        comp_type = "button_submit" if btn_type == "submit" else "button_action"
        return _build_button_component(tag, comp_type)

    # --- Links (potential CTAs) ---
    if tag_name == "a":
        return _classify_link(tag, class_str)

    # --- Media ---
    if tag_name == "img":
        # Skip tracking pixels
        width = tag.get("width", "")
        height = tag.get("height", "")
        if str(width) in ("0", "1") and str(height) in ("0", "1"):
            return None
        # Check if parent is carousel
        if _is_in_carousel(tag):
            return None  # Will be captured as carousel
        return {
            "type": "image_single",
            "tagName": "img",
            "attributes": {
                "alt": tag.get("alt", ""),
                "width": width,
                "height": height,
            },
        }

    if tag_name == "video":
        return {"type": "video", "tagName": "video", "attributes": {}}

    # --- Carousel/Slider (by class) ---
    if _CAROUSEL_PATTERNS.search(class_str):
        # Only capture the container, not individual items
        if not _has_ancestor_with_class(tag, _CAROUSEL_PATTERNS):
            return {
                "type": "image_carousel",
                "tagName": tag_name,
                "attributes": {"className": class_str},
                "childCount": len(tag.find_all("img", recursive=True)),
            }

    # --- Table ---
    if tag_name == "table":
        role = tag.get("role", "")
        if role == "presentation":
            return None
        return {
            "type": "table",
            "tagName": "table",
            "attributes": {
                "rowCount": len(tag.find_all("tr")),
                "colCount": len(tag.find_all("th")) or len(tag.find_all("td", limit=1)),
            },
        }

    # --- Accordion ---
    if tag_name == "details":
        summary = tag.find("summary")
        return {
            "type": "accordion",
            "tagName": "details",
            "attributes": {
                "summary": summary.get_text(strip=True)[:50] if summary else "",
                "open": tag.has_attr("open"),
            },
        }

    # --- Social proof (by class) ---
    if _SOCIAL_PROOF_PATTERNS.search(class_str):
        text = tag.get_text(strip=True)[:100]
        if text:
            return {
                "type": "social_proof",
                "tagName": tag_name,
                "attributes": {"text": text, "className": class_str},
            }

    # --- Urgency (by text content in specific elements) ---
    if tag_name in ("span", "p", "div", "strong", "em"):
        text = tag.get_text(strip=True)
        if text and _URGENCY_TEXT_PATTERNS.search(text):
            # Make sure this isn't inside a larger urgency element
            if not _has_ancestor_with_text_match(tag, _URGENCY_TEXT_PATTERNS):
                return {
                    "type": "urgency",
                    "tagName": tag_name,
                    "attributes": {"text": text[:100]},
                }

    # --- Sticky/Fixed elements (by class/style) ---
    style = tag.get("style", "")
    if isinstance(style, str) and ("position: fixed" in style or "position: sticky" in style):
        if tag_name in ("div", "footer", "header"):
            return {
                "type": "sticky_element",
                "tagName": tag_name,
                "attributes": {"className": class_str},
                "isSticky": True,
            }
    if _STICKY_CLASS_PATTERNS.search(class_str) and tag_name in ("div", "footer", "header", "nav"):
        # Avoid double-counting sections already marked sticky
        return {
            "type": "sticky_element",
            "tagName": tag_name,
            "attributes": {"className": class_str},
            "isSticky": True,
        }

    return None


def _build_form_component(tag: Tag, comp_type: str) -> dict:
    """Build a component dict for form elements."""
    # Find associated label
    label = _find_label(tag)
    return {
        "type": comp_type,
        "tagName": tag.name,
        "attributes": {
            "name": tag.get("name", ""),
            "label": label,
            "required": tag.has_attr("required"),
            "placeholder": tag.get("placeholder", ""),
        },
    }


def _build_button_component(tag: Tag, comp_type: str) -> dict:
    """Build a component dict for button elements."""
    label = tag.get_text(strip=True)[:50]
    classes = tag.get("class", [])
    class_str = " ".join(classes) if isinstance(classes, list) else str(classes or "")
    return {
        "type": comp_type,
        "tagName": "button",
        "attributes": {
            "label": label,
            "className": class_str,
        },
    }


def _classify_link(tag: Tag, class_str: str) -> Optional[dict]:
    """Classify an <a> tag - returns CTA component if it looks like a CTA, else None."""
    href = tag.get("href", "")
    text = tag.get_text(strip=True)[:50]

    # LINE link
    if href and "line.me" in href:
        return {
            "type": "cta_line",
            "tagName": "a",
            "attributes": {"label": text, "href": href},
        }

    # Tel link
    if href and href.startswith("tel:"):
        return {
            "type": "cta_tel",
            "tagName": "a",
            "attributes": {"label": text, "href": href},
        }

    # CTA by class pattern
    if _CTA_CLASS_PATTERNS.search(class_str):
        return {
            "type": "cta_link",
            "tagName": "a",
            "attributes": {
                "label": text,
                "className": class_str,
                "href": _sanitize_href(href),
            },
        }

    # CTA by text content (Japanese action words)
    if text and re.search(r"問い合わせ|お問合せ|資料請求|見学|内見|申し込|申込|予約|相談", text):
        return {
            "type": "cta_link",
            "tagName": "a",
            "attributes": {
                "label": text,
                "className": class_str,
                "href": _sanitize_href(href),
            },
        }

    return None


def _find_label(tag: Tag) -> str:
    """Find the label text for a form element."""
    # Check for explicit label with 'for' attribute
    tag_id = tag.get("id", "")
    if tag_id:
        label = tag.find_previous("label", attrs={"for": tag_id})
        if label:
            return label.get_text(strip=True)[:50]

    # Check for wrapping label
    parent = tag.find_parent("label")
    if parent:
        # Get label text excluding the input itself
        label_text = parent.get_text(strip=True)[:50]
        return label_text

    # Check for aria-label
    aria_label = tag.get("aria-label", "")
    if aria_label:
        return aria_label[:50]

    # Check preceding sibling or parent text
    prev = tag.find_previous_sibling(["label", "span", "p", "dt"])
    if prev:
        return prev.get_text(strip=True)[:50]

    return ""


def _is_in_carousel(tag: Tag) -> bool:
    """Check if tag is inside a carousel/slider container."""
    return _has_ancestor_with_class(tag, _CAROUSEL_PATTERNS)


def _has_ancestor_with_class(tag: Tag, pattern: re.Pattern) -> bool:
    """Check if any ancestor has a class matching the pattern."""
    for parent in tag.parents:
        if not isinstance(parent, Tag):
            continue
        classes = parent.get("class", [])
        class_str = " ".join(classes) if isinstance(classes, list) else str(classes or "")
        if pattern.search(class_str):
            return True
        if parent.name in ("body", "html"):
            break
    return False


def _has_ancestor_with_text_match(tag: Tag, pattern: re.Pattern) -> bool:
    """Check if any direct parent already matches the text pattern (avoid double-counting)."""
    parent = tag.parent
    if parent and isinstance(parent, Tag) and parent.name not in ("body", "html", "section", "div"):
        text = parent.get_text(strip=True)
        if pattern.search(text):
            return True
    return False


def _sanitize_href(href: str) -> str:
    """Sanitize href for storage (remove query params with tracking info)."""
    if not href:
        return ""
    # Remove common tracking params but keep path
    if "?" in href:
        base = href.split("?")[0]
        return base
    return href[:200]  # Limit length
