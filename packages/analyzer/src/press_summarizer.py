"""Press release article summarizer module.

Generates concise Japanese summaries (50-200 characters) from press release article
body text using category-based keyword extraction. No external AI API required.
"""


# Category-specific keywords for key sentence extraction
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "service_feature": ["新機能", "リリース", "サービス", "提供開始", "機能", "アップデート", "対応"],
    "market_data": ["調査", "結果", "データ", "割合", "%", "件数", "増加", "減少", "前年比"],
    "ux_improvement": ["UI", "UX", "デザイン", "改善", "リニューアル", "使いやすさ"],
    "pricing": ["料金", "価格", "プラン", "無料", "月額", "円"],
    "other": [],
}

# Sentence delimiters in Japanese
SENTENCE_DELIMITERS = "。！？"


def summarize_press_article(body: str, category: str) -> str:
    """Generate a summary (50-200 chars) from article body text.

    Strategy:
    1. Split body into sentences
    2. Pick first sentence (lead)
    3. Find sentences containing category keywords
    4. Combine until 50-200 char target
    5. Truncate at sentence boundary if over 200

    Args:
        body: The full article body text.
        category: The relevance category (service_feature, market_data, etc.).

    Returns:
        A summary string between 50-200 characters.
    """
    if not body or not body.strip():
        return ""

    body = body.strip()

    # If body itself is very short, return as-is or pad
    if len(body) <= 200:
        if len(body) >= 50:
            return body
        # Body is too short (< 50 chars), return as-is
        return body

    # Split body into sentences
    sentences = _split_into_sentences(body)

    if not sentences:
        return _truncate_at_sentence_boundary(body, 200)

    # Start with the first sentence (lead sentence)
    first_sentence = sentences[0]

    # If first sentence alone exceeds 200 chars, truncate it
    if len(first_sentence) > 200:
        return _truncate_at_sentence_boundary(first_sentence, 200)

    # If first sentence alone is in range [50, 200], check if we can add more
    # Extract key sentences related to the category
    key_sentences = _extract_key_sentences(body, category)

    # Build summary by combining first sentence + key sentences
    summary = first_sentence
    for sentence in key_sentences:
        # Skip if it's the same as first sentence
        if sentence == first_sentence:
            continue
        candidate = summary + sentence
        if len(candidate) <= 200:
            summary = candidate
        else:
            # Try to fit a partial sentence at boundary
            break

    # If summary is still under 50 chars, try adding more sentences
    if len(summary) < 50:
        for sentence in sentences[1:]:
            if sentence in summary:
                continue
            candidate = summary + sentence
            if len(candidate) <= 200:
                summary = candidate
            else:
                # Truncate the candidate at sentence boundary
                summary = _truncate_at_sentence_boundary(candidate, 200)
                break
            if len(summary) >= 50:
                break

    # Final length enforcement
    if len(summary) > 200:
        summary = _truncate_at_sentence_boundary(summary, 200)

    return summary


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using Japanese delimiters (。！？).

    Each returned sentence includes its trailing delimiter.
    """
    sentences = []
    current = ""
    for char in text:
        current += char
        if char in "。！？":
            stripped = current.strip()
            if stripped:
                sentences.append(stripped)
            current = ""

    # Handle remaining text without a sentence delimiter
    remaining = current.strip()
    if remaining:
        sentences.append(remaining)

    return sentences


def _extract_key_sentences(body: str, category: str) -> list[str]:
    """Extract sentences containing category-related keywords.

    Args:
        body: The full article body text.
        category: The relevance category to match keywords against.

    Returns:
        A list of sentences that contain at least one category keyword,
        ordered by their position in the original text.
    """
    keywords = CATEGORY_KEYWORDS.get(category, [])
    if not keywords:
        return []

    sentences = _split_into_sentences(body)
    key_sentences = []

    for sentence in sentences:
        for keyword in keywords:
            if keyword in sentence:
                key_sentences.append(sentence)
                break

    return key_sentences


def _truncate_at_sentence_boundary(text: str, max_length: int = 200) -> str:
    """Truncate text at the last sentence boundary (。！？) within max_length.

    If no sentence boundary found within the truncated portion, truncate at
    max_length directly.

    Args:
        text: The text to truncate.
        max_length: Maximum allowed length (default 200).

    Returns:
        A string of at most max_length characters, preferring to end at a
        sentence boundary.
    """
    if len(text) <= max_length:
        return text

    truncated = text[:max_length]

    # Find last sentence boundary within the truncated text
    for i in range(len(truncated) - 1, -1, -1):
        if truncated[i] in "。！？":
            return truncated[: i + 1]

    # No boundary found, hard truncate
    return truncated
