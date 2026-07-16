"""Rule-based change classification module.

Classifies DOM changes into categories using keyword matching and structural patterns.
No external AI API required.
"""

import re
from typing import Optional


CATEGORIES = ["CRO", "AD_PRODUCT", "SEO", "AI", "OTHER"]

# Category detection rules: (pattern, weight)
CATEGORY_RULES: dict[str, list[tuple[str, int]]] = {
    "CRO": [
        (r"button|btn|cta", 3),
        (r"form|input|submit|textarea|select", 4),
        (r"modal|dialog|popup|overlay", 3),
        (r"conversion|cv|contact|inquiry", 4),
        (r"step|wizard|progress", 3),
        (r"tab|accordion|toggle", 2),
        (r"carousel|slider|swiper", 2),
        (r"favorite|bookmark|save|clip", 3),
        (r"compare|hikaku", 3),
        (r"review|rating|star", 2),
        (r"breadcrumb|pagination", 1),
        (r"filter|sort|search-result", 2),
    ],
    "AD_PRODUCT": [
        (r"ad[-_]|ads[-_]|advert|sponsor", 5),
        (r"banner|promotion|promo", 4),
        (r"recommend|pickup|featured", 3),
        (r"campaign|sale|discount", 3),
        (r"partner|affiliate", 4),
        (r"premium|highlight|boost", 3),
        (r"slot|placement|inventory", 3),
    ],
    "SEO": [
        (r"schema|structured[-_]?data|json[-_]?ld", 5),
        (r"meta|og:|twitter:", 4),
        (r"canonical|alternate|hreflang", 5),
        (r"heading|<h[1-6]", 3),
        (r"internal[-_]?link|breadcrumb", 3),
        (r"sitemap|robots", 4),
        (r"aria[-_]|role=|alt=", 2),
        (r"nav|navigation|menu", 2),
    ],
    "AI": [
        (r"ai[-_]|chatbot|chat[-_]?bot", 5),
        (r"recommend|suggestion|similar", 3),
        (r"personali[sz]|machine[-_]?learn", 4),
        (r"auto[-_]?complete|predict", 3),
        (r"smart|intelligent", 2),
        (r"gpt|llm|generative", 5),
    ],
}

# Threshold for category assignment
CATEGORY_THRESHOLD = 5


def classify_change(diff_text: str) -> str:
    """Classify a DOM change using rule-based pattern matching.

    Returns:
        JSON-formatted string with category, confidence, and reason.
    """
    import json

    scores: dict[str, int] = {cat: 0 for cat in CATEGORIES}
    matched_rules: dict[str, list[str]] = {cat: [] for cat in CATEGORIES}

    diff_lower = diff_text.lower()

    for category, rules in CATEGORY_RULES.items():
        for pattern, weight in rules:
            matches = re.findall(pattern, diff_lower)
            if matches:
                scores[category] += weight * min(len(matches), 3)  # Cap repetition bonus
                matched_rules[category].append(pattern)

    # Find best category
    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    if best_score < CATEGORY_THRESHOLD:
        best_category = "OTHER"
        confidence = 0.3
        reason = "明確なパターンが検出されませんでした"
    else:
        # Normalize confidence (cap at 1.0)
        confidence = min(best_score / 20.0, 1.0)
        top_patterns = matched_rules[best_category][:3]
        reason = f"検出パターン: {', '.join(top_patterns)}"

    result = {
        "category": best_category,
        "confidence": round(confidence, 2),
        "reason": reason,
    }

    return json.dumps(result, ensure_ascii=False)
