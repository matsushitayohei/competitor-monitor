# Competitor Monitor

競合UIUXモニタリングシステム — 不動産ポータルサイトの競合サービスをはじめ各業界のサービスのUI/UX変更を自動検知・分析し、自社サービス（LIFULL HOME'S）への適用をAIがアドバイスするツール。

## 概要

| 項目 | 内容 |
|:---|:---|
| 対象競合 | SUUMO, athome, カナリー（+ 業界横断ベンチマーク） |
| 対象ページ | 物件一覧、物件詳細（賃貸マンション）など |
| 検知頻度 | 毎日 JST 10:00 |
| 通知先 | Slack |
| AI分析 | ルールベース自動分類 + Kiro on-demand分析（MCP経由） |

## アーキテクチャ

GitHub Actions (毎日 JST 10:00) → Python + Playwright でスクレイピング → DOM差分 + 画像差分を生成 → ルールベースで変更分類・サマリ生成 → Vercel Postgres に保存 → Slack 通知 → Next.js 管理画面で確認 → MCP Server 経由で Kiro からアドバイス生成・参照可能

## 技術スタック

| レイヤー | 技術 |
|:---|:---|
| フロントエンド | Next.js 14+ (App Router) |
| バックエンド | Next.js API Routes |
| スクレイピング | Python + Playwright |
| DB | Vercel Postgres (Neon ベース) |
| 画像保存 | Vercel Blob Storage |
| スケジューラ | GitHub Actions |
| ホスティング | Vercel |
| 通知 | Slack Incoming Webhook |
| AI分析 | ルールベース分類（自動）+ Kiro on-demand（MCP経由） |
| 認証 | NextAuth.js (Google OAuth, @lifull.com ドメイン制限) |
| MCP連携 | MCP Server (TypeScript) |

## セットアップ

詳細は docs/setup.md を参照してください。
