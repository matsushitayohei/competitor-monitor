# UIUX構造化抽出システム - 実装タスクリスト

**プロジェクト名**: Competitor Monitor - UIUX Structure Extraction  
**作成日**: 2026-08-14  
**最終更新**: 2026-08-14

---

## プロジェクト情報

- **目的**: 競合サイト + HOME'SのUIUX構造をコンポーネントレベルで抽出・蓄積し、AIによる改善自動化の材料とする
- **対象**: SUUMO, athome, カナリー, LIFULL HOME'S
- **重点ページ**: 問い合わせフォーム（CV直結）、物件詳細、検索結果一覧
- **開始日**: 2026-08-14
- **予定完了日**: 2026-08-18
- **総予定工数**: 16h

---

## タスク一覧

| ID | 先行タスクID | タスク名 | 状態 | 予定工数 | 実績工数 | 完了日時 | 備考 |
|:---|:---:|:---|:---:|:---:|:---:|:---|:---|
| 1 | - | DBスキーマ設計・マイグレーション | 完了 | 1h | 0.5h | 2026-08-14 | scripts/migrate_page_structure.sql |
| 2 | - | Prismaスキーマ更新 | 完了 | 0.5h | 0.5h | 2026-08-14 | schema.prisma に3モデル追加 |
| 3 | 1 | Python構造抽出コア (structure_extractor.py) | 完了 | 3h | 2h | 2026-08-14 | コンポーネント分類、セクション解析 |
| 4 | 3 | フォーム専用分析 (form_analyzer.py) | 完了 | 2h | 1.5h | 2026-08-14 | フィールド構成、バリデーション、CTA分析 |
| 5 | 3 | CV要素検出 (cv_detector.py) | 完了 | 1h | 1h | 2026-08-14 | CTA、ソーシャルプルーフ、緊急性表現 |
| 6 | 1,3 | DB保存モジュール (structure_db.py) | 完了 | 1h | 0.5h | 2026-08-14 | 構造データ保存、ハッシュ比較 |
| 7 | 6 | 既存スキャナー統合 (main.py拡張) | 完了 | 1.5h | 0.5h | 2026-08-14 | scan_page内で構造抽出を実行 |
| 8 | 1 | HOME'Sスキャン対応 (own_site_scanner.py) | 完了 | 2h | 1h | 2026-08-14 | OwnPage管理 + 構造抽出実行 |
| 9 | 2,6 | MCP Server ツール追加 | 完了 | 3h | 2h | 2026-08-14 | 6ツール追加 |
| 10 | 7,8 | GitHub Actions 統合 | 完了 | 1h | 0.5h | 2026-08-14 | daily-scan.yml にHOME'Sスキャンステップ追加 |

---

## タスク詳細

### タスク1: DBスキーマ設計・マイグレーション

**前提条件**:
- Vercel Postgres への接続情報 (DATABASE_URL)

**詳細手順**:

1. 以下のテーブルを Vercel Storage の Query タブで作成:

