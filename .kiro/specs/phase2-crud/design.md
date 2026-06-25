# Design Document: Phase 2 - Site & Page Management CRUD

## Overview

This design implements full CRUD functionality for managing monitored services (対象サイト) and their monitored pages (対象ページ) in the Competitor Monitor system. It builds on the existing Phase 1 read-only sites page by adding API routes for mutations, interactive UI components (modals, confirmation dialogs), client-side validation, and optimistic UI updates via Next.js revalidation.

The implementation follows the existing project conventions: Next.js 14 App Router, Server Components for data fetching, Client Components for interactivity, Prisma for database access, and Tailwind CSS for styling. All user-facing text is in Japanese.

## Architecture

```mermaid
graph TD
    subgraph "Browser"
        SP[SitesPage - Server Component]
        SCL[ServiceCardList - Client Component]
        SFM[ServiceFormModal - Client Component]
        PFM[PageFormModal - Client Component]
        DCD[DeleteConfirmDialog - Client Component]
        Toast[Toast Notifications - Client Component]
    end

    subgraph "Next.js API Layer"
        SA[/api/services]
        SAI[/api/services/[id]]
        SAP[/api/services/[id]/pages]
        PA[/api/pages/[id]]
    end

    subgraph "Data Layer"
        Prisma[Prisma Client]
        DB[(PostgreSQL)]
    end

    SP --> SCL
    SCL --> SFM
    SCL --> PFM
    SCL --> DCD
    SCL --> Toast

    SFM -->|POST/PUT| SA
    SFM -->|PUT| SAI
    DCD -->|DELETE| SAI
    DCD -->|DELETE| PA
    PFM -->|POST| SAP
    PFM -->|PUT| PA

    SA --> Prisma
    SAI --> Prisma
    SAP --> Prisma
    PA --> Prisma
    Prisma --> DB
```

### Data Flow Pattern

1. **Initial Load**: Server Component fetches data via Prisma, passes to Client Components as props.
2. **Mutations**: Client Components call API routes via `fetch()`. On success, call `router.refresh()` to trigger Server Component re-render.
3. **Validation**: Client-side validation runs before submission. Server-side validation runs in API routes as the authoritative check.
4. **Feedback**: Toast notifications for success/error. Field-level errors displayed inline in forms.

## Components and Interfaces

### API Route Handlers

#### `POST /api/services` — Create Service

**Request Body:**
```typescript
{
  name: string;        // required, unique identifier (e.g., "suumo")
  displayName: string; // required, display label (e.g., "SUUMO")
  baseUrl: string;     // required, valid URL format
  isActive?: boolean;  // optional, defaults to true
}
```

**Responses:**
| Status | Condition | Body |
|--------|-----------|------|
| 201 | Created successfully | `{ service: Service }` |
| 400 | Validation error | `{ error: string, fields?: Record<string, string> }` |
| 409 | Name already exists | `{ error: string, fields: { name: string } }` |

#### `GET /api/services` — List Services

**Query Parameters:** None

**Response (200):**
```typescript
{
  services: Array<Service & { _count: { pages: number } }>
}
```

Returns all services where `deletedAt` is null, ordered by `createdAt` ascending. Includes count of non-deleted pages.

#### `PUT /api/services/[id]` — Update Service

**Request Body:**
```typescript
{
  name?: string;
  displayName?: string;
  baseUrl?: string;
  isActive?: boolean;
}
```

**Responses:**
| Status | Condition | Body |
|--------|-----------|------|
| 200 | Updated successfully | `{ service: Service }` |
| 400 | Validation error | `{ error: string, fields?: Record<string, string> }` |
| 404 | Not found or soft-deleted | `{ error: string }` |
| 409 | Name conflicts with existing | `{ error: string, fields: { name: string } }` |

#### `DELETE /api/services/[id]` — Soft Delete Service

