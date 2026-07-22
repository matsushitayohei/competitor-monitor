# Requirements Document

## Introduction

管理パネルのサイドバーナビゲーションを、現在のフラットなリスト構造から「UIUX」と「PRESS」の2つの論理セクションに再編成する機能。これにより、UI/UX競合モニタリングとプレスリリースモニタリングという2つの異なるドメインの機能が視覚的に分離され、ユーザーの操作効率とナビゲーション理解度が向上する。

## Glossary

- **Sidebar**: 管理パネル左側に固定表示されるナビゲーションコンポーネント（`apps/web/components/sidebar.tsx`）
- **Section_Header**: サイドバー内のナビゲーション項目をグループ化するためのラベル要素
- **Navigation_Item**: サイドバー内の個別のリンク要素（アイコン、ラベル、遷移先URLで構成）
- **UIUX_Section**: UI/UX競合モニタリングに関連するナビゲーション項目のグループ
- **PRESS_Section**: プレスリリースモニタリングに関連するナビゲーション項目のグループ
- **Standalone_Item**: セクションに属さない独立したナビゲーション項目

## Requirements

### Requirement 1: サイドバーのセクション分割

**User Story:** As a 管理者, I want サイドバーのナビゲーション項目がドメイン別にグループ化されている, so that 目的の機能に素早くアクセスできる。

#### Acceptance Criteria

1. THE Sidebar SHALL display navigation items grouped into sections, where each section has a visible text heading ("UIUX", "PRESS") rendered above its navigation items
2. THE UIUX_Section SHALL contain the following Navigation_Items in this exact order: ダッシュボード（/dashboard）、対象サイト（/sites）、変更履歴（/changes）、AIアドバイス（/advice）
3. THE PRESS_Section SHALL contain the following Navigation_Items in this exact order: ソース管理（/press）、記事履歴（/press/articles）
4. THE Sidebar SHALL display the UIUX_Section above the PRESS_Section, with each section visually separated by spacing of at least 16px between the last item of the preceding section and the heading of the following section
5. THE Sidebar SHALL render each section as a semantic grouping with an accessible label matching the section heading text, so that assistive technologies can identify each navigation group
6. THE Sidebar SHALL display navigation items that do not belong to either the UIUX or PRESS section (such as 設定) outside of these grouped sections

### Requirement 2: セクションヘッダーの表示

**User Story:** As a 管理者, I want 各セクションにラベルが表示されている, so that どのグループにどの機能が属しているか一目で分かる。

#### Acceptance Criteria

1. THE Section_Header SHALL display the section name in uppercase text, where the defined sections and their grouped Navigation_Items are: "UIUX" (ダッシュボード, 対象サイト, 変更履歴, AIアドバイス) and "PRESS" (ソース管理, 記事履歴)
2. THE Section_Header SHALL be visually distinct from Navigation_Items by using a font size at least 2px smaller than Navigation_Item text and a text color with lower contrast against the background than Navigation_Item text
3. THE Section_Header SHALL not be clickable or focusable as a link, and SHALL NOT receive focus via keyboard Tab navigation
4. THE Section_Header SHALL be positioned immediately above the first Navigation_Item of its corresponding group, with no other interactive element between the header and the group
5. THE Section_Header SHALL use a semantic grouping element (such as a heading or group role) so that assistive technologies can identify the navigation section structure

### Requirement 3: 設定項目の独立配置

**User Story:** As a 管理者, I want 設定項目がセクションとは独立して配置されている, so that ドメインに関係なく設定にアクセスできる。

#### Acceptance Criteria

1. THE Sidebar SHALL display the 設定（/settings）Navigation_Item as a Standalone_Item below all sections and above the logout button
2. THE Standalone_Item SHALL be visually separated from the PRESS_Section by a vertical spacing of at least 16px（md以上のスペーシング）
3. THE Standalone_Item SHALL NOT be contained within any section's semantic grouping element（UIUX_Section or PRESS_Section）

### Requirement 4: セクション間の視覚的区切り

**User Story:** As a 管理者, I want セクション間に視覚的な区切りがある, so that グループの境界を直感的に認識できる。

#### Acceptance Criteria

1. THE Sidebar SHALL render vertical spacing of 16px or more between the UIUX_Section and the PRESS_Section, where this inter-section spacing is at least double the intra-section item spacing.
2. THE Sidebar SHALL render vertical spacing of 16px or more between the PRESS_Section and the Standalone_Item, where this inter-section spacing is at least double the intra-section item spacing.

### Requirement 5: 既存ナビゲーション機能の維持

**User Story:** As a 管理者, I want 再編成後もすべてのナビゲーション項目が正常に動作する, so that 既存の作業フローが中断されない。

#### Acceptance Criteria

1. WHEN a Navigation_Item is clicked, THE Sidebar SHALL navigate to the corresponding URL path, where the Navigation_Items and their paths are: ダッシュボード→/dashboard, 対象サイト→/sites, 変更履歴→/changes, AIアドバイス→/advice, ソース管理→/press, 記事履歴→/press/articles, 設定→/settings
2. THE Sidebar SHALL display a background color change on hover (hover:bg-gray-100) for all Navigation_Items, with a transition duration of 150ms or less
3. THE Sidebar SHALL display each Navigation_Item as a horizontal row containing an icon (emoji) on the left and a text label on the right, with a gap of 12px between them
4. WHEN the current browser URL matches a Navigation_Item's href, THE Sidebar SHALL visually distinguish that Navigation_Item from the others to indicate the active page
5. IF a Navigation_Item's target page fails to load, THEN THE Sidebar SHALL remain in its current state without losing the navigation list or its interactivity

### Requirement 6: アクセシビリティ対応

**User Story:** As a 管理者, I want サイドバーのセクション構造がスクリーンリーダーに正しく伝わる, so that アクセシビリティが確保される。

#### Acceptance Criteria

1. THE Sidebar SHALL use a `nav` landmark element to wrap the navigation link group, and a semantically distinct region（`aside`, `section`, or element with explicit `role`）to wrap the overall sidebar container
2. THE Section_Header SHALL be associated with its containing landmark or region using `aria-labelledby`（referencing the header element's `id`）or `aria-label`（providing an equivalent text string directly on the region element）
3. WHEN a navigation link corresponds to the currently active page, THE Sidebar SHALL convey the active state to assistive technology by applying `aria-current="page"` to that link
4. THE Sidebar SHALL support keyboard navigation such that all interactive elements（links, buttons）are reachable via Tab key in a logical top-to-bottom order matching the visual layout