```sql
-- 競合サイト ページ構造スナップショット
CREATE TABLE "PageStructure" (
  "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
  "pageId" TEXT NOT NULL,
  "capturedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "structureSummary" JSONB NOT NULL,       -- Level 1: セクション構成サマリー
  "sections" JSONB NOT NULL,               -- Level 2: セクション詳細 + コンポーネント
  "cvPoints" JSONB,                        -- CV要素抽出
  "formAnalysis" JSONB,                    -- フォーム専用分析（フォームページのみ）
  "componentCount" INTEGER NOT NULL DEFAULT 0,
  "hash" VARCHAR(64) NOT NULL,             -- 構造ハッシュ（変更あった時のみ保存）
  "metadata" JSONB,                        -- viewport, URL, device等

  CONSTRAINT "PageStructure_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "PageStructure_pageId_fkey" FOREIGN KEY ("pageId") 
    REFERENCES "MonitoredPage"("id") ON DELETE CASCADE
);

CREATE INDEX "PageStructure_pageId_capturedAt_idx" ON "PageStructure"("pageId", "capturedAt" DESC);
CREATE INDEX "PageStructure_hash_idx" ON "PageStructure"("hash");

-- HOME'S (自社) 監視ページ
CREATE TABLE "OwnPage" (
  "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
  "name" VARCHAR(255) NOT NULL,
  "pageType" VARCHAR(50) NOT NULL,         -- form, detail, list, top
  "url" TEXT NOT NULL,
  "device" VARCHAR(10) NOT NULL DEFAULT 'pc',
  "category" VARCHAR(50) DEFAULT 'chintai', -- chintai, buy, etc.
  "isActive" BOOLEAN NOT NULL DEFAULT true,
  "lastScannedAt" TIMESTAMP(3),
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deletedAt" TIMESTAMP(3),

  CONSTRAINT "OwnPage_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "OwnPage_pageType_device_idx" ON "OwnPage"("pageType", "device");

-- HOME'S ページ構造スナップショット
CREATE TABLE "OwnPageStructure" (
  "id" TEXT NOT NULL DEFAULT gen_random_uuid()::text,
  "ownPageId" TEXT NOT NULL,
  "capturedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "structureSummary" JSONB NOT NULL,
  "sections" JSONB NOT NULL,
  "cvPoints" JSONB,
  "formAnalysis" JSONB,
  "componentCount" INTEGER NOT NULL DEFAULT 0,
  "hash" VARCHAR(64) NOT NULL,
  "metadata" JSONB,

  CONSTRAINT "OwnPageStructure_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "OwnPageStructure_ownPageId_fkey" FOREIGN KEY ("ownPageId") 
    REFERENCES "OwnPage"("id") ON DELETE CASCADE
);

CREATE INDEX "OwnPageStructure_ownPageId_capturedAt_idx" ON "OwnPageStructure"("ownPageId", "capturedAt" DESC);
CREATE INDEX "OwnPageStructure_hash_idx" ON "OwnPageStructure"("hash");

-- Change テーブルに構造連携カラム追加
ALTER TABLE "Change" ADD COLUMN "structureBeforeId" TEXT;
ALTER TABLE "Change" ADD COLUMN "structureAfterId" TEXT;
ALTER TABLE "Change" ADD CONSTRAINT "Change_structureBeforeId_fkey" 
  FOREIGN KEY ("structureBeforeId") REFERENCES "PageStructure"("id") ON DELETE SET NULL;
ALTER TABLE "Change" ADD CONSTRAINT "Change_structureAfterId_fkey" 
  FOREIGN KEY ("structureAfterId") REFERENCES "PageStructure"("id") ON DELETE SET NULL;
```

**完了条件**:
- [ ] PageStructure テーブルが作成され、MonitoredPage と FK 連携
- [ ] OwnPage テーブルが作成され、HOME'Sページを登録可能
- [ ] OwnPageStructure テーブルが作成され、OwnPage と FK 連携
- [ ] Change テーブルに structureBeforeId / structureAfterId カラム追加

**検証方法**:
```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('PageStructure', 'OwnPage', 'OwnPageStructure');
```

---

### タスク2: Prismaスキーマ更新

**前提条件**:
- タスク1のマイグレーション完了（並行して作業可能だが、DB反映はタスク1後）

**詳細手順**:

1. `apps/web/prisma/schema.prisma` に新モデルを追加
2. `prisma generate` で型を再生成

**追加するモデル**:
- `PageStructure` (pageId → MonitoredPage)
- `OwnPage` (独立)
- `OwnPageStructure` (ownPageId → OwnPage)
- `Change` モデルに `structureBeforeId`, `structureAfterId` フィールド追加

**完了条件**:
- [ ] schema.prisma に 3 モデル追加
- [ ] Change モデルにリレーション追加
- [ ] `prisma generate` が正常完了
- [ ] MCP サーバー側にも型が反映

---

### タスク3: Python構造抽出コア (structure_extractor.py)

**前提条件**:
- なし（単体開発可能）

**詳細手順**:

