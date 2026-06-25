# Requirements Document

## Introduction

Phase 2 of the Competitor Monitoring System implements full CRUD (Create, Read, Update, Delete) functionality for managing monitored services (対象サイト) and their monitored pages (対象ページ). This builds on the Phase 1 foundation which established the basic layout, authentication, dashboard, and read-only site listing page. The system monitors competitor real estate portals (SUUMO, athome, カナリー) for UI/UX changes.

## Glossary

- **Service**: A competitor real estate portal site being monitored (e.g., SUUMO, athome, カナリー). Stored in the `Service` database table.
- **Monitored_Page**: A specific URL within a Service that is actively monitored for UI/UX changes. Stored in the `MonitoredPage` database table.
- **Page_Type**: The classification of a Monitored_Page, either "listing" (物件一覧) or "detail" (物件詳細).
- **Device**: The viewport configuration for monitoring a page, either "pc" (1280px) or "sp" (375px).
- **Soft_Delete**: A deletion strategy where records are marked with a `deletedAt` timestamp rather than physically removed from the database.
- **API_Route**: A Next.js App Router API endpoint under `/app/api/` that handles HTTP requests.
- **Service_Form**: The UI component (modal or page) used to create or edit a Service.
- **Page_Form**: The UI component (modal or page) used to create or edit a Monitored_Page.
- **Validation_Error**: An error returned when form input does not meet the defined constraints.

## Requirements

### Requirement 1: Service Listing

**User Story:** As a monitoring operator, I want to view all active services, so that I can see which competitor sites are currently being tracked.

#### Acceptance Criteria

1. WHEN a user requests the service list, THE API_Route SHALL return all Service records where `deletedAt` is null, ordered by `createdAt` ascending.
2. WHEN a user views the sites page, THE Sites_Page SHALL display each Service with its displayName, baseUrl, active status, and the count of associated non-deleted Monitored_Pages.
3. WHEN no services exist, THE Sites_Page SHALL display an empty state message indicating no services are registered.

### Requirement 2: Service Creation

**User Story:** As a monitoring operator, I want to register a new competitor service, so that I can begin tracking its pages for UI/UX changes.

#### Acceptance Criteria

1. WHEN a user submits a valid Service_Form with name, displayName, and baseUrl, THE API_Route SHALL create a new Service record and return the created record with HTTP status 201.
2. WHEN a user submits a Service_Form with an empty name field, THE API_Route SHALL reject the request with a Validation_Error and HTTP status 400.
3. WHEN a user submits a Service_Form with an empty displayName field, THE API_Route SHALL reject the request with a Validation_Error and HTTP status 400.
4. WHEN a user submits a Service_Form with a baseUrl that is not a valid URL format, THE API_Route SHALL reject the request with a Validation_Error and HTTP status 400.
5. WHEN a user submits a Service_Form with a name that already exists in the database, THE API_Route SHALL reject the request with a Validation_Error indicating the name is already taken and HTTP status 409.
6. WHEN a Service is successfully created, THE Sites_Page SHALL update to display the new Service without requiring a full page reload.

### Requirement 3: Service Update

**User Story:** As a monitoring operator, I want to edit an existing service's details, so that I can correct information or update URLs when sites change their domains.

#### Acceptance Criteria

1. WHEN a user submits an updated Service_Form for an existing Service, THE API_Route SHALL update the Service record and return the updated record with HTTP status 200.
2. WHEN a user submits an update with an empty name or displayName, THE API_Route SHALL reject the request with a Validation_Error and HTTP status 400.
3. WHEN a user submits an update with a baseUrl that is not a valid URL format, THE API_Route SHALL reject the request with a Validation_Error and HTTP status 400.
4. WHEN a user submits an update with a name that conflicts with another existing Service, THE API_Route SHALL reject the request with a Validation_Error and HTTP status 409.
5. WHEN a user attempts to update a Service that has been soft-deleted, THE API_Route SHALL return HTTP status 404.
6. WHEN a user toggles a Service's isActive status, THE API_Route SHALL update the isActive field accordingly.

### Requirement 4: Service Deletion

**User Story:** As a monitoring operator, I want to remove a service from monitoring, so that I can stop tracking sites that are no longer relevant.

#### Acceptance Criteria

1. WHEN a user confirms deletion of a Service, THE API_Route SHALL set the `deletedAt` field to the current UTC timestamp and return HTTP status 200.
2. WHEN a Service is soft-deleted, THE API_Route SHALL also soft-delete all associated Monitored_Pages by setting their `deletedAt` fields.
3. WHEN a user attempts to delete a Service that is already soft-deleted, THE API_Route SHALL return HTTP status 404.
4. WHEN a user initiates deletion, THE Sites_Page SHALL display a confirmation dialog before executing the delete operation.

