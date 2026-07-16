# Requirements Document

## Introduction

競合不動産ポータルサイト（SUUMO, athome, カナリー）のプレスリリースを自動的にキャッチアップし、サービス改善に活用可能な情報として蓄積・通知するシステム。既存のUI/UX変更検知と分離してプレスリリース情報をDBに保存し、AIによる要約とSlack通知でチームへの情報共有を行う。管理画面からウォッチ対象の設定が可能で、将来的にはMCP経由で他のメンバーも蓄積データを活用できるようにする。

## Glossary

- **Press_Release_Monitor**: プレスリリースの取得・分類・要約・通知を行うシステム全体
- **Press_Source**: プレスリリースの配信元（競合各社のプレスリリースページ）
- **Press_Article**: 取得した個別のプレスリリース記事データ
- **Relevance_Classifier**: プレスリリースの関連性を判定し、対象/対象外を分類するコンポーネント
- **Article_Summarizer**: プレスリリース本文をAIで要約するコンポーネント
- **Slack_Notifier**: 要約結果をSlackチャンネルに投稿するコンポーネント
- **Admin_Dashboard**: プレスウォッチの対象設定や履歴閲覧を行う管理画面
- **MCP_Server**: MCPプロトコル経由でプレスリリースデータを提供するサーバー
- **Relevant_Article**: サービスに関わる内容またはサービス改善に関わる調査データに該当するプレスリリース
- **Irrelevant_Article**: 人事異動・IR情報・イベント告知など、サービス改善に直接関係しないプレスリリース

## Requirements

### Requirement 1: プレスリリースソースの管理

**User Story:** As a 運用担当者, I want 管理画面からプレスウォッチの対象ソースを指定・編集できること, so that 監視対象を柔軟に変更できる

#### Acceptance Criteria

1. THE Admin_Dashboard SHALL display a list of all registered Press_Source entries with their name, URL, and active status, sorted by registration date in ascending order, excluding soft-deleted entries
2. WHEN a user adds a new Press_Source via the Admin_Dashboard, THE Press_Release_Monitor SHALL validate that the name is 1–50 characters (alphanumeric and hyphens only) and the URL is a valid http or https URL, and save the source with name, press release page URL, and active flag set to true by default
3. WHEN a user edits an existing Press_Source, THE Admin_Dashboard SHALL update the source name, URL, or active status in the database after applying the same validation rules as registration
4. WHEN a user deactivates a Press_Source, THE Press_Release_Monitor SHALL exclude the source from subsequent scraping runs
5. IF a user attempts to register a Press_Source with a URL that exactly matches an existing active entry's URL, THEN THE Admin_Dashboard SHALL reject the registration and display an error message indicating the URL is already registered
6. IF a user submits a Press_Source with a name or URL that fails validation, THEN THE Admin_Dashboard SHALL display field-level error messages indicating which fields are invalid and preserve the user's entered values
7. IF a user attempts to edit or deactivate a Press_Source that does not exist or has been deleted, THEN THE Admin_Dashboard SHALL display an error message indicating the source was not found

### Requirement 2: プレスリリースの自動取得

**User Story:** As a サービス改善担当者, I want 競合のプレスリリースが毎日自動的に取得されること, so that 手動確認の手間なく最新情報を把握できる

#### Acceptance Criteria

1. THE Press_Release_Monitor SHALL scrape all active Press_Source pages on a daily schedule (JST 6:00)
2. WHEN the scraper retrieves a press release page, THE Press_Release_Monitor SHALL extract article title, publication date, article URL, and article body text (maximum 100,000 characters) for each new article
3. WHEN a new article is detected whose article URL does not match any existing Press_Article record in the database, THE Press_Release_Monitor SHALL save the article as a new Press_Article record
4. WHILE a Press_Source is inactive, THE Press_Release_Monitor SHALL skip scraping for that source
5. IF the scraper fails to receive an HTTP response from a Press_Source within 30 seconds, or receives an HTTP status code of 400 or above, THEN THE Press_Release_Monitor SHALL log the error including the source name, URL, and failure reason, and continue processing remaining sources
6. IF the scraper fails to access a Press_Source, THEN THE Press_Release_Monitor SHALL send a failure notification to the Slack channel including the source name and failure reason
7. IF the scraper retrieves a press release page but extracts zero new articles, THEN THE Press_Release_Monitor SHALL log the result as a successful scrape with no new content and not treat it as an error

### Requirement 3: プレスリリースの関連性分類

**User Story:** As a サービス改善担当者, I want プレスリリースが自動的にサービス改善に関連するものかどうか分類されること, so that 不要なニュースに時間を取られない

#### Acceptance Criteria

1. WHEN a new Press_Article is saved, THE Relevance_Classifier SHALL classify the article as either Relevant_Article or Irrelevant_Article within 30 seconds of the save event
2. THE Relevance_Classifier SHALL classify articles about competitor service features, UX improvements, pricing changes, and market survey data as Relevant_Article
3. THE Relevance_Classifier SHALL classify articles about personnel changes, IR announcements, event sponsorships, and corporate news that does not mention product functionality or end-user experience as Irrelevant_Article
4. WHEN classification is complete, THE Press_Release_Monitor SHALL store the classification result and the assigned relevance category label with the Press_Article record
5. THE Relevance_Classifier SHALL assign a relevance category label (service_feature, market_data, ux_improvement, pricing, other) to each Relevant_Article
6. IF the Relevance_Classifier cannot determine classification with sufficient pattern match (matching score below the configured threshold), THEN THE Relevance_Classifier SHALL classify the article as Relevant_Article and mark it with a flag indicating manual review is required
7. IF the Press_Article content is empty or unreadable, THEN THE Relevance_Classifier SHALL mark the article as classification_failed and store an error indication with the Press_Article record

