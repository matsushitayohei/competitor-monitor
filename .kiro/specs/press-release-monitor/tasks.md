# Implementation Plan: Press Release Monitor

## Overview

競合不動産ポータル（SUUMO, athome, カナリー）のプレスリリースを日次自動取得し、ルールベース分類・要約・Slack通知を行うパイプラインを実装する。既存のUI/UX変更検知と並行して動作する独立したデータパイプラインとして、DB schema → Python scraper/analyzer → Next.js API/UI → MCP tools の順に段階的に構築する。

## Tasks

- [x] 1. Database schema and validation utilities
  - [x] 1.1 Add PressSource and PressArticle models to Prisma schema
    - Add `PressSource` model with fields: id, name (unique), url, isActive, createdAt, updatedAt, deletedAt
    - Add `PressArticle` model with fields: id, sourceId (FK), title (VarChar 512), articleUrl (VarChar 2048), publishedAt, bodyText (Text), classification, relevanceCategory, summary (VarChar 5000), needsManualReview, scrapedAt, createdAt, updatedAt, deletedAt
    - Add `@@map("press_source")` and `@@map("press_article")` for snake_case table names
    - Add `@@unique([sourceId, articleUrl])` constraint on PressArticle
    - Add indexes on publishedAt, sourceId, classification, relevanceCategory
    - Add cascade delete relation from PressSource to PressArticle
    - Run `prisma db push` to apply schema changes
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 1.2 Implement press source validation utilities
    - Create `apps/web/lib/press-validations.ts`
    - Implement `validatePressSourceInput` function: name must match `/^[a-zA-Z0-9-]{1,50}$/`, url must be valid http/https URL
    - Implement `validatePressSourceName(name: string): boolean`
    - Implement `validatePressSourceUrl(url: string): boolean`
    - Support partial validation for edit operations (same pattern as existing `validations.ts`)
    - Return field-level error messages in Japanese
    - _Requirements: 1.2, 1.3, 1.6_

  - [ ]* 1.3 Write property tests for press source validation (Property 1)
    - **Property 1: Source name and URL validation**
    - **Validates: Requirements 1.2**
    - Create `apps/web/__tests__/properties/press-source-validation.prop.test.ts`
    - Use fast-check to generate arbitrary strings and verify acceptance matches regex `/^[a-zA-Z0-9-]{1,50}$/`
    - Generate arbitrary URL strings and verify acceptance matches valid http/https URL pattern

  - [x] 1.4 Implement title truncation utility
    - Create `truncateTitle(title: string, maxLength?: number): string` in `apps/web/lib/press-utils.ts`
    - Return original title if ≤80 chars, otherwise truncate to 80 chars + "..."
    - _Requirements: 7.3_

  - [ ]* 1.5 Write property tests for title truncation (Property 17)
    - **Property 17: Title truncation**
    - **Validates: Requirements 7.3**
    - Create `apps/web/__tests__/properties/press-article-display.prop.test.ts`
    - Verify output ≤83 chars, original returned if ≤80 chars