1. `packages/scraper/src/structure_extractor.py` を新規作成
2. 以下の機能を実装:
   - HTMLからセクション構造を解析（`<section>`, `<article>`, `<form>`, `<nav>`, `<header>`, `<footer>` + 主要div）
   - 各セクション内のコンポーネントを分類
   - 階層的JSONを生成（summary / sections / components）

**コンポーネント分類ルール**:

```python
COMPONENT_TYPES = {
    # フォーム要素（CV重要）
    "input_text": "input[type=text], input[type=email], input[type=name]",
    "input_tel": "input[type=tel]",
    "input_number": "input[type=number]",
    "input_password": "input[type=password]",
    "textarea": "textarea",
    "select": "select",
    "checkbox": "input[type=checkbox]",
    "radio": "input[type=radio]",
    "button_submit": "button[type=submit], input[type=submit]",
    "button_action": "button:not([type=submit])",
    
    # CTA要素
    "cta_primary": "[class*=btn-primary], [class*=cta], a[class*=button][class*=primary]",
    "cta_secondary": "[class*=btn-secondary], [class*=btn-outline]",
    "cta_line": "a[href*=line.me], [class*=line-btn]",
    "cta_tel": "a[href^=tel:]",
    
    # メディア
    "image_carousel": "[class*=carousel], [class*=slider], [class*=swiper], [class*=gallery]",
    "image_single": "img:not([width='1']):not([height='1'])",
    "video": "video, [class*=video-player]",
    
    # ナビゲーション
    "tab_nav": "[role=tablist], [class*=tab-nav]",
    "breadcrumb": "[class*=breadcrumb], nav[aria-label*=breadcrumb]",
    "pagination": "[class*=pagination], [class*=pager]",
    "bottom_nav": "[class*=bottom-nav], [class*=footer-nav]",
    
    # 固定要素
    "sticky_header": "header[class*=sticky], [class*=fixed-header]",
    "sticky_footer": "[class*=fixed-bottom], [class*=sticky-footer], [style*='position: fixed'][style*='bottom']",
    "sticky_cta": "[class*=sticky][class*=btn], [class*=fixed][class*=cta]",
    
    # 情報表示
    "table": "table:not([role=presentation])",
    "accordion": "[class*=accordion], [class*=collapsible], details",
    "card": "[class*=card], [class*=cassette]",
    "badge": "[class*=badge], [class*=tag], [class*=chip]",
    "rating": "[class*=rating], [class*=review-score], [class*=star]",
    
    # ソーシャルプルーフ
    "social_proof": "[class*=review-count], [class*=view-count], [class*=favorite-count]",
    "urgency": "[class*=remaining], [class*=limited], [class*=hurry]",
}
```

**出力JSON構造**:
```json
{
  "summary": {
    "sectionCount": 8,
    "componentCount": 45,
    "formCount": 1,
    "ctaCount": 3,
    "hasStickyElements": true
  },
  "sections": [
    {
      "id": "section-0",
      "type": "header",
      "tagName": "header",
      "position": 0,
      "components": [
        {
          "type": "image_single",
          "tagName": "img",
          "attributes": {"alt": "SUUMO", "class": "logo"},
          "position": 0
        }
      ]
    }
  ]
}
```

**完了条件**:
- [ ] HTMLを入力として階層的JSON構造を出力できる
- [ ] セクション分割が正しく動作（form, nav, header, footer, main article 等）
- [ ] コンポーネント分類が全カテゴリで動作
- [ ] SUUMO / athome / カナリー のサンプルHTMLで検証済み

---

### タスク4: フォーム専用分析 (form_analyzer.py)

**前提条件**:
- タスク3完了（structure_extractor.py のコンポーネント分類を利用）

**詳細手順**:

1. `packages/scraper/src/form_analyzer.py` を新規作成
2. `<form>` 要素を検出し、以下を分析:
   - フィールド構成（種類・数・必須/任意・ラベル）
   - ステップ数（マルチステップフォーム対応）
   - バリデーション方式（リアルタイム / サブミット時 / なし）
   - 送信ボタンの設計（ラベル、色、サイズ、位置）
   - マイクロコピー（「しつこい営業はしません」等）
   - プログレスバー有無
   - 推定入力時間（フィールド数から算出）

