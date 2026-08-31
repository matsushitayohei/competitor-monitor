# Competitor Monitor - 開発ガイド

## プロジェクト概要

不動産ポータル競合サイト（SUUMO, athome, カナリー）のUI/UX変更を自動検知し、
LIFULL HOME'Sへの適用をAIがアドバイスするモニタリングシステム。

## 技術スタック

- フロントエンド: Next.js 14+ (App Router, TypeScript, Tailwind CSS)
- バックエンド: Next.js API Routes
- スクレイピング: Python + Playwright
- DB: Vercel Postgres (Neon ベース、Vercel Storage で管理)
- 画像保存: Vercel Blob Storage
- スケジューラ: GitHub Actions (毎日 JST 6:00)
- ホスティング: Vercel
- 通知: Slack Incoming Webhook
- AI分析: ルールベース分類（自動） + Kiro分析（MCP経由、オンデマンド）
- 認証: NextAuth.js (Google OAuth, @lifull.com ドメイン制限)
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

- Vercel Postgres (Neon ベース) — Vercel ダッシュボードの Storage タブで管理
- Prisma ORM でスキーマ管理
- マイグレーションは Vercel Storage の Query タブで手動実行（read-only トグルを OFF にして実行）
- テーブル名は PascalCase (Prisma デフォルト)
- タイムスタンプは全て UTC で保存、表示時に JST 変換
- ソフトデリート（deletedAt カラム）

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

## 監視サービス追加時のチェックリスト

新しいサービスを追加する際は、以下を必ず実施すること:

1. **サービス登録** (DB): name, displayName, baseUrl を設定
2. **監視ページ登録** (DB): 一覧ページ + 詳細ページを PC/SP で登録
   - URLは実際のサイトにアクセスして正しいことを確認する
   - PC/SPでURLが異なる場合は別々に登録、同じならdevice違いで同一URL
3. **掲載切れ自動対応** (Python):
   - `expired_detector.py`: サービス固有の掲載終了パターンを定義
   - `url_fallback.py`: 
     - `SERVICE_DETAIL_LINK_SELECTORS`: 一覧ページから詳細リンクを取得するCSSセレクタ
     - `DETAIL_URL_PATTERNS`: 詳細ページURLの正規表現パターン
     - `_identify_service()`: ドメイン→サービス名のマッピング追加
4. **コミット & デプロイ**: 変更をpush（Vercel自動デプロイ）


## ビジュアル差分（visual diff）の設計判断

### フルページ画像をフォールバックとして保存しない理由

`generate_visual_diff()` が `None` を返した場合（フィルタ不通過）でも、フルページ画像を
`beforeScreenshotPath` / `afterScreenshotPath` にフォールバック保存する実装は**意図的に行っていない**。

理由: Vercel Blob Storage のコスト・容量削減が優先。フルページ画像（JPEG 60% 圧縮後でも数百KB〜1MB）を
変更検知のたびに2枚保存するとストレージ増大が著しい。クロップ画像（変更箇所のみ、通常数十KB）に絞ることで
コストを抑えている。

`generate_visual_diff()` が `None` のとき、変更履歴カードの画像エリアは非表示になるが、
DOM差分テキストが代替情報として常に表示される。これは仕様。

### フィルタ閾値の設定根拠

`packages/scraper/src/visual_diff.py` の定数は以下の理由で設定されている:

| 定数 | 現在値 | 理由 |
|------|--------|------|
| `_MAX_REGIONS` | 30 | 不動産ポータルは複数セクションが同時に変わるケースが多いため緩め |
| `_MIN_REGION_CONCENTRATION` | 0.005 (0.5%) | UIコンポーネント単位の小さな変更も拾えるよう緩め |
| 高さ変化許容閾値 | 50% | 物件数増減による縦幅変動を許容するため旧値(25%)から拡張 |

閾値を厳しくしすぎると「画像なし」の変更履歴が増え、緩くしすぎると動的コンテンツ（価格・物件画像）の
ノイズが混入する。現状値はこのトレードオフのバランス点。再調整が必要な場合は上記3定数を変更する。
