"""Rule-based change summarization module.

Generates human-readable summaries from DOM diffs using structural analysis.
Focuses on extracting SPECIFIC, ACTIONABLE change descriptions:
- What button text changed
- What heading was added/removed
- What navigation item appeared
- What CTA was modified

No external AI API required.
"""

import re
from collections import Counter
from typing import Optional


# Tag-to-Japanese mapping for common UI elements
TAG_LABELS = {
    "button": "ボタン",
    "btn": "ボタン",
    "form": "フォーム",
    "input": "入力欄",
    "nav": "ナビゲーション",
    "header": "ヘッダー",
    "footer": "フッター",
    "modal": "モーダル",
    "dialog": "ダイアログ",
    "card": "カード",
    "tab": "タブ",
    "carousel": "カルーセル",
    "slider": "スライダー",
    "banner": "バナー",
    "sidebar": "サイドバー",
    "menu": "メニュー",
    "search": "検索",
    "filter": "フィルター",
    "sort": "ソート",
    "pagination": "ページネーション",
    "breadcrumb": "パンくずリスト",
    "accordion": "アコーディオン",
    "tooltip": "ツールチップ",
    "dropdown": "ドロップダウン",
    "table": "テーブル",
    "list": "リスト",
    "image": "画像",
    "img": "画像",
    "video": "動画",
    "icon": "アイコン",
    "badge": "バッジ",
    "tag": "タグ",
    "label": "ラベル",
    "link": "リンク",
    "section": "セクション",
    "article": "記事",
    "aside": "サイドコンテンツ",
    "ad": "広告",
    "ads": "広告",
    "sponsor": "スポンサー",
    "recommend": "おすすめ",
    "favorite": "お気に入り",
    "review": "レビュー",
    "rating": "評価",
    "map": "地図",
    "photo": "写真",
    "gallery": "ギャラリー",
}


def summarize_change(diff_text: str) -> str:
    """Generate a specific, actionable summary of the change in Japanese.

    Extracts concrete text changes from CRO-significant elements (buttons,
    headings, links, navigation) to show WHAT specifically changed.

    Returns:
        Structured summary text in Japanese showing specific changes.
    """
    lines = diff_text.splitlines()

    added_lines = [l[1:] for l in lines if l.startswith("+") and not l.startswith("+++")]
    removed_lines = [l[1:] for l in lines if l.startswith("-") and not l.startswith("---")]

    changes = []

    # 1. Extract specific text changes in CRO-significant elements
    text_changes = _extract_text_changes(added_lines, removed_lines)
    changes.extend(text_changes)

    # 2. Detect structural additions/removals (new sections, forms, buttons)
    structural_changes = _extract_structural_changes(added_lines, removed_lines)
    changes.extend(structural_changes)

    # 3. Detect attribute changes (class changes, style changes)
    attr_changes = _extract_attribute_changes(added_lines, removed_lines)
    changes.extend(attr_changes)

    # Deduplicate and limit
    seen = set()
    unique_changes = []
    for c in changes:
        if c not in seen:
            seen.add(c)
            unique_changes.append(c)

    if unique_changes:
        # Format as bullet points, limit to 5 items
        result = "\n".join(f"・{c}" for c in unique_changes[:5])
        if len(unique_changes) > 5:
            result += f"\n  他{len(unique_changes) - 5}件の変更"
        return result

    # Fallback: generic summary with scale
    total_changes = len(added_lines) + len(removed_lines)
    elements = _detect_elements("\n".join(added_lines + removed_lines))
    if elements:
        top = [TAG_LABELS.get(e, e) for e in list(elements.keys())[:3]]
        return f"{', '.join(top)}周辺のDOM構造変更 ({total_changes}行)"

    if total_changes > 0:
        return f"DOM構造に軽微な変更 ({total_changes}行)"
    return "DOM構造に変更を検知"


def _extract_text_changes(added_lines: list[str], removed_lines: list[str]) -> list[str]:
    """Extract specific text content changes from CRO-significant elements.

    Looks for preserved text (not [TEXT] placeholder) in buttons, headings, links, etc.
    that was added or removed - these represent actual UI copy changes visible to users.
    """
    changes = []

    # Pattern to find preserved text within HTML tags
    text_in_tag_pattern = re.compile(
        r'<(button|a|h[1-6]|label|th|summary|legend)[^>]*>'
        r'(.*?)'
        r'</\1>',
        re.DOTALL | re.IGNORECASE,
    )

    added_text = "\n".join(added_lines)
    removed_text = "\n".join(removed_lines)

    # Find text that was added in significant elements
    added_matches = text_in_tag_pattern.findall(added_text)
    removed_matches = text_in_tag_pattern.findall(removed_text)

    # Extract clean text content (strip inner tags)
    added_texts = {}
    for tag, content in added_matches:
        clean = _strip_html(content).strip()
        if clean and clean != "[TEXT]" and clean != "[PROPERTY_TEXT]" and len(clean) > 1:
            added_texts.setdefault(tag.lower(), []).append(clean)

    removed_texts = {}
    for tag, content in removed_matches:
        clean = _strip_html(content).strip()
        if clean and clean != "[TEXT]" and clean != "[PROPERTY_TEXT]" and len(clean) > 1:
            removed_texts.setdefault(tag.lower(), []).append(clean)

    # Generate change descriptions
    tag_ja = {
        "button": "ボタン", "a": "リンク",
        "h1": "大見出し(H1)", "h2": "見出し(H2)", "h3": "見出し(H3)",
        "h4": "見出し(H4)", "h5": "見出し(H5)", "h6": "見出し(H6)",
        "label": "ラベル", "th": "テーブルヘッダー",
        "summary": "サマリー", "legend": "フォーム凡例",
    }

    # Check for text modifications (same tag, different text)
    for tag in set(list(added_texts.keys()) + list(removed_texts.keys())):
        added_list = added_texts.get(tag, [])
        removed_list = removed_texts.get(tag, [])
        tag_label = tag_ja.get(tag, tag)

        if added_list and removed_list:
            # Text was changed
            for old_text in removed_list[:2]:
                for new_text in added_list[:2]:
                    if old_text != new_text:
                        old_short = _truncate(old_text, 20)
                        new_short = _truncate(new_text, 20)
                        changes.append(f"{tag_label}テキスト変更:「{old_short}」→「{new_short}」")
                        break
                break
        elif added_list and not removed_list:
            # Text was added
            for text in added_list[:2]:
                text_short = _truncate(text, 25)
                changes.append(f"{tag_label}追加:「{text_short}」")
        elif removed_list and not added_list:
            # Text was removed
            for text in removed_list[:2]:
                text_short = _truncate(text, 25)
                changes.append(f"{tag_label}削除:「{text_short}」")

    return changes