**出力JSON構造**:
```json
{
  "forms": [
    {
      "id": "form-0",
      "action": "/inquiry/submit",
      "method": "POST",
      "totalFields": 8,
      "requiredFields": 5,
      "fieldTypes": {
        "text": 2, "tel": 1, "email": 1, "select": 2, "checkbox": 1, "radio": 1
      },
      "fields": [
        {
          "type": "input_text",
          "name": "name",
          "label": "お名前",
          "required": true,
          "placeholder": "山田太郎",
          "position": 0,
          "hasValidation": true
        }
      ],
      "steps": 1,
      "hasProgressBar": false,
      "validationType": "realtime",
      "submitButton": {
        "label": "無料で問い合わせる",
        "color": "#FF6B00",
        "size": "full_width",
        "position": "form_bottom"
      },
      "microCopy": [
        "しつこい営業はしません",
        "1分で完了"
      ],
      "socialProof": [
        "本日5人が問い合わせ済み"
      ],
      "estimatedCompletionMinutes": 2
    }
  ]
}
```

**完了条件**:
- [ ] フォーム要素の検出・分析が正しく動作
- [ ] フィールド構成（種類・数・必須）を正確に抽出
- [ ] 送信ボタンの属性（ラベル・色・サイズ）を抽出
- [ ] マイクロコピー/ソーシャルプルーフを検出
- [ ] SUUMO問い合わせフォーム / athomeフォーム で検証済み

---

### タスク5: CV要素検出 (cv_detector.py)

**前提条件**:
- タスク3完了

**詳細手順**:

1. `packages/scraper/src/cv_detector.py` を新規作成
2. ページ内のCV関連要素を検出・分類:
   - CTA（プライマリ / セカンダリ / LINE / 電話）
   - ソーシャルプルーフ（閲覧数、問い合わせ数、レビュー数）
   - 緊急性表現（残りN件、期間限定）
   - 固定CTA（スティッキー要素）
   - マイクロコピー（安心訴求）

**出力JSON構造**:
```json
{
  "cvPoints": [
    {
      "type": "primary_cta",
      "element": "button",
      "label": "無料で問い合わせる",
      "position": "form_bottom",
      "isSticky": false,
      "style": {
        "backgroundColor": "#FF6B00",
        "width": "100%",
        "height": "56px"
      },
      "microCopy": "しつこい営業はありません",
      "socialProof": null,
      "urgencyText": null
    }
  ],
  "summary": {
    "totalCtaCount": 3,
    "stickyCtaCount": 1,
    "socialProofCount": 2,
    "urgencyCount": 1,
    "hasMicroCopy": true
  }
}
```

**完了条件**:
- [ ] CTA要素の検出・分類が正しく動作
- [ ] 固定要素（position: fixed/sticky）を検出
- [ ] ソーシャルプルーフ/緊急性テキストを抽出
- [ ] マイクロコピーを検出

---

### タスク6: DB保存モジュール (structure_db.py)

**前提条件**:
- タスク1（DBスキーマ作成済み）
- タスク3（構造抽出モジュール完成）

**詳細手順**:

1. `packages/scraper/src/structure_db.py` を新規作成
2. 実装する関数:
   - `save_page_structure(page_id, structure_data)` — 構造ハッシュを比較し、変更時のみ新レコード保存
   - `get_latest_page_structure(page_id)` — 最新の構造データ取得
   - `save_own_page_structure(own_page_id, structure_data)` — HOME'S構造保存
   - `get_latest_own_page_structure(own_page_id)` — HOME'S最新構造取得
   - `get_active_own_pages()` — アクティブなHOME'Sページ一覧

**完了条件**:
- [ ] 構造データのJSON保存が正常動作
- [ ] ハッシュ比較で変更なし時はスキップ
- [ ] 変更あり時のみ新レコード保存
- [ ] HOME'S用の保存・取得も動作

