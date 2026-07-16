"""Rule-based change summarization module.

Generates human-readable summaries from DOM diffs using structural analysis.
No external AI API required.
"""

import re
from collections import Counter


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
    """Generate a brief summary of the change in Japanese.

    Analyzes the diff to identify what UI elements were added, removed, or modified.

    Returns:
        Summary text in Japanese (3 lines max).
    """
    lines = diff_text.splitlines()

    added_lines = [l[1:] for l in lines if l.startswith("+") and not l.startswith("+++")]
    removed_lines = [l[1:] for l in lines if l.startswith("-") and not l.startswith("---")]

    # Detect UI elements in changes
    added_elements = _detect_elements("\n".join(added_lines))
    removed_elements = _detect_elements("\n".join(removed_lines))

    parts = []

    # Additions
    if added_elements:
        top_added = [TAG_LABELS.get(e, e) for e in list(added_elements.keys())[:3]]
        parts.append(f"追加: {', '.join(top_added)}関連の要素")

    # Removals
    if removed_elements:
        top_removed = [TAG_LABELS.get(e, e) for e in list(removed_elements.keys())[:3]]
        parts.append(f"削除: {', '.join(top_removed)}関連の要素")

    # Scale
    total_changes = len(added_lines) + len(removed_lines)
    if total_changes > 100:
        parts.append(f"大規模な変更 ({len(added_lines)}行追加, {len(removed_lines)}行削除)")
    elif total_changes > 30:
        parts.append(f"中規模な変更 ({len(added_lines)}行追加, {len(removed_lines)}行削除)")

    if not parts:
        if total_changes > 0:
            parts.append(f"DOM構造に軽微な変更を検知 ({total_changes}行)")
        else:
            parts.append("DOM構造に変更を検知しました")

    return "\n".join(parts[:3])


def _detect_elements(text: str) -> Counter:
    """Detect UI element keywords in text and return frequency counts."""
    text_lower = text.lower()
    found = Counter()

    for keyword in TAG_LABELS:
        count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
        if count == 0:
            # Also check as class/id pattern
            count = len(re.findall(re.escape(keyword), text_lower))
        if count > 0:
            found[keyword] = count

    return found