def _extract_structural_changes(added_lines: list[str], removed_lines: list[str]) -> list[str]:
    """Detect addition/removal of structural elements (sections, forms, new components)."""
    changes = []

    # Patterns for structural elements being added/removed (opening tags)
    structural_patterns = [
        (r'<form\b', "フォーム"),
        (r'<nav\b', "ナビゲーション"),
        (r'<section\b', "セクション"),
        (r'<aside\b', "サイドバー"),
        (r'<dialog\b|<div[^>]*modal', "モーダル/ダイアログ"),
        (r'<details\b', "アコーディオン"),
        (r'class="[^"]*carousel|class="[^"]*slider|class="[^"]*swiper', "カルーセル/スライダー"),
        (r'class="[^"]*tab', "タブ"),
        (r'class="[^"]*search', "検索UI"),
        (r'class="[^"]*filter', "フィルターUI"),
        (r'class="[^"]*banner', "バナー"),
        (r'class="[^"]*cta|class="[^"]*cv[-_]', "CVエリア"),
        (r'class="[^"]*recommend|class="[^"]*pickup', "おすすめ/ピックアップ"),
        (r'class="[^"]*review|class="[^"]*rating', "レビュー/評価"),
    ]

    added_text = "\n".join(added_lines)
    removed_text = "\n".join(removed_lines)

    for pattern, label in structural_patterns:
        added_count = len(re.findall(pattern, added_text, re.IGNORECASE))
        removed_count = len(re.findall(pattern, removed_text, re.IGNORECASE))

        if added_count > 0 and removed_count == 0:
            changes.append(f"{label}が新規追加")
        elif removed_count > 0 and added_count == 0:
            changes.append(f"{label}が削除")
        elif added_count > removed_count:
            changes.append(f"{label}が追加 (+{added_count - removed_count})")

    return changes


def _extract_attribute_changes(added_lines: list[str], removed_lines: list[str]) -> list[str]:
    """Detect meaningful attribute changes (colors, classes, aria attributes)."""
    changes = []

    # Look for class changes that indicate UI modifications
    class_pattern = re.compile(r'class="([^"]*)"')

    added_classes = set()
    removed_classes = set()

    for line in added_lines:
        for match in class_pattern.finditer(line):
            for cls in match.group(1).split():
                added_classes.add(cls)

    for line in removed_lines:
        for match in class_pattern.finditer(line):
            for cls in match.group(1).split():
                removed_classes.add(cls)

    # Detect new classes that weren't in removed lines (new styling/components)
    new_classes = added_classes - removed_classes
    gone_classes = removed_classes - added_classes

    # Look for significant class patterns
    significant_class_patterns = [
        (r'hidden|display-none|d-none|invisible', "要素の表示/非表示変更"),
        (r'color|bg-|background', "色・背景の変更"),
        (r'fixed|sticky|absolute', "レイアウト位置の変更"),
        (r'sp-|pc-|mobile-|desktop-', "デバイス別表示の変更"),
        (r'new|badge|notification', "新着/バッジ表示の変更"),
    ]

    new_class_str = " ".join(new_classes | gone_classes)
    for pattern, label in significant_class_patterns:
        if re.search(pattern, new_class_str, re.IGNORECASE):
            changes.append(label)

    # Detect aria/role changes (accessibility improvements)
    aria_added = sum(1 for l in added_lines if 'aria-' in l or 'role=' in l)
    aria_removed = sum(1 for l in removed_lines if 'aria-' in l or 'role=' in l)
    if aria_added > aria_removed + 2:
        changes.append("アクセシビリティ属性の追加")

    return changes


def _strip_html(text: str) -> str:
    """Strip HTML tags from text content."""
    return re.sub(r'<[^>]+>', '', text)


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _detect_elements(text: str) -> Counter:
    """Detect UI element keywords in text and return frequency counts."""
    text_lower = text.lower()
    found = Counter()

    for keyword in TAG_LABELS:
        count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
        if count == 0:
            count = len(re.findall(re.escape(keyword), text_lower))
        if count > 0:
            found[keyword] = count

    return found
