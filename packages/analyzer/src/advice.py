"""Rule-based advice stub module.

In this architecture, detailed AI advice is generated on-demand via MCP + Kiro,
not during the automated scan. This module provides a lightweight placeholder
that marks changes as "pending analysis" for later Kiro-driven review.
"""

import json


# Priority heuristics based on category and change scale
PRIORITY_RULES = {
    "CRO": "high",      # CRO changes directly impact conversion
    "AD_PRODUCT": "medium",  # Ad changes are revenue-related
    "SEO": "medium",    # SEO changes affect organic traffic
    "AI": "high",       # AI features represent major competitive moves
    "OTHER": "low",     # Design/branding changes are lower priority
}


def generate_advice(
    service_name: str,
    page_type: str,
    category: str,
    diff_summary: str,
) -> str:
    """Generate a placeholder advice record for later Kiro analysis.

    The actual detailed analysis is done on-demand via MCP when a user
    asks Kiro to analyze a specific change.

    Returns:
        JSON string with basic advice fields.
    """
    priority = PRIORITY_RULES.get(category, "low")

    result = {
        "summary": diff_summary[:200] if diff_summary else "変更を検知しました",
        "intent": "MCP経由でKiroに分析を依頼してください",
        "proposal": "MCP経由でKiroに分析を依頼してください",
        "priority": priority,
        "expected_effect": None,
        "risks": None,
    }

    return json.dumps(result, ensure_ascii=False)
