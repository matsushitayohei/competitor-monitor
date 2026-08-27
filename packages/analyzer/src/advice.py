"""Rule-based advice module with structured priority heuristics.

In this architecture, detailed AI advice is generated on-demand via MCP + Kiro,
not during the automated scan. This module provides a structured placeholder that:
  - Assigns priority based on category AND change scale (additions + deletions)
  - Detects whether CV-critical elements are involved (forms, CTAs, modals)
  - Embeds scale metadata so Kiro has richer context when generating full advice

Priority logic:
  base priority  — from category (CRO/AI → high, AD_PRODUCT/SEO → medium, OTHER → low)
  scale boost    — large diffs (>50 changed lines total) bump medium→high, low→medium
  CV signal      — diff text mentions conversion-critical elements → floor raised to medium
"""

import json
import re


# Base priority by change category
_PRIORITY_BASE: dict[str, str] = {
    "CRO":        "high",    # Directly impacts conversion
    "AI":         "high",    # Major competitive signal
    "AD_PRODUCT": "medium",  # Revenue-related
    "SEO":        "medium",  # Organic traffic
    "OTHER":      "low",
}

# Threshold for "large" change (total added + deleted normalized lines)
_LARGE_CHANGE_THRESHOLD = 50

# Patterns that indicate CV-critical elements are involved
_CV_CRITICAL_RE = re.compile(
    r'<form\b|geetest|class="[^"]*(?:cta|cv[-_]|contact|inquiry|modal|dialog'
    r'|apply|reserve|booking|visit|tour|muisnack)[^"]*"'
    r'|aria-label="[^"]*(?:申込|問合|資料|見学|予約|内見)[^"]*"',
    re.IGNORECASE,
)


def _compute_priority(
    category: str,
    additions: int,
    deletions: int,
    diff_summary: str,
) -> str:
    """Compute change priority from category, scale, and CV signal."""
    base = _PRIORITY_BASE.get(category, "low")
    total_lines = additions + deletions

    # Scale boost: large diffs raise priority one step
    if total_lines >= _LARGE_CHANGE_THRESHOLD:
        if base == "medium":
            base = "high"
        elif base == "low":
            base = "medium"

    # CV floor: if diff touches conversion elements, at least medium
    if base == "low" and _CV_CRITICAL_RE.search(diff_summary or ""):
        base = "medium"

    return base


def generate_advice(
    service_name: str,
    page_type: str,
    category: str,
    diff_summary: str,
    additions: int = 0,
    deletions: int = 0,
) -> str:
    """Generate a structured advice record for later Kiro analysis.

    The actual detailed analysis (intent, proposal, expected_effect, risks) is
    done on-demand via MCP when a user asks Kiro to analyze a specific change.
    This function ensures the priority and scale metadata are already populated
    so Kiro's analysis is grounded in concrete change context.

    Args:
        service_name: The competitor service (suumo, canary, etc.).
        page_type: Page type where the change occurred (detail, listing, form…).
        category: Change category from classifier (CRO, SEO, AI, AD_PRODUCT, OTHER).
        diff_summary: Human-readable summary from summarize_change().
        additions: Number of added lines in the diff.
        deletions: Number of removed lines in the diff.

    Returns:
        JSON string with advice fields including priority and scale context.
    """
    priority = _compute_priority(category, additions, deletions, diff_summary)
    total_lines = additions + deletions

    # Build a richer summary context string for Kiro
    scale_label = (
        "大規模変更" if total_lines >= _LARGE_CHANGE_THRESHOLD
        else "中規模変更" if total_lines >= 10
        else "小規模変更"
    )
    has_cv_signal = bool(_CV_CRITICAL_RE.search(diff_summary or ""))
    cv_note = "（CV要素への影響を含む）" if has_cv_signal else ""

    result = {
        "summary": diff_summary[:200] if diff_summary else "変更を検知しました",
        "intent": "MCP経由でKiroに分析を依頼してください",
        "proposal": "MCP経由でKiroに分析を依頼してください",
        "priority": priority,
        "expected_effect": None,
        "risks": None,
        # Metadata for Kiro context (not shown in UI directly but stored in rawResponse)
        "_meta": {
            "service": service_name,
            "page_type": page_type,
            "category": category,
            "additions": additions,
            "deletions": deletions,
            "scale": scale_label,
            "cv_signal": has_cv_signal,
            "cv_note": cv_note,
        },
    }

    return json.dumps(result, ensure_ascii=False)