- [x] 2. Press release scraper (Python)
  - [x] 2.1 Create press database access module
    - Create `packages/scraper/src/press_db.py`
    - Implement `get_active_press_sources()`: query press_source where isActive=true AND deletedAt IS NULL
    - Implement `article_exists(source_id, article_url)`: duplicate URL check per source
    - Implement `save_press_article(data)`: insert new press_article record with status=pending
    - Implement `update_article_classification(article_id, classification, category, needs_manual_review)`
    - Implement `update_article_summary(article_id, summary)`
    - Follow existing `db.py` patterns (psycopg2 connection pool, cuid2 IDs, UTC timestamps)
    - _Requirements: 2.3, 6.4, 6.6_

  - [ ]* 2.2 Write property tests for active source filtering (Property 2)
    - **Property 2: Active source filtering**
    - **Validates: Requirements 1.4, 2.4**
    - Create `apps/web/__tests__/properties/press-source-filter.prop.test.ts`
    - Generate source records with varying isActive/deletedAt, verify only active non-deleted sources returned

  - [x] 2.3 Implement site-specific press release parsers
    - Create `packages/scraper/src/press_parsers.py`
    - Implement base class `PressSourceParser` with methods: `parse_article_list(html) -> list[dict]`, `parse_article_body(html) -> str`
    - Implement `SuumoPressParser`: parse SUUMO press release page structure
    - Implement `AthomePressParser`: parse athome press release page structure
    - Implement `CanaryPressParser`: parse カナリー press release page structure
    - Each parser extracts: title (≤512 chars), URL (≤2048 chars), publication date, body text (≤100,000 chars)
    - Implement `get_parser_for_source(source_name: str) -> PressSourceParser` factory function
    - _Requirements: 2.2_

  - [x] 2.4 Implement press release scraper main module
    - Create `packages/scraper/src/press_scraper.py`
    - Implement `scrape_press_source(source)`: fetch page with Playwright, extract articles using parser, check duplicates, save new articles
    - Implement `fetch_article_body(url)`: navigate to article page, extract body text
    - Add 30s timeout per HTTP request (Requirements 2.5)
    - Add 2s inter-request delay between requests
    - Handle errors per source independently (one failure doesn't block others)
    - Log successful zero-new-article scrapes without treating as error
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 2.5 Write property tests for article deduplication (Property 5)
    - **Property 5: New article deduplication**
    - **Validates: Requirements 2.3**
    - Create `apps/web/__tests__/properties/press-article-dedup.prop.test.ts`
    - Generate existing URL sets and candidate URLs, verify only truly new URLs are saved

- [x] 3. Checkpoint - Ensure scraper pipeline compiles and basic tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Press classifier (Python)
  - [x] 4.1 Implement press article classifier
    - Create `packages/analyzer/src/press_classifier.py`
    - Define `IRRELEVANT_PATTERNS`: regex patterns for 人事, IR, イベント, CSR, オフィス移転
    - Define `RELEVANT_PATTERNS`: dict mapping categories to keyword/regex patterns for service_feature, market_data, ux_improvement, pricing
    - Implement `classify_press_article(title, body) -> ClassificationResult`
    - Classification logic: check irrelevant first → score relevant categories → assign category or flag manual review
    - Set `needs_manual_review=True` when confidence below threshold
    - Handle empty content as `classification_failed`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 4.2 Write property tests for classification correctness (Property 7, Property 8)
    - **Property 7: Classification correctness**
    - **Property 8: Relevant article category assignment and manual review flag**
    - **Validates: Requirements 3.2, 3.3, 3.5, 3.6**
    - Create `packages/analyzer/tests/prop_test_press_classifier.py`
    - Use hypothesis to generate article titles/bodies with known keyword patterns
    - Verify irrelevant patterns yield is_relevant=false
    - Verify relevant patterns yield exactly one category from the allowed list
    - Verify low-confidence results set needs_manual_review=true

- [x] 5. Press summarizer (Python)
  - [x] 5.1 Implement press article summarizer
    - Create `packages/analyzer/src/press_summarizer.py`
    - Implement `summarize_press_article(body, category) -> str`
    - Implement `_extract_key_sentences(body, category) -> list[str]`: extract sentences containing category-related keywords
    - Implement `_truncate_at_sentence_boundary(text, max_length=200) -> str`: truncate at 。！？ boundaries
    - Summary must be 50-200 characters in Japanese
    - Prioritize first sentence + category-related keyword sentences
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 5.2 Write property tests for summary length and truncation (Property 9, Property 10)
    - **Property 9: Summary length constraint**
    - **Property 10: Summary truncation at sentence boundary**
    - **Validates: Requirements 4.2, 4.6**
    - Create `packages/analyzer/tests/prop_test_press_summarizer.py`
    - Use hypothesis to generate body texts of varying length
    - Verify summary length is always 50-200 chars
    - Verify truncated text ends at sentence boundary (。！？)

- [x] 6. Press notifier (Python)
  - [x] 6.1 Implement Slack press release notifier
    - Create `packages/analyzer/src/press_notifier.py`
    - Implement `notify_press_article(article) -> bool`: POST to Slack webhook
    - Implement `format_slack_message(article) -> dict`: format with Block Kit (title as clickable link, source name, date, category, summary)
    - Implement retry logic: on failure, wait 30s, retry once
    - If retry fails, log error and skip (don't block other notifications)
    - If SLACK_WEBHOOK_URL not configured, log config error and skip all
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [ ]* 6.2 Write property tests for notification format completeness (Property 11)
    - **Property 11: Notification format completeness**
    - **Validates: Requirements 5.2, 5.3**
    - Create `apps/web/__tests__/properties/press-notifier-format.prop.test.ts`
    - Generate PressArticle objects with all fields populated
    - Verify formatted message contains title as Slack link, source name, date, category, and summary

- [x] 7. Press pipeline orchestrator
  - [x] 7.1 Create press release pipeline main entry point
    - Create `packages/scraper/src/press_main.py`
    - Implement `main()`: fetch active sources → for each source: scrape → classify → summarize → notify
    - Ensure each source is processed independently (one failure doesn't stop others)
    - Add error logging with source name and failure reason per Requirements 2.5
    - Send failure notification to Slack for source access failures per Requirements 2.6
    - Print summary at end (total sources, new articles, errors)
    - _Requirements: 2.1, 2.5, 2.6, 2.7_

- [x] 8. Checkpoint - Ensure Python pipeline compiles and tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. API Routes for press sources and articles
  - [x] 9.1 Implement press-sources API routes
    - Create `apps/web/app/api/press-sources/route.ts` with GET (list all active sources sorted by createdAt ASC) and POST (create new source with validation)
    - Create `apps/web/app/api/press-sources/[id]/route.ts` with PUT (update source) and DELETE (soft delete via deletedAt)
    - Apply auth middleware (existing pattern from other API routes)
    - Return 400 for validation errors with field-level messages
    - Return 409 for duplicate URL registration
    - Return 404 for non-existent or deleted sources
    - Exclude soft-deleted entries from GET responses
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 9.2 Implement press-articles API route
    - Create `apps/web/app/api/press-articles/route.ts` with GET
    - Support query params: sourceId, classification, relevanceCategory, page (default 1)
    - Return paginated results (20 per page) sorted by publishedAt DESC
    - Apply AND logic for all filters
    - Include total count and page metadata in response
    - Exclude soft-deleted articles
    - _Requirements: 7.1, 7.2, 7.5_

  - [ ]* 9.3 Write property tests for article list sorting and filtering (Property 15, Property 16, Property 18)
    - **Property 15: Article list sorted by publication date descending**
    - **Property 16: AND-filter correctness**
    - **Property 18: Pagination correctness**
    - **Validates: Requirements 7.1, 7.2, 7.5**
    - Create `apps/web/__tests__/properties/press-article-list.prop.test.ts`
    - Generate article sets with varying dates, verify descending sort order
    - Generate filter combinations, verify all returned articles satisfy all conditions
    - Generate article counts, verify pagination returns ≤20 per page with correct total pages

- [x] 10. Admin dashboard pages
  - [x] 10.1 Implement press source management page
    - Create `apps/web/app/press/page.tsx` as Server Component
    - Display list of registered press sources (name, URL, active status)
    - Add "新規登録" button to open source creation form
    - Add edit/deactivate actions per source row
    - Create `apps/web/components/press-source-form-modal.tsx` for create/edit modal
    - Show field-level validation errors on submit
    - Show success/error toast notifications
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 10.2 Implement press article history page
    - Create `apps/web/app/press/articles/page.tsx` as client component
    - Display article list: title (truncated to 80 chars), source name, publication date, classification, category, summary
    - Implement filter dropdowns: source, classification, category (AND logic)
    - Make article title clickable → open original URL in new tab
    - Implement pagination (20 per page, show current page / total pages)
    - Show "記事が見つかりません" when no results match filters
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 10.3 Add press navigation item to sidebar
    - Update `apps/web/components/sidebar.tsx` to add "プレスリリース" navigation section
    - Add sub-links: "ソース管理" (/press), "記事履歴" (/press/articles)
    - Use appropriate icon (e.g., newspaper icon)
    - _Requirements: 1.1, 7.1_

- [x] 11. Checkpoint - Ensure web app builds and all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. MCP Server tools
  - [x] 12.1 Add press release query tools to MCP server
    - Add `query_press_articles` tool: query by source_name, date_from, date_to, category with max 100 results
    - Add `get_latest_press_articles` tool: get latest N (1-50) articles per source, ordered by publishedAt DESC
    - Add `list_press_sources` tool: return all registered sources with active status
    - Return article fields: title, url, publishedAt, relevanceCategory, summary
    - Return error with parameter name and reason for invalid parameters
    - Return empty array (not error) when query matches zero records
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 12.2 Write property tests for MCP tools (Property 19, Property 20, Property 21, Property 22)
    - **Property 19: MCP query result limit**
    - **Property 20: MCP response format completeness**
    - **Property 21: MCP latest-N query correctness**
    - **Property 22: MCP invalid parameter error reporting**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
    - Create `apps/web/__tests__/properties/press-mcp-tools.prop.test.ts`
    - Verify query results never exceed 100 records
    - Verify response objects contain title, url, publishedAt, relevanceCategory, summary
    - Verify latest-N returns min(N, M) articles in date descending order
    - Verify invalid params produce error with parameter name and reason

- [x] 13. GitHub Actions integration
  - [x] 13.1 Add press release pipeline to daily-scan workflow
    - Update `.github/workflows/daily-scan.yml` to add press release scan step after existing UI/UX scan
    - Add step: `python packages/scraper/src/press_main.py`
    - Ensure SLACK_WEBHOOK_URL and DATABASE_URL secrets are available to the step
    - Add `hypothesis` to `packages/analyzer/requirements.txt` for dev dependencies
    - Add failure notification for press scan step
    - _Requirements: 2.1_

- [x] 14. Final checkpoint - Ensure all tests pass and build succeeds
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Python components follow existing patterns: psycopg2 connection pool, cuid2 IDs, Playwright for scraping
- TypeScript components follow existing patterns: Prisma ORM, Next.js API Routes, fast-check for PBT
- The press pipeline runs independently from the existing UI/UX scraper within the same GitHub Actions workflow

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.4"] },
    { "id": 1, "tasks": ["1.3", "1.5", "2.1", "2.3"] },
    { "id": 2, "tasks": ["2.2", "2.4", "4.1"] },
    { "id": 3, "tasks": ["2.5", "4.2", "5.1"] },
    { "id": 4, "tasks": ["5.2", "6.1"] },
    { "id": 5, "tasks": ["6.2", "7.1"] },
    { "id": 6, "tasks": ["9.1", "9.2"] },
    { "id": 7, "tasks": ["9.3", "10.1", "10.2", "10.3"] },
    { "id": 8, "tasks": ["12.1"] },
    { "id": 9, "tasks": ["12.2", "13.1"] }
  ]
}
```