### Requirement 4: プレスリリースのAI要約

**User Story:** As a サービス改善担当者, I want プレスリリースの内容がAIで要約されること, so that 記事全文を読まずに要点を素早く把握できる

#### Acceptance Criteria

1. WHEN a Press_Article is classified as Relevant_Article, THE Article_Summarizer SHALL generate a summary from the article body text within 30 seconds of classification completion
2. THE Article_Summarizer SHALL produce a summary between 50 and 200 characters in Japanese
3. THE Article_Summarizer SHALL include in the summary at least one concrete finding related to the article's relevance category (service_feature, market_data, ux_improvement, or pricing)
4. WHEN summarization is complete, THE Press_Release_Monitor SHALL store the summary with the Press_Article record
5. IF the Article_Summarizer fails to generate a summary due to timeout, empty response, or API error, THEN THE Press_Release_Monitor SHALL store the article without a summary and set the article's review status to "pending_manual_review"
6. IF the Article_Summarizer produces a summary that exceeds 200 characters, THEN THE Article_Summarizer SHALL truncate the summary to 200 characters at the nearest sentence boundary

### Requirement 5: Slack通知

**User Story:** As a チームメンバー, I want プレスリリースの要約がSlackチャンネルに投稿されること, so that チーム全員が競合動向をリアルタイムに把握できる

#### Acceptance Criteria

1. WHEN a Relevant_Article has been summarized, THE Slack_Notifier SHALL post a notification to the designated Slack channel within 60 seconds of summarization completion
2. THE Slack_Notifier SHALL include the article title, article URL, source name, publication date, relevance category, and AI-generated summary in each notification
3. THE Slack_Notifier SHALL format the notification with the article title as a clickable link
4. WHEN multiple Relevant_Articles are summarized in a single scraping run, THE Slack_Notifier SHALL post one notification per article
5. WHILE no Relevant_Article is detected in a scraping run, THE Slack_Notifier SHALL not post any message
6. IF the Slack notification fails, THEN THE Press_Release_Monitor SHALL log the failure and retry once after 30 seconds
7. IF the retry also fails, THEN THE Press_Release_Monitor SHALL log the final failure with the article ID and skip the notification for that article without blocking remaining notifications
8. IF the Slack Webhook URL is not configured, THEN THE Press_Release_Monitor SHALL log a configuration error and skip all Slack notifications for the scraping run

### Requirement 6: プレスリリースデータのUI/UXデータとの分離保存

**User Story:** As a 開発者, I want プレスリリースデータがUI/UX変更データとは別のテーブルに保存されること, so that データの管理と活用が明確に分離される

#### Acceptance Criteria

1. THE Press_Release_Monitor SHALL store Press_Article records in a dedicated table separate from the existing Change table, with no foreign key relationship between Press_Article and Change
2. THE Press_Release_Monitor SHALL associate each Press_Article with its Press_Source via a foreign key relationship, and SHALL cascade-delete Press_Article records when the associated Press_Source is deleted
3. THE Press_Release_Monitor SHALL store the following fields in the Press_Article record: article title (maximum 512 characters), publication date, article URL (maximum 2,048 characters), body text (maximum 100,000 characters), classification result, relevance category, and AI summary (maximum 5,000 characters)
4. THE Press_Release_Monitor SHALL record the scraping timestamp for each Press_Article in UTC
5. THE Press_Release_Monitor SHALL implement soft delete (nullable deleted_at DateTime column) for Press_Article records, consistent with existing data model conventions where soft-deleted records are excluded from default queries
6. THE Press_Release_Monitor SHALL enforce uniqueness of Press_Article records by the combination of Press_Source foreign key and article URL, preventing duplicate entries for the same article from the same source

### Requirement 7: プレスリリース履歴の閲覧

**User Story:** As a サービス改善担当者, I want 管理画面から過去のプレスリリース履歴を閲覧できること, so that 時系列で競合動向を振り返ることができる

#### Acceptance Criteria

1. THE Admin_Dashboard SHALL display a list of Press_Article records sorted by publication date in descending order
2. THE Admin_Dashboard SHALL allow filtering Press_Article records by Press_Source, relevance classification, and relevance category, applying all selected filters with AND logic
3. THE Admin_Dashboard SHALL display article title (truncated to 80 characters with ellipsis if exceeded), source name, publication date, classification, category, and summary in the list view
4. WHEN a user clicks on a Press_Article in the list, THE Admin_Dashboard SHALL navigate to the original article URL in a new browser tab
5. THE Admin_Dashboard SHALL support pagination with 20 articles per page, displaying the current page number and total page count
6. IF no Press_Article records match the current filter criteria, THEN THE Admin_Dashboard SHALL display a message indicating that no articles were found

### Requirement 8: MCP経由でのデータ提供

**User Story:** As a チームメンバー, I want MCP経由でプレスリリースデータにアクセスできること, so that AI分析と組み合わせてサービス改善に活用できる

#### Acceptance Criteria

1. THE MCP_Server SHALL expose a tool to query Press_Article records by source name, date range, and relevance category, returning a maximum of 100 records per query
2. THE MCP_Server SHALL return article title, URL, publication date, relevance category, and summary in the query response
3. THE MCP_Server SHALL expose a tool to retrieve the latest N articles per Press_Source, where N is an integer between 1 and 50
4. WHEN the MCP_Server receives a query with invalid parameters (non-existent source name, invalid date format, unrecognized relevance category, or N outside the allowed range), THE MCP_Server SHALL return an error message indicating the parameter name and the reason for invalidity
5. THE MCP_Server SHALL expose a tool to list all registered Press_Source entries with their active status
6. WHEN a query matches zero Press_Article records, THE MCP_Server SHALL return an empty result list with no error
