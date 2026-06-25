# Implementation Plan: Phase 2 - Site & Page Management CRUD

## Overview

Implement full CRUD operations for Services and MonitoredPages, transforming the existing read-only sites page into an interactive management interface. The implementation starts with shared utilities, builds up API routes, then layers UI components on top.

## Tasks

- [ ] 1. Set up test framework and shared validation library
  - [ ] 1.1 Install test dependencies (vitest, fast-check, @testing-library/react)
    - Add `vitest`, `@vitejs/plugin-react`, `fast-check`, `@testing-library/react`, `@testing-library/jest-dom` to devDependencies
    - Create `vitest.config.ts` at `apps/web/` with React plugin and path aliases
    - Add `"test": "vitest --run"` script to `apps/web/package.json`
    - _Requirements: Testing Strategy_

  - [ ] 1.2 Create shared validation library `apps/web/lib/validations.ts`
    - Implement `validateServiceInput(data)` returning `ValidationResult` with field-level errors in Japanese
    - Implement `validatePageInput(data)` returning `ValidationResult` with field-level errors in Japanese
    - Implement `isValidUrl(url: string)` helper (must start with http:// or https://)
    - Validation rules: name (non-empty, alphanumeric + hyphens, max 50), displayName (non-empty, max 100), baseUrl (valid URL), url (valid URL), pageType ("listing" | "detail"), device ("pc" | "sp")
    - Export `ValidationResult` interface: `{ valid: boolean; fields: Record<string, string> }`
    - _Requirements: 2.2, 2.3, 2.4, 3.2, 3.3, 6.2, 6.3, 6.4, 6.5, 7.2, 9.1_

  - [ ]* 1.3 Write property tests for validation library
    - **Property 3: Validation rejects invalid inputs**
    - *For any* input with invalid URL, empty required field, or invalid enum value, validation SHALL return `valid: false`
    - Generate random invalid URLs, empty/whitespace strings, out-of-range enum values
    - Generate random valid inputs, verify validation returns `valid: true`
    - Use `fast-check` with 100+ iterations
    - **Validates: Requirements 2.2, 2.3, 2.4, 3.2, 3.3, 6.2, 6.3, 6.4, 6.5, 7.2**

- [ ] 2. Implement Service API routes
  - [ ] 2.1 Implement `GET /api/services` route
    - Create `apps/web/app/api/services/route.ts`
    - Query services where `deletedAt` is null, ordered by `createdAt` asc
    - Include `_count` of non-deleted pages via Prisma `include`
    - Return `{ services: [...] }` with HTTP 200
    - _Requirements: 1.1_

  - [ ] 2.2 Implement `POST /api/services` route
    - Add POST handler in `apps/web/app/api/services/route.ts`
    - Parse JSON body, run `validateServiceInput()`
    - On validation failure: return 400 with `{ error, fields }`
    - Check unique constraint on `name`: if conflict, return 409
    - On success: create record via Prisma, return 201 with `{ service }`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 2.3 Implement `PUT /api/services/[id]` route
    - Create `apps/web/app/api/services/[id]/route.ts`
    - Find service by id where `deletedAt` is null; if not found return 404
    - Validate non-empty provided fields, validate URL format if baseUrl provided
    - Check name uniqueness (excluding current record) if name is being changed
    - Update record via Prisma, return 200 with `{ service }`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 2.4 Implement `DELETE /api/services/[id]` route
    - Add DELETE handler in `apps/web/app/api/services/[id]/route.ts`
    - Find service by id where `deletedAt` is null; if not found return 404
    - Use Prisma transaction: set service `deletedAt` + set all associated pages' `deletedAt`
    - Return 200 with `{ message: "サービスを削除しました" }`
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 2.5 Write property tests for Service API logic
    - **Property 1: Service listing excludes soft-deleted records and maintains order**
    - **Property 2: Valid service creation round-trip**
    - **Property 5: Soft delete sets deletedAt timestamp**
    - **Property 6: Cascade soft-delete propagates to child pages**
    - Test against validation logic and mock Prisma responses
    - **Validates: Requirements 1.1, 2.1, 4.1, 4.2**

- [ ] 3. Implement Monitored Page API routes
  - [ ] 3.1 Implement `GET /api/services/[id]/pages` route
    - Create `apps/web/app/api/services/[id]/pages/route.ts`
    - Find service by id where `deletedAt` is null; if not found return 404
    - Query pages for that service where `deletedAt` is null, ordered by `createdAt` asc
    - Return `{ pages: [...] }` with HTTP 200
    - _Requirements: 5.1_

  - [ ] 3.2 Implement `POST /api/services/[id]/pages` route
    - Add POST handler in `apps/web/app/api/services/[id]/pages/route.ts`
    - Verify service exists and is not soft-deleted; return 404 if not
    - Parse body, run `validatePageInput()`
    - On validation failure: return 400 with `{ error, fields }`
    - On success: create record via Prisma with `serviceId`, return 201 with `{ page }`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ] 3.3 Implement `PUT /api/pages/[id]` route
    - Create `apps/web/app/api/pages/[id]/route.ts`
    - Find page by id where `deletedAt` is null; if not found return 404
    - Validate provided fields via `validatePageInput()` (partial mode)
    - Update record via Prisma, return 200 with `{ page }`
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ] 3.4 Implement `DELETE /api/pages/[id]` route
    - Add DELETE handler in `apps/web/app/api/pages/[id]/route.ts`
    - Find page by id where `deletedAt` is null; if not found return 404
    - Set `deletedAt` to current UTC timestamp
    - Return 200 with `{ message: "ページを削除しました" }`
    - _Requirements: 8.1, 8.2_

  - [ ]* 3.5 Write property tests for Page API logic
    - **Property 7: Page listing excludes soft-deleted records and maintains order**
    - **Property 8: Valid page creation round-trip**
    - **Property 9: Valid page update preserves changes**
    - **Validates: Requirements 5.1, 6.1, 7.1, 7.4**