---

### タスク7: 既存スキャナー統合 (main.py拡張)

**前提条件**:
- タスク6完了（DB保存が動作）
- タスク3,4,5完了（抽出モジュール完成）

**詳細手順**:

1. `main.py` の `scan_page()` 内に構造抽出ステップを追加
2. DOM取得後（Step 2の後）に構造抽出を実行
3. 構造ハッシュを比較し、変更時のみ保存
4. Change保存時に `structureBeforeId` / `structureAfterId` を設定

**変更箇所**:
- `scan_page()` の Step 2（DOM構造抽出）の後に構造抽出追加
- `save_change()` 呼び出し時に構造IDを渡す

**完了条件**:
- [ ] 既存のスキャンフローを壊さずに構造抽出が統合
- [ ] 構造データがPageStructureテーブルに保存される
- [ ] Change レコードに構造IDが紐付く
- [ ] 構造抽出エラー時もスキャン全体は継続（try-catch）

---

### タスク8: HOME'Sスキャン対応 (own_site_scanner.py)

**前提条件**:
- タスク1（OwnPageテーブル作成済み）
- タスク3,4,5,6完了

**詳細手順**:

1. `packages/scraper/src/own_site_scanner.py` を新規作成
2. 実装内容:
   - OwnPage テーブルからアクティブページを取得
   - 各ページをPlaywrightでキャプチャ
   - structure_extractor / form_analyzer / cv_detector で分析
   - OwnPageStructure に保存
3. HOME'Sの初期ページ登録SQL:

```sql
-- 賃貸 問い合わせフォーム
INSERT INTO "OwnPage" (id, name, "pageType", url, device, category) VALUES
  (gen_random_uuid()::text, 'HOME''S 賃貸 問い合わせフォーム SP', 'form', 'https://www.homes.co.jp/chintai/room-inquiry/', 'sp', 'chintai'),
  (gen_random_uuid()::text, 'HOME''S 賃貸 物件詳細 SP', 'detail', 'https://www.homes.co.jp/chintai/b-[TBD]/', 'sp', 'chintai'),
  (gen_random_uuid()::text, 'HOME''S 賃貸 一覧 SP', 'list', 'https://www.homes.co.jp/chintai/tokyo/city/', 'sp', 'chintai'),
  (gen_random_uuid()::text, 'HOME''S 賃貸 問い合わせフォーム PC', 'form', 'https://www.homes.co.jp/chintai/room-inquiry/', 'pc', 'chintai'),
  (gen_random_uuid()::text, 'HOME''S 賃貸 物件詳細 PC', 'detail', 'https://www.homes.co.jp/chintai/b-[TBD]/', 'pc', 'chintai'),
  (gen_random_uuid()::text, 'HOME''S 賃貸 一覧 PC', 'list', 'https://www.homes.co.jp/chintai/tokyo/city/', 'pc', 'chintai');
```

**注意事項**:
- HOME'Sの物件詳細URLは掲載切れ問題があるため、初回は一覧ページから取得して設定
- 実際のURLは実装時に確認して設定

**完了条件**:
- [ ] OwnPage にHOME'Sページが登録済み
- [ ] 全ページのキャプチャ + 構造抽出が正常動作
- [ ] OwnPageStructure にデータが保存される
- [ ] 競合と同じ形式のJSONが生成される（比較可能）

---

### タスク9: MCP Server ツール追加

**前提条件**:
- タスク2完了（Prismaスキーマに型定義あり）
- タスク6完了（DBにデータが存在）

**詳細手順**:

1. `packages/mcp-server/src/index.ts` に以下のツールを追加:

**ツール一覧**:

