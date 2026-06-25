# Competitor Monitor

競合UIUXモニタリングシステム — 不動産ポータルサイトの競合サービスのUI/UX変更を自動検知・分析し、自社サービス（LIFULL HOME'S）への適用をAIがアドバイスするツール。

## 概要

| 項目 | 内容 |
|:---|:---|
| 対象競合 | SUUMO, athome, カナリー |
| 対象ページ | 物件一覧、物件詳細（賃貸マンション） |
| 検知頻度 | 毎日 JST 6:00 |
| 通知先 | Slack |
| AI分析 | Google Gemini API |

## アーキテクチャ

GitHub Actions (毎日6:00) -> Python + Playwright でスクレイピング -> DOM差分 + 画像差分を生成 -> Gemini で変更分析 -> Supabase に保存 -> Slack 通知 -> Next.js 管理画面で確認 -> MCP Server 経由で Kiro から参照可能

## 技術スタック

| レイヤー | 技術 |
|:---|:---|
| フロントエンド | Next.js 14+ (App Router) |
| バックエンド | Next.js API Routes |
| スクレイピング | Python + Playwright |
| DB | Supabase (PostgreSQL) |
| 画像保存 | Supabase Storage |
| スケジューラ | GitHub Actions |
| ホスティング | Vercel |
| 通知 | Slack Incoming Webhook |
| AI分析 | Google Gemini API |
| 認証 | Supabase Auth (Google OAuth) |
| MCP連携 | MCP Server (TypeScript) |

## セットアップ

詳細は docs/setup.md を参照してください。
