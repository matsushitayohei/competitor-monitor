"""Form Analyzer - Deep analysis of form elements for CV optimization comparison.

Extracts:
- Field composition (type, count, required/optional, labels)
- Multi-step form detection
- Validation method detection
- Submit button design (label, color, size, position)
- Micro-copy (reassurance text)
- Social proof elements near forms
- Estimated completion time
"""

import re
from typing import Optional
from bs4 import BeautifulSoup, Tag


# --- Validation Detection Patterns ---

# Patterns indicating real-time validation
_REALTIME_VALIDATION_PATTERNS = [
    r"validate",
    r"error.*message",
    r"invalid",
    r"has-error",
    r"is-invalid",
    r"field-error",
    r"validation",
]
_REALTIME_VALIDATION_RE = re.compile("|".join(_REALTIME_VALIDATION_PATTERNS), re.IGNORECASE)

# Patterns for step indicators
_STEP_PATTERNS = re.compile(
    r"step|progress|wizard|phase|stage|ステップ|STEP",
    re.IGNORECASE,
)

# Micro-copy patterns (reassurance around forms)
_MICRO_COPY_PATTERNS = re.compile(
    r"無料|しつこい.*ません|営業.*ません|安心|簡単|かんたん"
    r"|\d+分で完了|\d+秒で|すぐに届|今すぐ|無理な勧誘"
    r"|個人情報.*保護|SSL|暗号化|セキュア",
)

# Social proof patterns near forms
_SOCIAL_PROOF_NEAR_FORM = re.compile(
    r"本日\d+人|今日\d+人|\d+人が(問い合わせ|申し込|利用|閲覧)"
    r"|満足度\d+|★\d|評価\d|\d+件のレビュー",
)

# Average time per field type (seconds)
_FIELD_TIME_ESTIMATES = {
    "input_text": 8,
    "input_tel": 6,
    "input_number": 5,
    "input_password": 6,
    "input_date": 5,
    "textarea": 20,
    "select": 4,
    "checkbox": 2,
    "radio": 3,
}


