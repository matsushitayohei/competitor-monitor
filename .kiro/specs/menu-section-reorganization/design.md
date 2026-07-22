# Design Document: menu-section-reorganization

## Overview

サイドバーナビゲーションを現在のフラットリスト構造から、ドメイン別のセクション（「UIUX」「PRESS」）に分割し、設定項目を独立配置する。変更は `apps/web/components/sidebar.tsx` 単一ファイル内で完結し、既存の Server Component アーキテクチャ、Next.js App Router、Tailwind CSS を維持する。

### 設計方針

- **最小変更**: 既存コンポーネント構造（Server Component + signOut server action）を変更しない
- **データ駆動**: ナビゲーション定義を型付きデータ構造に変更し、レンダリングロジックをデータから導出
- **セマンティック HTML**: `<section>` + `aria-labelledby` でアクセシビリティ対応
- **アクティブ状態**: `usePathname()` による URL マッチングで視覚 + ARIA 両方の active 表示

## Architecture

```mermaid
graph TD
    subgraph "apps/web/components/sidebar.tsx"
        A[Navigation Config Data] --> B[Sidebar Component]
        B --> C[SidebarSection Component]
        B --> D[SidebarNavItem Component]
        B --> E[Standalone Items]
        B --> F[Logout Form]
    end

    subgraph "External Dependencies"
        G[next/link] --> D
        H[next/navigation usePathname] --> B
        I[@/lib/auth signOut] --> F
    end
```

### コンポーネント階層

```
<aside> (sidebar container)
  <header> (app title)
  <nav> (navigation landmark)
    <section aria-labelledby="uiux-heading"> (UIUX group)
      <h2 id="uiux-heading"> UIUX </h2>
      <SidebarNavItem /> × 4
    </section>
    <section aria-labelledby="press-heading"> (PRESS group)
      <h2 id="press-heading"> PRESS </h2>
      <SidebarNavItem /> × 2
    </section>
    <SidebarNavItem /> (設定 - standalone)
  </nav>
  <form> (logout button)
</aside>
```

### 設計判断

| 判断 | 選択肢 | 決定 | 理由 |
|------|--------|------|------|
| セクションのセマンティクス | `<div role="group">` vs `<section>` | `<section aria-labelledby>` | HTML5 セマンティクスに準拠、スクリーンリーダーがセクション境界を認識 |
| ヘッダー要素 | `<span>` vs `<h2>` | `<h2>` (視覚的に小さく表示) | 文書構造として正しく、aria-labelledby の参照先として適切 |
| アクティブ状態の取得 | Server-side headers vs Client hook | `usePathname()` (Client Component 分離) | App Router では Server Component からパスを取得する標準手法がないため、ナビリンク部分のみ Client Component 化 |
| コンポーネント分割 | 単一ファイル vs 複数ファイル | 単一ファイル内に抽出 | 小規模な変更であり、ファイル分割のオーバーヘッドが利点を上回らない |

## Components and Interfaces

### NavItem 型定義

```typescript
type NavItem = {
  href: string;
  label: string;
  icon: string;
};
```

### NavSection 型定義

```typescript
type NavSection = {
  id: string;       // HTML id prefix (e.g., "uiux", "press")
  heading: string;  // 表示テキスト (e.g., "UIUX", "PRESS")
  items: NavItem[];
};
```

### NavigationConfig

```typescript
const sections: NavSection[] = [
  {
    id: "uiux",
    heading: "UIUX",
    items: [
      { href: "/dashboard", label: "ダッシュボード", icon: "📊" },
      { href: "/sites", label: "対象サイト", icon: "🌐" },
      { href: "/changes", label: "変更履歴", icon: "🔄" },
      { href: "/advice", label: "AIアドバイス", icon: "💡" },
    ],
  },
  {
    id: "press",
    heading: "PRESS",
    items: [
      { href: "/press", label: "ソース管理", icon: "📰" },
      { href: "/press/articles", label: "記事履歴", icon: "📄" },
    ],
  },
];

const standaloneItems: NavItem[] = [
  { href: "/settings", label: "設定", icon: "⚙️" },
];
```

