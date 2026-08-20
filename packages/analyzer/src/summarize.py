"""Rule-based change summarization module.

Generates human-readable summaries from DOM diffs using structural analysis.
Design goals:
- Human: one-read understandable ("what specifically changed")
- AI-consumable: concrete nouns (button labels, field names, section IDs)
  so downstream automation (growth planning, AI proposals) can extract meaning

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

# 汎用すぎてヒントにならないクラス名・属性値
_GENERIC_CLASSNAMES = {
    "hidden", "block", "flex", "grid", "w-full", "container", "wrapper",
    "inner", "outer", "content", "main", "body", "row", "col", "item",
    "list", "top", "bottom", "left", "right", "center", "active", "disabled",
    "true", "false", "on", "off", "open", "close", "show", "hide",
}


def summarize_change(diff_text: str) -> str:
    """Generate a specific, actionable summary of the change in Japanese.

    Returns structured text with concrete element names, labels, field names
    so both humans and downstream AI can extract meaning without reading raw diff.
    """
    lines = diff_text.splitlines()

    added_lines = [l[1:] for l in lines if l.startswith("+") and not l.startswith("+++")]
    removed_lines = [l[1:] for l in lines if l.startswith("-") and not l.startswith("---")]

    changes = []

    # 1. Specific text changes in CRO-significant elements (buttons, headings, links)
    changes.extend(_extract_text_changes(added_lines, removed_lines))

    # 2. Structural additions/removals with content snippets
    changes.extend(_extract_structural_changes(added_lines, removed_lines))

    # 3. Form field additions/removals (high value for AI downstream)
    changes.extend(_extract_form_changes(added_lines, removed_lines))

    # 4. Aria/role additions (accessibility improvements)
    changes.extend(_extract_attribute_changes(added_lines, removed_lines))

    # Deduplicate preserving order
    seen = set()
    unique_changes = []
    for c in changes:
        if c not in seen:
            seen.add(c)
            unique_changes.append(c)

    if unique_changes:
        # Show up to 8 items (increased from 5 to preserve more detail for AI)
        result = "\n".join(f"・{c}" for c in unique_changes[:8])
        if len(unique_changes) > 8:
            result += f"\n・他{len(unique_changes) - 8}件の変更"
        return result

    # Fallback: generic summary pointing to diff
    total_changes = len(added_lines) + len(removed_lines)
    elements = _detect_elements("\n".join(added_lines + removed_lines))
    if elements:
        top = [TAG_LABELS.get(e, e) for e in list(elements.keys())[:3]]
        return f"{', '.join(top)}周辺の構造変更（{total_changes}行）— 詳細はDOM差分を参照"

    if total_changes > 0:
        return f"DOM構造の変更（{total_changes}行）— 詳細はDOM差分を参照"
    return "DOM構造に変更を検知"


# ─────────────────────────────────────────────
# 1. テキスト変更の抽出
# ─────────────────────────────────────────────

def _extract_text_changes(added_lines: list[str], removed_lines: list[str]) -> list[str]:
    """Extract specific text content changes from CRO-significant elements.

    Preserved text (not [TEXT] placeholder) in buttons/headings/links represents
    actual copy visible to users — the most valuable signal for both human review
    and AI-driven planning.
    """
    changes = []

    text_in_tag_pattern = re.compile(
        r'<(button|a|h[1-6]|label|th|summary|legend)[^>]*>'
        r'(.*?)'
        r'</\1>',
        re.DOTALL | re.IGNORECASE,
    )

    added_text = "\n".join(added_lines)
    removed_text = "\n".join(removed_lines)

    added_matches = text_in_tag_pattern.findall(added_text)
    removed_matches = text_in_tag_pattern.findall(removed_text)

    def _clean(content: str) -> str:
        text = _strip_html(content).strip()
        # collapse whitespace
        return re.sub(r'\s+', ' ', text)

    added_texts: dict[str, list[str]] = {}
    for tag, content in added_matches:
        clean = _clean(content)
        if clean and clean not in ("[TEXT]", "[PROPERTY_TEXT]") and len(clean) > 1:
            added_texts.setdefault(tag.lower(), []).append(clean)

    removed_texts: dict[str, list[str]] = {}
    for tag, content in removed_matches:
        clean = _clean(content)
        if clean and clean not in ("[TEXT]", "[PROPERTY_TEXT]") and len(clean) > 1:
            removed_texts.setdefault(tag.lower(), []).append(clean)

    tag_ja = {
        "button": "ボタン", "a": "リンク",
        "h1": "大見出し(H1)", "h2": "見出し(H2)", "h3": "見出し(H3)",
        "h4": "見出し(H4)", "h5": "見出し(H5)", "h6": "見出し(H6)",
        "label": "ラベル", "th": "テーブルヘッダー",
        "summary": "サマリー", "legend": "フォーム凡例",
    }

    for tag in set(list(added_texts.keys()) + list(removed_texts.keys())):
        added_list = added_texts.get(tag, [])
        removed_list = removed_texts.get(tag, [])
        tag_label = tag_ja.get(tag, tag)

        if added_list and removed_list:
            for old_text in removed_list[:2]:
                for new_text in added_list[:2]:
                    if old_text != new_text:
                        changes.append(
                            f"{tag_label}テキスト変更:「{_truncate(old_text, 25)}」→「{_truncate(new_text, 25)}」"
                        )
                        break
                break
        elif added_list and not removed_list:
            for text in added_list[:3]:
                changes.append(f"{tag_label}追加:「{_truncate(text, 30)}」")
        elif removed_list and not added_list:
            for text in removed_list[:3]:
                changes.append(f"{tag_label}削除:「{_truncate(text, 30)}」")

    return changes


# ─────────────────────────────────────────────
# 2. 構造変更の抽出（内容スニペット付き）
# ─────────────────────────────────────────────

def _extract_structural_changes(added_lines: list[str], removed_lines: list[str]) -> list[str]:
    """Detect addition/removal of structural elements with content snippets.

    Appends a short content preview so readers (and AI) understand what the
    added/removed element actually contains — not just that it exists.
    """
    changes = []

    structural_patterns = [
        (r'<form\b', "フォーム"),
        (r'<nav\b', "ナビゲーション"),
        (r'<section\b', "セクション"),
        (r'<aside\b', "サイドバー"),
        (r'<dialog\b|<div[^>]*modal', "モーダル/ダイアログ"),
        (r'<details\b', "アコーディオン"),
        (r'class="[^"]*carousel|class="[^"]*slider|class="[^"]*swiper', "カルーセル/スライダー"),
        (r'class="[^"]*\btab\b', "タブ"),
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
            snippet = _extract_content_snippet(added_text, pattern)
            suffix = f" [{snippet}]" if snippet else ""
            changes.append(f"{label}が新規追加{suffix}")
        elif removed_count > 0 and added_count == 0:
            snippet = _extract_content_snippet(removed_text, pattern)
            suffix = f" [{snippet}]" if snippet else ""
            changes.append(f"{label}が削除{suffix}")
        elif added_count > removed_count:
            snippet = _extract_content_snippet(added_text, pattern)
            suffix = f" [{snippet}]" if snippet else ""
            changes.append(f"{label}が追加 (+{added_count - removed_count}){suffix}")

    return changes


def _extract_content_snippet(text: str, tag_pattern: str, max_len: int = 80) -> str:
    """マッチした要素ブロックから人が読めるコンテンツを抽出する。

    優先順位:
    1. ボタン・リンク・見出しのテキスト（最も情報密度が高い）
    2. input の placeholder / aria-label / value
    3. class/id 名のうち意味のあるもの
    """
    lines = text.splitlines()

    # マッチした行のインデックスを探す
    start_idx = None
    for i, line in enumerate(lines):
        if re.search(tag_pattern, line, re.IGNORECASE):
            start_idx = i
            break

    if start_idx is None:
        return ""

    # マッチ行から最大20行のブロックを取得
    block = "\n".join(lines[start_idx: start_idx + 20])

    # 1. ボタン・リンク・見出しのテキストを収集
    cta_pattern = re.compile(
        r'<(button|a|h[1-6]|legend)[^>]*>(.*?)</\1>',
        re.DOTALL | re.IGNORECASE,
    )
    cta_texts = []
    for _, content in cta_pattern.findall(block):
        clean = re.sub(r'\s+', ' ', _strip_html(content)).strip()
        if clean and clean not in ("[TEXT]", "[PROPERTY_TEXT]") and len(clean) > 1:
            cta_texts.append(_truncate(clean, 20))

    if cta_texts:
        return " / ".join(cta_texts[:3])

    # 2. input の placeholder / aria-label
    input_hints = []
    for m in re.finditer(
        r'<input[^>]*(?:placeholder|aria-label)="([^"]+)"',
        block, re.IGNORECASE
    ):
        val = m.group(1).strip()
        if val and val not in ("[TEXT]",):
            input_hints.append(_truncate(val, 15))
    if input_hints:
        return " / ".join(input_hints[:4])

    # 3. 意味のある class/id 名（汎用名を除外）
    id_match = re.search(r'\bid="([^"]+)"', block, re.IGNORECASE)
    if id_match:
        val = id_match.group(1).split()[0]
        if val and val.lower() not in _GENERIC_CLASSNAMES:
            return val

    class_match = re.search(r'\bclass="([^"]+)"', block, re.IGNORECASE)
    if class_match:
        for cls in class_match.group(1).split():
            if cls.lower() not in _GENERIC_CLASSNAMES and len(cls) > 3:
                return cls

    return ""


# ─────────────────────────────────────────────
# 3. フォームフィールド変更の抽出
# ─────────────────────────────────────────────

def _extract_form_changes(added_lines: list[str], removed_lines: list[str]) -> list[str]:
    """Extract form field additions/removals with field names.

    Form changes are high-value signals for growth automation:
    'フォームに「沿線・駅」「間取り」フィールドが追加' is actionable for HOME'S.
    Only emits output when there is NO accompanying <form> tag addition/removal
    (to avoid duplicating what _extract_structural_changes already covers).
    """
    changes = []

    # <form> タグ自体の追加/削除があった場合は structural_changes 側でカバー済みなのでスキップ
    form_added = any(re.search(r'<form\b', l, re.IGNORECASE) for l in added_lines)
    form_removed = any(re.search(r'<form\b', l, re.IGNORECASE) for l in removed_lines)
    if form_added or form_removed:
        return []

    # input / select / textarea の追加・削除を検出
    field_pattern = re.compile(r'<(?:input|select|textarea)\b[^>]*>', re.IGNORECASE)
    name_attrs = re.compile(r'(?:placeholder|aria-label|name|id)="([^"]+)"', re.IGNORECASE)

    def _field_names(lines_list: list[str]) -> list[str]:
        names = []
        for line in lines_list:
            if field_pattern.search(line):
                for m in name_attrs.finditer(line):
                    val = m.group(1).strip()
                    if val and val not in ("[TEXT]", "[HIDDEN_VALUE]") and not val.startswith("["):
                        names.append(_truncate(val, 15))
                        break
        return names

    added_fields = _field_names(added_lines)
    removed_fields = _field_names(removed_lines)

    added_set = [f for f in added_fields if f not in removed_fields]
    removed_set = [f for f in removed_fields if f not in added_fields]

    if added_set:
        names_str = "「" + "」「".join(added_set[:5]) + "」"
        suffix = f"など{len(added_set)}項目" if len(added_set) > 5 else ""
        changes.append(f"フォームフィールド追加: {names_str}{suffix}")

    if removed_set:
        names_str = "「" + "」「".join(removed_set[:5]) + "」"
        suffix = f"など{len(removed_set)}項目" if len(removed_set) > 5 else ""
        changes.append(f"フォームフィールド削除: {names_str}{suffix}")

    return changes


# ─────────────────────────────────────────────
# 4. aria/role 変更の抽出
# ─────────────────────────────────────────────

def _extract_attribute_changes(added_lines: list[str], removed_lines: list[str]) -> list[str]:
    """Aria/role additions only — class-pattern heuristics removed as too noisy."""
    changes = []

    aria_added = sum(1 for l in added_lines if 'aria-' in l or 'role=' in l)
    aria_removed = sum(1 for l in removed_lines if 'aria-' in l or 'role=' in l)
    if aria_added > aria_removed + 2:
        changes.append("アクセシビリティ属性（aria/role）が追加")

    return changes


# ─────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────

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
