"""Press article relevance classifier module.

Classifies press release articles into relevance categories using keyword/regex
pattern matching. No external AI API required.

Classification logic:
1. If title+body is empty → classification_failed
2. Check IRRELEVANT_PATTERNS against title+body → if match with no relevant match → irrelevant
3. Score each RELEVANT_PATTERNS category (count matches / total patterns)
4. Pick highest scoring category
5. If best score >= CONFIDENCE_THRESHOLD → relevant with that category
6. If best score > 0 but < threshold → relevant with needs_manual_review=True, category="other"
7. If no relevant patterns match at all → default to relevant + needs_manual_review=True
"""

import re
from dataclasses import dataclass
from typing import Optional


# Feature: press-release-monitor, Property 7: Classification correctness
# Feature: press-release-monitor, Property 8: Relevant article category assignment and manual review flag

RELEVANCE_CATEGORIES = [
    "service_feature",  # サービス機能に関する発表
    "market_data",      # 市場調査データ
    "ux_improvement",   # UX改善に関する発表
    "pricing",          # 料金改定
    "other",            # その他（関連だが上記に該当しない）
]

IRRELEVANT_PATTERNS = [
    r"人事|取締役|執行役|役員|代表|社長就任",
    r"決算|IR|投資家|株主|配当|有価証券",
    r"イベント|セミナー|展示会|協賛|スポンサー",
    r"CSR|SDGs|社会貢献|ボランティア",
    r"オフィス移転|組織変更|グループ会社",
]

RELEVANT_PATTERNS: dict[str, list[str]] = {
    "service_feature": [
        r"新機能|リリース|サービス開始|提供開始|機能追加|アップデート|新サービス|β版|正式版",
    ],
    "market_data": [
        r"調査|レポート|統計|データ|白書|トレンド|動向|市場|実態",
    ],
    "ux_improvement": [
        r"UI|UX|デザイン|ユーザビリティ|使いやすさ|リニューアル|改善|刷新",
    ],
    "pricing": [
        r"料金|価格|プラン|値下げ|無料|有料|課金|手数料",
    ],
}

CONFIDENCE_THRESHOLD = 0.3  # Below this → needs_manual_review


@dataclass
class ClassificationResult:
    """Result of press article classification."""

    is_relevant: bool
    category: Optional[str] = None
    confidence: float = 0.0
    needs_manual_review: bool = False


def classify_press_article(title: str, body: str) -> ClassificationResult:
    """Classify a press article by relevance.

    Args:
        title: Article title text.
        body: Article body text.

    Returns:
        ClassificationResult with relevance determination, category, confidence,
        and manual review flag.
    """
    # Step 1: Handle empty content
    combined_text = (title or "").strip() + " " + (body or "").strip()
    combined_text = combined_text.strip()

    if not combined_text:
        return ClassificationResult(
            is_relevant=False,
            category="classification_failed",
            confidence=0.0,
            needs_manual_review=False,
        )

    # Step 2: Check irrelevant patterns
    has_irrelevant_match = _matches_any_pattern(combined_text, IRRELEVANT_PATTERNS)

    # Step 3: Score relevant categories
    category_scores = _score_relevant_categories(combined_text)
    best_category, best_score = _get_best_category(category_scores)

    # Step 2 continued: If irrelevant match and no relevant match → irrelevant
    if has_irrelevant_match and best_score == 0.0:
        return ClassificationResult(
            is_relevant=False,
            category=None,
            confidence=0.0,
            needs_manual_review=False,
        )

    # Step 4-5: If best score >= threshold → relevant with that category
    if best_score >= CONFIDENCE_THRESHOLD:
        return ClassificationResult(
            is_relevant=True,
            category=best_category,
            confidence=best_score,
            needs_manual_review=False,
        )

    # Step 6: If best score > 0 but < threshold → relevant with manual review, category="other"
    if best_score > 0.0:
        return ClassificationResult(
            is_relevant=True,
            category="other",
            confidence=best_score,
            needs_manual_review=True,
        )

    # Step 7: No relevant patterns match at all → default to relevant + needs_manual_review
    # Per Requirements 3.6: classify as Relevant and mark for manual review
    return ClassificationResult(
        is_relevant=True,
        category="other",
        confidence=0.0,
        needs_manual_review=True,
    )


def _matches_any_pattern(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the given regex patterns."""
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False


def _score_relevant_categories(text: str) -> dict[str, float]:
    """Score each relevant category based on pattern matches.

    For each category, the score is: number of matching patterns / total patterns in that category.
    Each pattern string may contain multiple alternatives (separated by |),
    so we count how many of those alternatives match.
    """
    scores: dict[str, float] = {}

    for category, patterns in RELEVANT_PATTERNS.items():
        total_keywords = 0
        matched_keywords = 0

        for pattern_str in patterns:
            # Split pattern alternatives to count individual keyword matches
            alternatives = pattern_str.split("|")
            total_keywords += len(alternatives)

            for alt in alternatives:
                alt = alt.strip()
                if alt and re.search(re.escape(alt), text):
                    matched_keywords += 1

        scores[category] = matched_keywords / total_keywords if total_keywords > 0 else 0.0

    return scores


def _get_best_category(scores: dict[str, float]) -> tuple[str, float]:
    """Get the category with the highest score.

    Returns:
        Tuple of (category_name, score). If all scores are 0, returns ("other", 0.0).
    """
    if not scores:
        return ("other", 0.0)

    best_category = max(scores, key=lambda k: scores[k])
    best_score = scores[best_category]

    if best_score == 0.0:
        return ("other", 0.0)

    return (best_category, best_score)