### SidebarNavItem コンポーネント

```typescript
// Client Component ("use client") - usePathname を使用するため
type SidebarNavItemProps = {
  item: NavItem;
  pathname: string;
};

function SidebarNavItem({ item, pathname }: SidebarNavItemProps) {
  const isActive = pathname === item.href;
  return (
    <Link
      href={item.href}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "flex items-center gap-3 px-3 py-2 text-sm rounded-lg transition-colors",
        isActive
          ? "bg-gray-100 text-gray-900 font-semibold"
          : "text-gray-700 hover:bg-gray-100"
      )}
    >
      <span>{item.icon}</span>
      <span>{item.label}</span>
    </Link>
  );
}
```

### SidebarNav コンポーネント（Client Component）

```typescript
"use client";

import { usePathname } from "next/navigation";

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <nav className="flex-1">
      {sections.map((section, idx) => (
        <section
          key={section.id}
          aria-labelledby={`${section.id}-heading`}
          className={idx > 0 ? "mt-6" : ""}
        >
          <h2
            id={`${section.id}-heading`}
            className="px-3 mb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider"
          >
            {section.heading}
          </h2>
          <div className="space-y-1">
            {section.items.map((item) => (
              <SidebarNavItem key={item.href} item={item} pathname={pathname} />
            ))}
          </div>
        </section>
      ))}

      {/* Standalone items */}
      <div className="mt-6 space-y-1">
        {standaloneItems.map((item) => (
          <SidebarNavItem key={item.href} item={item} pathname={pathname} />
        ))}
      </div>
    </nav>
  );
}
```

### Sidebar コンポーネント（Server Component - 既存構造維持）

```typescript
import { signOut } from "@/lib/auth";
import { SidebarNav } from "./sidebar-nav"; // or inline

export function Sidebar() {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen p-4 flex flex-col">
      <div className="mb-8">
        <h1 className="text-lg font-bold text-gray-900">Competitor Monitor</h1>
        <p className="text-xs text-gray-500">競合UIUX監視</p>
      </div>
      <SidebarNav />
      <form
        action={async () => {
          "use server";
          await signOut({ redirectTo: "/login" });
        }}
      >
        <button
          type="submit"
          className="w-full text-left px-3 py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          ログアウト
        </button>
      </form>
    </aside>
  );
}
```

## Data Models

本機能にデータベース変更はない。データモデルはフロントエンドの型定義のみ。

### 型定義一覧

```typescript
/** 個別ナビゲーション項目 */
export type NavItem = {
  href: string;   // 遷移先パス (e.g., "/dashboard")
  label: string;  // 表示ラベル (e.g., "ダッシュボード")
  icon: string;   // Emoji アイコン (e.g., "📊")
};

/** ナビゲーションセクション */
export type NavSection = {
  id: string;       // セクション識別子 (e.g., "uiux") - HTML id に使用
  heading: string;  // セクション見出し (e.g., "UIUX") - 表示テキスト
  items: NavItem[]; // セクション内のナビ項目（表示順）
};

/** サイドバー全体の設定 */
export type SidebarConfig = {
  sections: NavSection[];      // セクション一覧（表示順）
  standaloneItems: NavItem[];  // セクション外の独立項目
};
```

### スペーシング設計

| 区間 | Tailwind クラス | 実ピクセル |
|------|----------------|-----------|
| セクション内アイテム間 | `space-y-1` | 4px |
| セクション間 | `mt-6` | 24px |
| セクション末尾〜スタンドアロン | `mt-6` | 24px |
| セクションヘッダー〜最初のアイテム | `mb-1` | 4px |

Inter-section spacing (24px) ≥ 2× intra-section spacing (4px) の要件を満たす。

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Semantic grouping has matching ARIA label