def analyze_forms(html: str) -> dict:
    """Analyze all forms on a page.

    Returns:
        {
            "forms": [...],
            "summary": {
                "totalForms": int,
                "hasMultiStepForm": bool,
                "totalFields": int,
                "totalRequiredFields": int,
            }
        }
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove non-visual elements
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    forms = []
    form_tags = soup.find_all("form")

    for idx, form_tag in enumerate(form_tags):
        form_data = _analyze_single_form(form_tag, idx)
        if form_data and form_data["totalFields"] > 0:
            forms.append(form_data)

    # Also check for form-like structures without <form> tag
    # (some SPAs use div-based forms)
    if not forms:
        # Look for significant input groups
        implicit_form = _detect_implicit_form(soup)
        if implicit_form:
            forms.append(implicit_form)

    total_fields = sum(f["totalFields"] for f in forms)
    total_required = sum(f["requiredFields"] for f in forms)
    has_multi_step = any(f["steps"] > 1 for f in forms)

    return {
        "forms": forms,
        "summary": {
            "totalForms": len(forms),
            "hasMultiStepForm": has_multi_step,
            "totalFields": total_fields,
            "totalRequiredFields": total_required,
        },
    }


def _analyze_single_form(form_tag: Tag, index: int) -> Optional[dict]:
    """Analyze a single <form> element."""
    # Extract fields
    fields = _extract_fields(form_tag)

    if not fields:
        return None

    # Count field types
    field_types: dict[str, int] = {}
    required_count = 0
    for field in fields:
        ft = field["type"]
        field_types[ft] = field_types.get(ft, 0) + 1
        if field.get("required"):
            required_count += 1

    # Detect steps
    steps = _detect_steps(form_tag)

    # Detect validation type
    validation_type = _detect_validation_type(form_tag)

    # Find submit button
    submit_button = _extract_submit_button(form_tag)

    # Find micro-copy
    micro_copies = _extract_micro_copy(form_tag)

    # Find social proof
    social_proofs = _extract_social_proof(form_tag)

    # Detect progress bar
    has_progress_bar = _detect_progress_bar(form_tag)

    # Estimate completion time
    estimated_seconds = sum(
        _FIELD_TIME_ESTIMATES.get(f["type"], 5) for f in fields
        if f["type"] != "input_hidden"
    )
    estimated_minutes = max(1, round(estimated_seconds / 60))

    return {
        "id": f"form-{index}",
        "action": form_tag.get("action", ""),
        "method": (form_tag.get("method", "GET")).upper(),
        "totalFields": len(fields),
        "requiredFields": required_count,
        "fieldTypes": field_types,
        "fields": fields,
        "steps": steps,
        "hasProgressBar": has_progress_bar,
        "validationType": validation_type,
        "submitButton": submit_button,
        "microCopy": micro_copies,
        "socialProof": social_proofs,
        "estimatedCompletionMinutes": estimated_minutes,
    }


def _extract_fields(container: Tag) -> list[dict]:
    """Extract all form fields from a container."""
    fields = []
    position = 0

    # Text inputs, email, tel, etc.
    for inp in container.find_all("input"):
        input_type = inp.get("type", "text").lower()
        if input_type in ("hidden", "submit", "button", "reset", "image"):
            continue

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
        }
        field_type = type_map.get(input_type, "input_text")

        field = {
            "type": field_type,
            "name": inp.get("name", ""),
            "label": _find_field_label(inp),
            "required": inp.has_attr("required") or _has_required_indicator(inp),
            "placeholder": inp.get("placeholder", ""),
            "position": position,
            "hasValidation": _has_validation_attrs(inp),
        }
        fields.append(field)
        position += 1

    # Textareas
    for ta in container.find_all("textarea"):
        field = {
            "type": "textarea",
            "name": ta.get("name", ""),
            "label": _find_field_label(ta),
            "required": ta.has_attr("required") or _has_required_indicator(ta),
            "placeholder": ta.get("placeholder", ""),
            "position": position,
            "hasValidation": _has_validation_attrs(ta),
        }
        fields.append(field)
        position += 1

    # Selects
    for sel in container.find_all("select"):
        options = sel.find_all("option")
        option_count = len(options) - 1  # Exclude placeholder option
        default_option = ""
        for opt in options:
            if opt.has_attr("selected"):
                default_option = opt.get_text(strip=True)
                break

        field = {
            "type": "select",
            "name": sel.get("name", ""),
            "label": _find_field_label(sel),
            "required": sel.has_attr("required") or _has_required_indicator(sel),
            "optionCount": max(0, option_count),
            "defaultOption": default_option,
            "position": position,
            "hasValidation": False,
        }
        fields.append(field)
        position += 1

    return fields


def _find_field_label(tag: Tag) -> str:
    """Find the label text for a form field."""
    # Check for explicit label via 'for' attribute
    tag_id = tag.get("id", "")
    if tag_id:
        form = tag.find_parent("form") or tag.find_parent("body")
        if form:
            label = form.find("label", attrs={"for": tag_id})
            if label:
                return label.get_text(strip=True)[:80]

    # Check wrapping label
    parent_label = tag.find_parent("label")
    if parent_label:
        text = parent_label.get_text(strip=True)[:80]
        # Remove the input's own placeholder from label text
        return text

    # aria-label
    aria = tag.get("aria-label", "")
    if aria:
        return aria[:80]

    # Adjacent label/dt/th
    prev = tag.find_previous_sibling(["label", "span", "dt", "th", "p"])
    if prev and prev.get_text(strip=True):
        return prev.get_text(strip=True)[:80]

    # Parent's first text node
    parent = tag.parent
    if parent:
        for child in parent.children:
            if isinstance(child, str) and child.strip():
                return child.strip()[:80]
            if isinstance(child, Tag) and child.name in ("label", "span", "p"):
                text = child.get_text(strip=True)
                if text and child != tag:
                    return text[:80]

    return ""


def _has_required_indicator(tag: Tag) -> bool:
    """Check if a field has visual required indicators (*, 必須, etc.)."""
    # Check aria-required
    if tag.get("aria-required") == "true":
        return True

    # Check parent/sibling for required markers
    parent = tag.parent
    if parent:
        parent_text = parent.get_text()
        if "必須" in parent_text or "※" in parent_text:
            return True
        # Check for asterisk in adjacent elements
        for sibling in parent.find_all(["span", "em", "strong"], recursive=False):
            if sibling.get_text(strip=True) in ("*", "※", "必須"):
                return True

    return False


def _has_validation_attrs(tag: Tag) -> bool:
    """Check if a field has validation-related attributes."""
    validation_attrs = ["pattern", "minlength", "maxlength", "min", "max", "required"]
    for attr in validation_attrs:
        if tag.has_attr(attr):
            return True

    # Check for validation-related classes
    classes = tag.get("class", [])
    class_str = " ".join(classes) if isinstance(classes, list) else str(classes or "")
    return bool(_REALTIME_VALIDATION_RE.search(class_str))


def _detect_steps(form_tag: Tag) -> int:
    """Detect number of steps in a multi-step form."""
    # Look for step indicators within or near the form
    form_parent = form_tag.parent

    # Check for step-like elements
    step_elements = form_tag.find_all(
        lambda t: t.name and _STEP_PATTERNS.search(
            " ".join(t.get("class", [])) if isinstance(t.get("class", []), list)
            else str(t.get("class", ""))
        )
    )

    if step_elements:
        # Count distinct step items
        for el in step_elements:
            items = el.find_all("li") or el.find_all(True, recursive=False)
            if len(items) >= 2:
                return len(items)

    # Check parent for step indicators
    if form_parent:
        parent_classes = " ".join(form_parent.get("class", []))
        if _STEP_PATTERNS.search(parent_classes):
            step_items = form_parent.find_all("li")
            if len(step_items) >= 2:
                return len(step_items)

    # Check for multiple fieldsets (sometimes indicates steps)
    fieldsets = form_tag.find_all("fieldset")
    if len(fieldsets) >= 2:
        return len(fieldsets)

    return 1


def _detect_validation_type(form_tag: Tag) -> str:
    """Detect the validation approach used by the form.

    Returns: "realtime", "onsubmit", or "none"
    """
    # Check form attributes
    if form_tag.has_attr("novalidate"):
        # novalidate means custom JS validation (likely realtime)
        return "realtime"

    # Check for validation-related classes/elements
    form_html = str(form_tag)
    if _REALTIME_VALIDATION_RE.search(form_html):
        return "realtime"

    # Check for HTML5 validation attributes on inputs
    has_html5_validation = False
    for inp in form_tag.find_all(["input", "textarea", "select"]):
        if inp.has_attr("pattern") or inp.has_attr("required"):
            has_html5_validation = True
            break

    if has_html5_validation:
        return "onsubmit"

    return "none"


def _extract_submit_button(form_tag: Tag) -> Optional[dict]:
    """Extract submit button details."""
    # Find submit button
    btn = form_tag.find("button", attrs={"type": "submit"})
    if not btn:
        btn = form_tag.find("input", attrs={"type": "submit"})
    if not btn:
        # Look for button-like elements
        btn = form_tag.find("button")
    if not btn:
        # Check for links styled as buttons
        for a in form_tag.find_all("a"):
            classes = " ".join(a.get("class", []))
            if _CTA_CLASS_RE.search(classes):
                btn = a
                break

    if not btn:
        return None

    # Get label
    if btn.name == "input":
        label = btn.get("value", "送信")
    else:
        label = btn.get_text(strip=True)[:50]

    # Get visual properties from class
    classes = btn.get("class", [])
    class_str = " ".join(classes) if isinstance(classes, list) else str(classes or "")

    # Determine size
    size = "default"
    if "full" in class_str.lower() or "w-full" in class_str or "block" in class_str:
        size = "full_width"
    elif "lg" in class_str or "large" in class_str:
        size = "large"
    elif "sm" in class_str or "small" in class_str:
        size = "small"

    # Try to extract inline style color
    style = btn.get("style", "")
    color = _extract_color_from_style(style)

    return {
        "label": label,
        "className": class_str,
        "size": size,
        "color": color,
        "position": "form_bottom",  # Default assumption
    }


_CTA_CLASS_RE = re.compile(r"btn|button|cta|submit", re.IGNORECASE)


def _extract_color_from_style(style: str) -> str:
    """Extract background-color from inline style."""
    if not style:
        return ""
    match = re.search(r"background(?:-color)?\s*:\s*([^;]+)", style, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_micro_copy(form_tag: Tag) -> list[str]:
    """Extract micro-copy (reassurance text) near the form."""
    copies = []

    # Search within form
    for tag in form_tag.find_all(["p", "span", "small", "div", "em"]):
        text = tag.get_text(strip=True)
        if text and _MICRO_COPY_PATTERNS.search(text):
            if text not in copies and len(text) <= 100:
                copies.append(text)

    # Search in siblings (just after form)
    next_sibling = form_tag.find_next_sibling()
    if next_sibling and isinstance(next_sibling, Tag):
        text = next_sibling.get_text(strip=True)
        if text and _MICRO_COPY_PATTERNS.search(text) and len(text) <= 100:
            if text not in copies:
                copies.append(text)

    return copies[:5]  # Max 5 micro-copies


def _extract_social_proof(form_tag: Tag) -> list[str]:
    """Extract social proof elements near the form."""
    proofs = []

    # Search within form and nearby
    search_area = form_tag.parent if form_tag.parent else form_tag
    for tag in search_area.find_all(["p", "span", "div", "strong"]):
        text = tag.get_text(strip=True)
        if text and _SOCIAL_PROOF_NEAR_FORM.search(text):
            if text not in proofs and len(text) <= 100:
                proofs.append(text)

    return proofs[:3]


def _detect_progress_bar(form_tag: Tag) -> bool:
    """Detect if form has a progress bar/indicator."""
    # Check within form
    progress = form_tag.find("progress")
    if progress:
        return True

    # Check for progress-like classes
    for tag in form_tag.find_all(True):
        classes = tag.get("class", [])
        class_str = " ".join(classes) if isinstance(classes, list) else str(classes or "")
        if re.search(r"progress|stepper|wizard-bar|indicator", class_str, re.IGNORECASE):
            return True

    # Check parent for progress elements
    parent = form_tag.parent
    if parent:
        for tag in parent.find_all(True, recursive=False):
            if tag == form_tag:
                break  # Only check elements before the form
            classes = tag.get("class", [])
            class_str = " ".join(classes) if isinstance(classes, list) else str(classes or "")
            if re.search(r"progress|stepper|step-indicator", class_str, re.IGNORECASE):
                return True

    return False


def _detect_implicit_form(soup: BeautifulSoup) -> Optional[dict]:
    """Detect form-like structures without explicit <form> tags (SPA patterns)."""
    # Look for groups of input fields not inside a form
    inputs_without_form = []
    for inp in soup.find_all(["input", "textarea", "select"]):
        if not inp.find_parent("form"):
            input_type = inp.get("type", "text").lower()
            if input_type not in ("hidden", "submit", "button", "reset"):
                inputs_without_form.append(inp)

    if len(inputs_without_form) >= 3:
        # Find common ancestor
        container = inputs_without_form[0].parent
        fields = _extract_fields(container) if container else []
        if fields:
            return {
                "id": "form-implicit",
                "action": "",
                "method": "",
                "totalFields": len(fields),
                "requiredFields": sum(1 for f in fields if f.get("required")),
                "fieldTypes": {},
                "fields": fields,
                "steps": 1,
                "hasProgressBar": False,
                "validationType": "none",
                "submitButton": None,
                "microCopy": [],
                "socialProof": [],
                "estimatedCompletionMinutes": 1,
                "isImplicit": True,
            }

    return None
