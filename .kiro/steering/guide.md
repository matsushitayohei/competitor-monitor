# Competitor Monitor - 開発ガイド

## プロジェクト概要

不動産ポータル競合サイト（SUUMO, athome, カナリー）のUI/UX変更を自動検知し、
LIFULL HOME'Sへの適用をAIがアドバイスするモニタリングシステム。

## 技術スタック

- フロントエンド: Next.js 14+ (App Router, TypeScript, Tailwind CSS)
- バックエンド: Next.js API Routes
- スクレイピング: Python + Playwright
- DB: Supabase (PostgreSQL)
- 画像保存: Supabase Storage
- スケジューラ: GitHub Actions (毎日 JST 6:00)
- ホスティング: Vercel
- 通知: Slack Incoming Webhook
- AI分析: Google Gemini API (gemini-1.5-pro)
- 認証: Supabase Auth (Google OAuth, @lifull.com ドメイン制限)
- MCP連携: TypeScript MCP Server

## コーディング規約

- TypeScript strict mode
- ESLint + Prettier
- コンポーネントは関数コンポーネント + hooks
- Server Components をデフォルトで使用、クライアント操作が必要な場合のみ "use client"
- Tailwind CSS でスタイリング（CSS Modules は使わない）
- API Routes は /app/api/ 配下に配置
- エラーハンドリングは try-catch + ユーザーフレンドリーなエラー表示

## DB設計方針

- Supabase の RLS (Row Level Security) を有効化
- テーブル名は snake_case
- タイムスタンプは全て UTC で保存、表示時に JST 変換
- ソフトデリート（deleted_at カラム）

## データ保持方針

- スナップショット・変更履歴は無期限保持（自動削除なし）
- 更新は上書きではなく追加（アーカイブ形式）
- 全ての履歴を蓄積し、MCP経由でサイト改善の自動化時に現状把握に活用
- Snapshot テーブル: キャプチャごとに新レコード追加、過去分は削除しない
- Change テーブル: 変更検知ごとに新レコード追加、isReviewed で既読管理

## 変更検知ロジック

- DOM構造差分がメイン検知
- 物件固有情報（価格、住所、築年数等）は除外
- ビジュアル差分は補助（Before/After画像比較用）
- 物件詳細URLの掲載切れ検知（ハイブリッド方式）:
  - HTTP 404 の場合 → 一覧から自動で新URL取得
  - HTTP 200 だが「掲載終了」表示の場合 → HTML内のキーワードで検出し、一覧から新URL取得
  - 検知パターンは expired_detector.py で各サービス別に定義
  - 切替成功/失敗をSlackに通知
