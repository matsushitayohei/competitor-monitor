# Implementation Plan: menu-section-reorganization

## Overview

サイドバーナビゲーションを現在のフラットリスト構造から、ドメイン別セクション（「UIUX」「PRESS」）に再編成する。変更は `apps/web/components/sidebar.tsx` を中心に、Client Component 分離とセマンティック HTML 構造の導入を行う。既存の Server Component アーキテクチャ、Next.js App Router、Tailwind CSS を維持しつつ、アクセシビリティ対応（aria-labelledby、aria-current）を追加する。

## Tasks

- [x] 1. ナビゲーション型定義とデータ構造の作成
  - [x] 1.1 NavItem, NavSection 型定義とナビゲーション設定データを作成する
    - `apps/web/components/sidebar.tsx` に `NavItem` 型と `NavSection` 型を定義
    - `sections` 配列（UIUX: ダッシュボード、対象サイト、変更履歴、AIアドバイス / PRESS: ソース管理、記事履歴）を定義
    - `standaloneItems` 配列（設定）を定義
    - 既存の `navItems` 配列を削除し、新しいデータ構造に置き換え
    - _Requirements: 1.1, 1.2, 1.3, 1.6_

- [x] 2. Client Component（SidebarNav）の実装
  - [x] 2.1 SidebarNavItem コンポーネントを実装する
    - `apps/web/components/sidebar.tsx` 内に `SidebarNavItem` コンポーネントを作成
    - `usePathname()` からの pathname と item props を受け取る設計
    - アクティブ状態の判定（`pathname === item.href`）
    - `aria-current="page"` の条件付き設定
    - アクティブ時のスタイル（bg-gray-100, font-semibold）と非アクティブ時のスタイル（text-gray-700, hover:bg-gray-100）
    - flex + gap-3 レイアウトで icon span と label span を配置
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.3_

  - [x] 2.2 SidebarNav Client Component を実装する
    - `apps/web/components/sidebar.tsx` 内に `"use client"` ディレクティブ付きの `SidebarNav` コンポーネントを作成
    - `usePathname()` で現在のパスを取得
    - `sections` を `<section aria-labelledby>` でイテレーションし、各セクション内に `<h2>` ヘッダーと `SidebarNavItem` リストを配置
    - セクション間に `mt-6`（24px）のスペーシングを設定
    - `standaloneItems` をセクション外に `mt-6` で配置
    - セクションヘッダーのスタイリング: `text-xs font-semibold text-gray-400 uppercase tracking-wider`
    - _Requirements: 1.1, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 4.1, 4.2, 6.1, 6.2, 6.4_

- [x] 3. Sidebar Server Component のリファクタリング
  - [x] 3.1 既存の Sidebar コンポーネントを SidebarNav を利用する形にリファクタリングする
    - `apps/web/components/sidebar.tsx` の `Sidebar` コンポーネントを更新
    - 既存の `<nav>` 内の navItems マッピングを削除し、`<SidebarNav />` に置き換え
    - `<aside>` コンテナ、`<header>`（アプリタイトル）、`<form>`（ログアウト）の既存構造を維持
    - `signOut` server action はそのまま維持
    - 不要になった `navItems` 配列と `Link` の直接インポート（Sidebar本体から）を整理
    - _Requirements: 5.1, 5.5, 6.1_

- [x] 4. チェックポイント - ビルドとリンティングの確認
  - Ensure all tests pass, ask the user if questions arise.
  - `npm run build` が成功すること
  - `npm run lint` がエラーなしで通ること

- [ ] 5. テストの実装
  - [ ]* 5.1 Property 1 のテストを実装する: セマンティックグルーピングに対応する ARIA ラベルがあること
    - **Property 1: Semantic grouping has matching ARIA label**
    - **Validates: Requirements 1.5, 6.2**
    - `apps/web/components/__tests__/sidebar.test.tsx` に fast-check を使用した property test を実装
    - ランダム生成した NavSection 設定に対して、レンダリング結果の `<section>` が `aria-labelledby` を持ち、参照先の要素にセクション heading テキストが含まれることを検証

  - [ ]* 5.2 Property 2 のテストを実装する: セクションヘッダーが大文字テキストで表示されること
    - **Property 2: Section headers render as uppercase text**
    - **Validates: Requirements 2.1**
    - ランダム生成した heading 文字列に対して、表示されたヘッダーテキストが uppercase 表現と一致することを検証

  - [ ]* 5.3 Property 3 のテストを実装する: セクションヘッダーがキーボードフォーカス不可であること
    - **Property 3: Section headers are not keyboard-focusable**
    - **Validates: Requirements 2.3**
    - レンダリングされたセクションヘッダー要素が anchor/button でなく、正の tabindex を持たないことを検証

  - [ ]* 5.4 Property 4 のテストを実装する: ナビゲーション項目の href が設定パスと一致すること
    - **Property 4: Navigation item href matches configured path**
    - **Validates: Requirements 5.1**
    - ランダム生成した NavItem 設定に対して、レンダリングされた anchor の href が設定値と一致することを検証

  - [ ]* 5.5 Property 5 のテストを実装する: ナビゲーション項目がアイコンとラベルを含むこと
    - **Property 5: Navigation item structure contains icon and label**
    - **Validates: Requirements 5.3**
    - ランダム生成した NavItem 設定に対して、レンダリング結果が gap-3 の flex コンテナで、icon span と label span を含むことを検証

  - [ ]* 5.6 Property 6 のテストを実装する: アクティブページが視覚・ARIA 両方の表示を受けること
    - **Property 6: Active page receives visual and ARIA indication**
    - **Validates: Requirements 5.4, 6.3**
    - ランダム生成した pathname に対して、一致する項目に aria-current="page" とアクティブスタイルが適用され、非一致項目には適用されないことを検証

  - [ ]* 5.7 Example-based ユニットテストを実装する
    - 静的な DOM 構造の検証（UIUX セクションが PRESS セクションの上に表示される順序確認）
    - 設定項目がセクション外に配置されていることの確認
    - ログアウトボタンが最下部に存在することの確認
    - セクション間のスペーシング（mt-6）が適用されていることの確認
    - _Requirements: 1.2, 1.3, 1.4, 3.1, 3.2, 3.3_

- [x] 6. 最終チェックポイント - 全テスト通過確認
  - Ensure all tests pass, ask the user if questions arise.
  - `npm run test` が全テスト通過すること
  - `npm run build` が成功すること

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from design.md
- Unit tests validate specific examples and edge cases
- 変更は `apps/web/components/sidebar.tsx` 単一ファイル内で完結する（設計方針に従い複数ファイル分割しない）
- 既存の fast-check, vitest, @testing-library/react が devDependencies に含まれているため追加インストール不要
- `usePathname()` を使用するため、テスト時は `next/navigation` のモックが必要

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2"] },
    { "id": 3, "tasks": ["3.1"] },
    { "id": 4, "tasks": ["5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7"] }
  ]
}
```