### Requirement 5: Monitored Page Listing

**User Story:** As a monitoring operator, I want to view all monitored pages for a specific service, so that I can manage which URLs are being tracked.

#### Acceptance Criteria

1. WHEN a user requests the page list for a Service, THE API_Route SHALL return all Monitored_Page records for that Service where `deletedAt` is null, ordered by `createdAt` ascending.
2. WHEN displaying pages, THE Page_List SHALL show each Monitored_Page's url, Page_Type label, Device label, active status, and lastScannedAt timestamp in JST.
3. WHEN a Service has no monitored pages, THE Page_List SHALL display an empty state message.

### Requirement 6: Monitored Page Creation

**User Story:** As a monitoring operator, I want to add a new URL to monitor for a service, so that I can track specific pages for UI/UX changes.

#### Acceptance Criteria

1. WHEN a user submits a valid Page_Form with url, pageType, and device, THE API_Route SHALL create a new Monitored_Page record associated with the specified Service and return the created record with HTTP status 201.
2. WHEN a user submits a Page_Form with an empty url field, THE API_Route SHALL reject the request with a Validation_Error and HTTP status 400.
3. WHEN a user submits a Page_Form with a url that is not a valid URL format, THE API_Route SHALL reject the request with a Validation_Error and HTTP status 400.
4. WHEN a user submits a Page_Form with a pageType value other than "listing" or "detail", THE API_Route SHALL reject the request with a Validation_Error and HTTP status 400.
5. WHEN a user submits a Page_Form with a device value other than "pc" or "sp", THE API_Route SHALL reject the request with a Validation_Error and HTTP status 400.
6. WHEN a user submits a Page_Form for a Service that does not exist or is soft-deleted, THE API_Route SHALL return HTTP status 404.

### Requirement 7: Monitored Page Update

**User Story:** As a monitoring operator, I want to edit a monitored page's settings, so that I can change the device type or page classification without re-creating the entry.

#### Acceptance Criteria

1. WHEN a user submits an updated Page_Form for an existing Monitored_Page, THE API_Route SHALL update the record and return the updated record with HTTP status 200.
2. WHEN a user submits an update with an invalid url, pageType, or device value, THE API_Route SHALL reject the request with a Validation_Error and HTTP status 400.
3. WHEN a user attempts to update a Monitored_Page that has been soft-deleted, THE API_Route SHALL return HTTP status 404.
4. WHEN a user toggles a Monitored_Page's isActive status, THE API_Route SHALL update the isActive field accordingly.

### Requirement 8: Monitored Page Deletion

**User Story:** As a monitoring operator, I want to remove a page from monitoring, so that I can stop tracking URLs that are no longer relevant.

#### Acceptance Criteria

1. WHEN a user confirms deletion of a Monitored_Page, THE API_Route SHALL set the `deletedAt` field to the current UTC timestamp and return HTTP status 200.
2. WHEN a user attempts to delete a Monitored_Page that is already soft-deleted, THE API_Route SHALL return HTTP status 404.
3. WHEN a user initiates page deletion, THE Page_List SHALL display a confirmation dialog before executing the delete operation.

### Requirement 9: Form Validation and User Feedback

**User Story:** As a monitoring operator, I want clear validation feedback on forms, so that I can correct errors before submission.

#### Acceptance Criteria

1. WHEN a user submits a form with validation errors, THE Service_Form or Page_Form SHALL display field-level error messages in Japanese adjacent to the invalid fields.
2. WHEN a user corrects a field that previously had an error, THE Service_Form or Page_Form SHALL clear the error message for that field.
3. WHEN an API request fails due to a server error, THE System SHALL display a user-friendly error message in Japanese.
4. WHEN a create or update operation succeeds, THE System SHALL display a success notification in Japanese.

### Requirement 10: UI Navigation and Interaction

**User Story:** As a monitoring operator, I want intuitive navigation between services and their pages, so that I can efficiently manage all monitored targets.

#### Acceptance Criteria

1. WHEN a user clicks on a Service card on the Sites_Page, THE System SHALL navigate to or display the list of Monitored_Pages for that Service.
2. THE Sites_Page SHALL display action buttons for adding a new Service, editing each Service, and deleting each Service.
3. THE Page_List SHALL display action buttons for adding a new Monitored_Page, editing each page, and deleting each page.
4. WHEN a destructive action (delete) button is pressed, THE System SHALL require explicit confirmation before proceeding.