**Responses:**
| Status | Condition | Body |
|--------|-----------|------|
| 200 | Deleted successfully | `{ message: string }` |
| 404 | Not found or already deleted | `{ error: string }` |

**Side effect:** All associated MonitoredPages are also soft-deleted (deletedAt set).

#### `POST /api/services/[id]/pages` — Create Monitored Page

**Request Body:**
```typescript
{
  url: string;           // required, valid URL format
  pageType: "listing" | "detail";  // required
  device: "pc" | "sp";  // required
  isActive?: boolean;    // optional, defaults to true
}
```

**Responses:**
| Status | Condition | Body |
|--------|-----------|------|
| 201 | Created successfully | `{ page: MonitoredPage }` |
| 400 | Validation error | `{ error: string, fields?: Record<string, string> }` |
| 404 | Service not found or soft-deleted | `{ error: string }` |

#### `GET /api/services/[id]/pages` — List Pages for Service

**Response (200):**
```typescript
{
  pages: MonitoredPage[]
}
```

Returns all pages for the service where `deletedAt` is null, ordered by `createdAt` ascending.

#### `PUT /api/pages/[id]` — Update Page

**Request Body:**
```typescript
{
  url?: string;
  pageType?: "listing" | "detail";
  device?: "pc" | "sp";
  isActive?: boolean;
}
```

**Responses:**
| Status | Condition | Body |
|--------|-----------|------|
| 200 | Updated successfully | `{ page: MonitoredPage }` |
| 400 | Validation error | `{ error: string, fields?: Record<string, string> }` |
| 404 | Not found or soft-deleted | `{ error: string }` |

#### `DELETE /api/pages/[id]` — Soft Delete Page

**Responses:**
| Status | Condition | Body |
|--------|-----------|------|
| 200 | Deleted successfully | `{ message: string }` |
| 404 | Not found or already deleted | `{ error: string }` |

### UI Components

#### ServiceFormModal

```typescript
interface ServiceFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  service?: Service | null; // null = create mode, Service = edit mode
}
```

- Modal overlay with form fields: name, displayName, baseUrl, isActive toggle
- Client-side validation on blur and on submit
- Displays field-level errors in Japanese below each field
- Submit button text: "登録" (create) / "更新" (edit)

#### PageFormModal

```typescript
interface PageFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  serviceId: string;
  page?: MonitoredPage | null; // null = create mode
}
```

- Modal with fields: url, pageType (select), device (select), isActive toggle
- pageType options: "物件一覧" (listing) / "物件詳細" (detail)
- device options: "PC (1280px)" / "SP (375px)"

#### DeleteConfirmDialog

```typescript
interface DeleteConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  isLoading?: boolean;
}
```

- Reusable confirmation dialog with cancel/confirm buttons
- Confirm button styled as destructive (red)
- Displays during API call with loading state

#### ServiceCardList (Client Component)

Wraps the existing service cards with interactive capabilities:
- "サービス追加" button at the top
- Edit (✏️) and Delete (🗑️) buttons on each card
- Expandable section to show pages per service
- Manages modal open/close state

#### ServicePagesSection

```typescript
interface ServicePagesSectionProps {
  serviceId: string;
  pages: MonitoredPage[];
  onRefresh: () => void;
}
```

- Displays list of monitored pages for a service
- "ページ追加" button
- Edit/delete buttons per page row
- Shows pageType and device labels in Japanese
- Shows lastScannedAt in JST format

#### Toast / Notification

Simple toast notification component:
- Success (green): "サービスを登録しました", "ページを削除しました", etc.
- Error (red): "エラーが発生しました。もう一度お試しください。"
- Auto-dismiss after 3 seconds
- Positioned top-right

### Page Structure Update

The existing `app/sites/page.tsx` (Server Component) will be refactored:

