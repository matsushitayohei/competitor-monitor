"""Slack Block Kit notification module for the daily competitor scan."""

import os
from typing import Optional

import httpx


# ---- ページ種別・カテゴリのラベルマップ ----

_PAGE_TYPE_LABELS: dict[str, str] = {
    "detail": "物件詳細",
    "list": "一覧",
    "top": "トップ",
    "search": "検索結果",
}

_CATEGORY_LABELS: dict[str, str] = {
    "CRO": "CRO",
    "AD_PRODUCT": "広告商品",
    "SEO": "SEO",
    "AI": "AI機能",
    "OTHER": "その他",
}


def page_type_label(page_type: str) -> str:
    """Convert page_type to Japanese label."""
    return _PAGE_TYPE_LABELS.get(page_type, page_type or "不明")


def priority_rank(priority: str) -> int:
    """Return numeric rank for priority comparison (high=3, medium=2, low=1)."""
    return {"high": 3, "medium": 2, "low": 1}.get(priority, 0)


def group_changes_by_url(changes: list[dict]) -> list[dict]:
    """Group changes by URL, merging PC/SP into one entry per URL.

    Returns a deduplicated list with merged device info and highest priority.
    """
    from collections import OrderedDict

    grouped: OrderedDict[str, dict] = OrderedDict()

    for r in changes:
        url = r["url"]
        if url not in grouped:
            grouped[url] = {
                "url": url,
                "service": r["service"],
                "devices": [r["device"]],
                "category": r.get("category", "OTHER"),
                "summary": r.get("summary", "DOM構造に変更を検知"),
                "priority": r.get("priority", "low"),
                "page_type": r.get("page_type", ""),
            }
        else:
            if r["device"] not in grouped[url]["devices"]:
                grouped[url]["devices"].append(r["device"])
            # Keep the highest priority
            if priority_rank(r.get("priority", "low")) > priority_rank(grouped[url]["priority"]):
                grouped[url]["priority"] = r.get("priority", "low")
            # Keep the longer summary
            new_summary = r.get("summary", "")
            if new_summary and len(new_summary) > len(grouped[url]["summary"] or ""):
                grouped[url]["summary"] = new_summary

    return list(grouped.values())


def format_change_block(item: dict) -> dict:
    """Format a single grouped change as a Slack Block Kit section."""
    service_display = item["service"].upper()
    label = page_type_label(item.get("page_type", ""))
    devices = "/".join(item.get("devices", []))
    category = _CATEGORY_LABELS.get(item.get("category", "OTHER"), "その他")
    summary = item.get("summary", "変更を検知")
    if summary and len(summary) > 120:
        summary = summary[:117] + "..."

    text = (
        f"*【{service_display}】{label}* ({devices})\n"
        f"分類: {category}\n"
        f"{summary}"
    )
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def build_blocks(results: list[dict], app_url: str) -> Optional[list[dict]]:
    """Build Slack Block Kit blocks from scan results.

    Returns None when there is nothing worth notifying.
    """
    changes = [r for r in results if r["change_detected"]]
    rotations = [r for r in results if r.get("url_rotated")]
    no_fallback = [
        r for r in results
        if r["status"].endswith("_no_fallback") or r["status"] == "expired_no_valid_fallback"
    ]

    if not changes and not rotations and not no_fallback:
        return None

    blocks: list[dict] = []

    # --- 変更レポートヘッダー ---
    if changes:
        grouped = group_changes_by_url(changes)

        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔍 競合変更レポート ({len(grouped)}箇所)",
                "emoji": True,
            },
        })

        high = [g for g in grouped if g["priority"] == "high"]
        medium = [g for g in grouped if g["priority"] == "medium"]
        low = [g for g in grouped if g["priority"] == "low"]

        if high:
            blocks.append({"type": "divider"})
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*🔴 対応検討推奨*"}})
            for item in high:
                blocks.append(format_change_block(item))

        if medium:
            blocks.append({"type": "divider"})
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*🟡 参考情報*"}})
            for item in medium:
                blocks.append(format_change_block(item))

        if low:
            blocks.append({"type": "divider"})
            low_text = "*⚪ その他の変更*\n"
            for item in low:
                label = page_type_label(item.get("page_type", ""))
                low_text += f"• {item['service'].upper()} ({label}): {item['summary'][:60]}\n"
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": low_text.strip()}})

    # --- URL 自動切替 ---
    if rotations:
        blocks.append({"type": "divider"})
        text = f"*🔄 物件URL自動切替: {len(rotations)}件*\n"
        for r in rotations:
            text += f"• {r['service']} ({r['device']}): {r.get('new_url', 'N/A')}\n"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text.strip()}})

    # --- URL 切替失敗 ---
    if no_fallback:
        blocks.append({"type": "divider"})
        text = f"*⚠️ URL切替失敗（要手動対応）: {len(no_fallback)}件*\n"
        for r in no_fallback:
            text += f"• {r['service']} ({r['device']}): {r['url']}\n"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text.strip()}})

    # --- レンダリング失敗（30%超のときだけ通知） ---
    rendering_failures = [r for r in results if r["status"] == "rendering_failure"]
    if len(rendering_failures) >= len(results) * 0.3:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*🔧 レンダリング失敗（誤検知除外）: {len(rendering_failures)}件*\n"
                    "ページ読み込み不完全を検知し自動スキップ。頻発する場合はスクレイパーの待機時間調整が必要。"
                ),
            },
        })

    # --- フッター ---
    if app_url:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"📊 <{app_url}/changes|ダッシュボードで詳細を確認>"}],
        })

    return blocks


async def send_slack_notification(results: list[dict]) -> None:
    """Send a structured Slack Block Kit notification about detected changes."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return

    app_url = os.environ.get("NEXT_PUBLIC_APP_URL", "")
    blocks = build_blocks(results, app_url)
    if blocks is None:
        return

    changes = [r for r in results if r["change_detected"]]
    fallback_text = f"競合変更レポート: {len(changes)}件の変更を検知"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json={"text": fallback_text, "blocks": blocks},
                timeout=10,
            )
            response.raise_for_status()
    except Exception as e:
        print(f"Slack notification error: {e}")