*For any* section in the navigation configuration, the rendered semantic grouping element (`<section>`) must have an `aria-labelledby` attribute whose referenced element contains text matching the section's heading string.

**Validates: Requirements 1.5, 6.2**

### Property 2: Section headers render as uppercase text

*For any* section heading string in the navigation configuration, the displayed header text must equal the uppercase representation of that string.

**Validates: Requirements 2.1**

### Property 3: Section headers are not keyboard-focusable

*For any* section header element in the rendered sidebar, it must not be an interactive element (anchor, button) and must not have a positive tabindex, ensuring it is excluded from the keyboard tab sequence.

**Validates: Requirements 2.3**

### Property 4: Navigation item href matches configured path

*For any* navigation item in the configuration (across all sections and standalone items), the rendered anchor element's `href` attribute must equal the item's configured path.

**Validates: Requirements 5.1**

### Property 5: Navigation item structure contains icon and label

*For any* navigation item in the configuration, the rendered element must be a flex container with a 12px gap (gap-3), containing exactly two child spans: the first with the item's icon text and the second with the item's label text.

**Validates: Requirements 5.3**

### Property 6: Active page receives visual and ARIA indication

*For any* navigation item whose `href` matches the current pathname, the rendered anchor must have `aria-current="page"` set and must have active visual styling (bg-gray-100, font-semibold). For any item whose `href` does not match, `aria-current` must not be `"page"` and the active styling must not be applied.

**Validates: Requirements 5.4, 6.3**

## Error Handling

本機能は純粋な UI 構造変更であり、外部 API 呼び出しやデータフェッチを含まない。エラーハンドリングの考慮事項:

| シナリオ | 対応 |
|----------|------|
| ページ遷移失敗（ネットワークエラー） | Next.js の既存エラーバウンダリが処理。サイドバー自体は独立してレンダリングされるため影響なし |
| `usePathname()` が null/undefined を返す | pathname のデフォルト値を空文字列に設定し、どのアイテムもアクティブにならない（安全なフォールバック） |
| JavaScript 無効環境 | Server Component でサイドバー構造自体は SSR されるため表示される。アクティブ表示は動作しないが、ナビゲーション機能は維持 |

## Testing Strategy

### テスト構成

**Property-Based Tests（fast-check + vitest）**:
- 上記 6 つの Correctness Properties を property-based test として実装
- 各テスト最低 100 回のイテレーション
- ナビゲーション設定をランダム生成し、レンダリング結果を検証

**Example-Based Unit Tests（vitest + @testing-library/react）**:
- 静的な DOM 構造の検証（セクション順序、アイテム順序）
- 特定のスタイリングクラスの存在確認
- ログアウトボタンの位置確認

**テスト対象ファイル**: `apps/web/components/__tests__/sidebar.test.tsx`

### Property Test の実装方針

```typescript
import fc from "fast-check";
import { render } from "@testing-library/react";

// NavItem のアービトラリ
const navItemArb = fc.record({
  href: fc.stringMatching(/^\/[a-z][a-z-/]*$/),
  label: fc.string({ minLength: 1, maxLength: 20 }),
  icon: fc.constantFrom("📊", "🌐", "🔄", "💡", "📰", "📄", "⚙️"),
});

// NavSection のアービトラリ
const navSectionArb = fc.record({
  id: fc.stringMatching(/^[a-z]+$/),
  heading: fc.string({ minLength: 1, maxLength: 10 }),
  items: fc.array(navItemArb, { minLength: 1, maxLength: 5 }),
});
```

### テスト Tag フォーマット

各 property test に以下のコメントを付与:

```typescript
// Feature: menu-section-reorganization, Property 1: Semantic grouping has matching ARIA label
// Feature: menu-section-reorganization, Property 2: Section headers render as uppercase text
// ...
```

### PBT ライブラリ

プロジェクトには既に `fast-check` が devDependencies に含まれているため、追加インストール不要。