```
app/sites/page.tsx          → Server Component (data fetching)
  └─ ServiceCardList        → Client Component (interactivity)
       ├─ ServiceFormModal   → Client Component (create/edit form)
       ├─ DeleteConfirmDialog → Client Component (delete confirm)
       └─ ServicePagesSection → Client Component (page list per service)
            ├─ PageFormModal  → Client Component (create/edit page form)
            └─ DeleteConfirmDialog → Client Component (page delete confirm)
```

## Data Models

The existing Prisma schema already defines the necessary models. No schema changes are required.

### Service

| Field | Type | Constraints |
|-------|------|-------------|
| id | String (cuid) | Primary key |
| name | String | Unique, required |
| displayName | String | Required |
| baseUrl | String | Required, valid URL |
| isActive | Boolean | Default: true |
| createdAt | DateTime | Auto-set |
| updatedAt | DateTime | Auto-updated |
| deletedAt | DateTime? | Null = active |

### MonitoredPage

| Field | Type | Constraints |
|-------|------|-------------|
| id | String (cuid) | Primary key |
| serviceId | String | FK to Service |
| url | String | Required, valid URL |
| pageType | String | "listing" or "detail" |
| device | String | "pc" or "sp", default "pc" |
| isActive | Boolean | Default: true |
| lastScannedAt | DateTime? | Set by scraper |
| lastStatus | Int? | HTTP status from last scan |
| createdAt | DateTime | Auto-set |
| updatedAt | DateTime | Auto-updated |
| deletedAt | DateTime? | Null = active |

### Validation Rules