| ツール名 | 説明 | パラメータ |
|:---|:---|:---|
| `get_page_structure` | 競合ページの最新構造を取得 | service, page_type, device, depth(summary/full) |
| `get_own_page_structure` | HOME'Sページの最新構造を取得 | page_type, device, category, depth |
| `compare_with_homes` | 競合とHOME'Sの構造を比較 | service, page_type, device |
| `get_form_comparison` | フォーム構造の比較 | service (省略時は全社比較) |
| `get_cv_gaps` | HOME'Sに足りないCV要素一覧 | page_type (省略時は全ページ) |
| `get_structure_history` | 構造変遷の履歴 | service, page_type, device, since |

**compare_with_homes の動的比較ロジック**:
- 指定されたpage_type/deviceで競合の最新PageStructureとHOME'Sの最新OwnPageStructureを取得
- セクション構成、コンポーネント種類、CV要素を比較
- 「競合にあってHOME'Sにないもの」をgapsとして返す

**完了条件**:
- [ ] 全6ツールが動作
- [ ] `get_page_structure` で構造データが正しく返る
- [ ] `compare_with_homes` で差分が計算される
- [ ] `get_form_comparison` でフォーム要素が比較される
- [ ] `get_cv_gaps` でCV差分が返る

---

### タスク10: GitHub Actions 統合

**前提条件**:
- タスク7,8完了（スキャナー統合 + HOME'Sスキャン動作）

**詳細手順**:

1. `.github/workflows/daily-scan.yml` に構造抽出ステップを追加:
   - 既存のmain.py実行で自動的に構造抽出も実行される（タスク7で統合済み）
   - HOME'Sスキャン用の新ステップを追加

```yaml
      - name: Run own site structure scan
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          python packages/scraper/src/own_site_scanner.py
```

**完了条件**:
- [ ] daily-scan.yml にHOME'Sスキャンステップ追加
- [ ] 手動トリガーで正常実行を確認
- [ ] エラー時の通知設定

---

## 工数サマリー

### フェーズ別工数

- **DB/スキーマ設計** (タスク1,2): 予定 1.5h
- **Python抽出モジュール** (タスク3,4,5): 予定 6h
- **統合・DB連携** (タスク6,7,8): 予定 4.5h
- **MCP Server** (タスク9): 予定 3h
- **CI/CD** (タスク10): 予定 1h

### 合計工数

- **予定工数**: 16h

---

## リスク管理

| リスクID | リスク内容 | 発生確率 | 影響度 | 対応策 |
|:---|:---|:---:|:---:|:---|
| R1 | 競合サイトのDOM構造が複雑でセクション分割が不正確 | 中 | 中 | SUUMO/athome/canaryのサンプルHTMLで事前検証、分割ルールを逐次改善 |
| R2 | HOME'Sページが認証必要 or 構造取得困難 | 低 | 中 | 公開ページのみ対象。取得困難な場合はスキップ |
| R3 | 構造データが巨大化しDBストレージ圧迫 | 中 | 低 | ハッシュ比較で変更時のみ保存、JSONBの圧縮 |
| R4 | CSSクラス名でのコンポーネント分類が不安定 | 高 | 中 | 複数のセレクタパターンを用意、フォールバック分類あり |
| R5 | Playwright実行時間増加でGitHub Actions タイムアウト | 中 | 中 | 構造抽出は既存キャプチャのHTMLを再利用（追加リクエストなし） |

---

## 実装順序（Wave分割）

**Wave 1** (並行可能): タスク1, タスク2, タスク3
- DB設計とPython抽出コアは独立して開発可能

**Wave 2** (タスク3完了後): タスク4, タスク5
- form_analyzer と cv_detector は structure_extractor に依存

**Wave 3** (Wave1,2完了後): タスク6, タスク7, タスク8
- DB保存と統合はDB + 抽出モジュール両方必要

**Wave 4** (Wave3完了後): タスク9, タスク10
- MCP Server とCI/CDは全体統合後

---

## 備考

- LLMハイブリッド解釈（Phase 2）: データ蓄積後に精度を評価し、必要に応じて追加実装
- UXパターンカタログ（Phase 2）: 1〜2ヶ月のデータ蓄積後に実装検討
- 自動改善提案（Phase 3）: compare結果をKiroが解釈する運用で開始