- [ ] 4. Checkpoint - Ensure all API tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement shared UI components
  - [ ] 5.1 Create Toast notification component
    - Create `apps/web/components/toast.tsx` (Client Component)
    - Implement toast context provider with `useToast()` hook
    - Support success (green) and error (red) variants
    - Auto-dismiss after 3 seconds, positioned top-right
    - All messages in Japanese
    - _Requirements: 9.3, 9.4_

  - [ ] 5.2 Create DeleteConfirmDialog component
    - Create `apps/web/components/delete-confirm-dialog.tsx` (Client Component)
    - Accept `title`, `message`, `onConfirm`, `onClose`, `isLoading` props
    - Modal overlay with "キャンセル" and "削除" buttons
    - "削除" button styled red, shows loading spinner during API call
    - _Requirements: 4.4, 8.3, 10.4_

  - [ ] 5.3 Create ServiceFormModal component
    - Create `apps/web/components/service-form-modal.tsx` (Client Component)
    - Accept `service` prop (null = create mode, Service object = edit mode)
    - Form fields: name (text), displayName (text), baseUrl (text), isActive (toggle)
    - Client-side validation on submit using `validateServiceInput()`
    - Display field-level errors in Japanese below each field
    - Clear error when user modifies the field
    - On submit: call POST or PUT API, trigger `onSuccess` callback
    - Submit button: "登録" (create) / "更新" (edit)
    - _Requirements: 2.1, 2.6, 3.1, 9.1, 9.2_

  - [ ] 5.4 Create PageFormModal component
    - Create `apps/web/components/page-form-modal.tsx` (Client Component)
    - Accept `serviceId` and optional `page` prop (null = create, object = edit)
    - Form fields: url (text), pageType (select: "物件一覧"/"物件詳細"), device (select: "PC (1280px)"/"SP (375px)"), isActive (toggle)
    - Client-side validation using `validatePageInput()`
    - Display field-level errors in Japanese
    - On submit: call POST or PUT API, trigger `onSuccess` callback
    - _Requirements: 6.1, 7.1, 9.1, 9.2_

- [ ] 6. Implement feature page components and wire together
  - [ ] 6.1 Create ServicePagesSection component
    - Create `apps/web/components/service-pages-section.tsx` (Client Component)
    - Display list of monitored pages for a service in a table/list format
    - Show url, pageType label (物件一覧/物件詳細), device label (PC/SP), isActive badge, lastScannedAt in JST
    - "ページ追加" button opens PageFormModal in create mode
    - Edit/delete buttons per row
    - Empty state: "監視対象のページがありません"
    - _Requirements: 5.2, 5.3, 10.3_

  - [ ] 6.2 Create ServiceCardList client component
    - Create `apps/web/components/service-card-list.tsx` (Client Component)
    - Wrap service cards with interactive capabilities
    - "サービス追加" button at the top opens ServiceFormModal in create mode
    - Edit (pencil icon) and Delete (trash icon) buttons on each card
    - Clicking a card expands/navigates to show ServicePagesSection
    - Manage modal and dialog state
    - On mutation success: call `router.refresh()` to re-fetch server data
    - Integrate Toast for success/error feedback
    - _Requirements: 2.6, 10.1, 10.2_

  - [ ] 6.3 Refactor `apps/web/app/sites/page.tsx`
    - Keep as Server Component for initial data fetch
    - Pass fetched services (with pages and _count) to ServiceCardList as props
    - Wrap page with ToastProvider
    - Remove inline card rendering, delegate to ServiceCardList
    - _Requirements: 1.2, 1.3_

- [ ] 7. Final checkpoint - Ensure all tests pass and UI works
  - Ensure all tests pass, ask the user if questions arise.
  - Verify end-to-end flow: create service → add pages → edit → delete with cascade

## Task Dependency Graph

```json
{
  "waves": [
    ["1.1", "1.2"],
    ["1.3", "2.1", "2.2", "2.3", "2.4"],
    ["2.5", "3.1", "3.2", "3.3", "3.4"],
    ["3.5", "4"],
    ["5.1", "5.2", "5.3", "5.4"],
    ["6.1", "6.2", "6.3"],
    ["7"]
  ]
}
```

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using `fast-check`
- All user-facing text is in Japanese per project conventions
- The existing Prisma schema requires no changes
- `router.refresh()` is used instead of client-side state management for data freshness