```typescript
// Shared validation utilities: lib/validations.ts

interface ValidationResult {
  valid: boolean;
  fields: Record<string, string>; // field name → error message (Japanese)
}

// Service validation rules:
// - name: non-empty, alphanumeric + hyphens, max 50 chars
// - displayName: non-empty, max 100 chars
// - baseUrl: valid URL (starts with https:// or http://)

// MonitoredPage validation rules:
// - url: non-empty, valid URL format
// - pageType: must be "listing" or "detail"
// - device: must be "pc" or "sp"
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Service listing excludes soft-deleted records and maintains order

*For any* collection of Service records (some with deletedAt set, some without), the listing API SHALL return only records where deletedAt is null, and the returned list SHALL be ordered by createdAt ascending.

**Validates: Requirements 1.1**

### Property 2: Valid service creation round-trip

*For any* valid service input (non-empty name, non-empty displayName, valid URL baseUrl), creating a service via the API SHALL return a record whose name, displayName, and baseUrl match the input exactly.

**Validates: Requirements 2.1**

### Property 3: Validation rejects invalid inputs

*For any* service or page creation/update request containing an invalid URL (not matching URL format), an empty required field, or an enum value outside the allowed set ("listing"/"detail" for pageType, "pc"/"sp" for device), the API SHALL return HTTP 400.

**Validates: Requirements 2.2, 2.3, 2.4, 3.2, 3.3, 6.2, 6.3, 6.4, 6.5, 7.2**

### Property 4: Valid service update preserves changes

*For any* existing non-deleted Service and any valid partial update payload, updating the service via the API SHALL return the updated record with the changed fields reflecting the new values and unchanged fields retaining their original values.

**Validates: Requirements 3.1, 3.6**

### Property 5: Soft delete sets deletedAt timestamp

*For any* existing non-deleted Service or MonitoredPage, calling the delete API SHALL set the deletedAt field to a UTC timestamp within a reasonable tolerance of the current time, and subsequent listing calls SHALL exclude this record.

**Validates: Requirements 4.1, 8.1**

### Property 6: Cascade soft-delete propagates to child pages

*For any* Service with N associated non-deleted MonitoredPages (where N ≥ 0), soft-deleting the Service SHALL result in all N pages also having their deletedAt field set.

**Validates: Requirements 4.2**

### Property 7: Page listing excludes soft-deleted records and maintains order

*For any* collection of MonitoredPage records belonging to a Service (some with deletedAt set, some without), the page listing API SHALL return only records where deletedAt is null, ordered by createdAt ascending.

**Validates: Requirements 5.1**

### Property 8: Valid page creation round-trip

*For any* valid page input (non-empty valid URL, pageType in {"listing", "detail"}, device in {"pc", "sp"}) and an existing non-deleted Service, creating a page via the API SHALL return a record whose url, pageType, device, and serviceId match the input exactly.

**Validates: Requirements 6.1**

### Property 9: Valid page update preserves changes

*For any* existing non-deleted MonitoredPage and any valid partial update payload, updating the page via the API SHALL return the updated record with changed fields reflecting new values and unchanged fields retaining original values.

**Validates: Requirements 7.1, 7.4**

## Error Handling

### API Error Response Format

All API errors follow a consistent structure:

```typescript
interface ApiErrorResponse {
  error: string;                    // Human-readable message in Japanese
  fields?: Record<string, string>;  // Field-specific errors (for validation)
}
```

### Error Categories

| Category | HTTP Status | Example Message |
|----------|-------------|-----------------|
| Validation | 400 | "入力内容に誤りがあります" |
| Not Found | 404 | "対象のサービスが見つかりません" |
| Conflict | 409 | "このサービス名は既に使用されています" |
| Server Error | 500 | "サーバーエラーが発生しました" |

### Error Handling Strategy

**API Routes:**
- Wrap all handlers in try-catch
- Validate input before database operations
- Check for Prisma unique constraint violations → return 409
- Catch unknown errors → log and return generic 500

**Client Components:**
- Display field-level errors from `fields` object inline
- Display top-level `error` message as toast notification
- Handle network failures with a generic error toast
- Clear field errors when user modifies the field

### Field-Level Error Messages (Japanese)

| Field | Condition | Message |
|-------|-----------|---------|
| name | Empty | "サービス名を入力してください" |
| name | Duplicate | "このサービス名は既に使用されています" |
| displayName | Empty | "表示名を入力してください" |
| baseUrl | Empty | "URLを入力してください" |
| baseUrl | Invalid format | "有効なURL形式で入力してください" |
| url | Empty | "URLを入力してください" |
| url | Invalid format | "有効なURL形式で入力してください" |
| pageType | Invalid | "ページ種別を選択してください" |
| device | Invalid | "デバイスを選択してください" |

## Testing Strategy

### Unit Tests (Example-based)

Focus on:
- Validation function edge cases (empty strings, whitespace-only, malformed URLs)
- Unique constraint conflict handling
- Soft-delete cascade behavior
- 404 responses for deleted/non-existent records
- UI component rendering (empty states, error states)

### Property-Based Tests

Use a property-based testing library (e.g., `fast-check`) to validate universal properties:
- Minimum 100 iterations per property
- Each test tagged with: **Feature: phase2-crud, Property {N}: {title}**

Property tests focus on:
- Validation logic: generate random invalid inputs, verify rejection
- CRUD round-trips: generate random valid inputs, verify data integrity
- Listing filters: generate mixed deleted/non-deleted records, verify correct filtering
- Cascade behavior: generate services with random page counts, verify cascade

### Integration Tests

- API route handlers with real Prisma client against test database
- Verify HTTP status codes and response shapes
- Test unique constraint handling end-to-end

### Test File Organization

```
apps/web/
├── __tests__/
│   ├── api/
│   │   ├── services.test.ts          # Service API route tests
│   │   └── pages.test.ts             # Page API route tests
│   ├── lib/
│   │   └── validations.test.ts       # Validation logic tests
│   └── components/
│       ├── ServiceFormModal.test.tsx  # Form component tests
│       └── DeleteConfirmDialog.test.tsx
```

### Test Configuration

- Testing framework: Jest (or Vitest if preferred by team)
- Property-based testing: `fast-check`
- Component testing: `@testing-library/react`
- API testing: Direct handler invocation with mocked NextRequest/NextResponse
