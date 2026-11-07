# ShelfWise: Product Requirements Document (PRD)

---

## 1. Document Overview & Executive Summary

ShelfWise is an intelligent, web-based retail demand forecasting and inventory replenishment application. It empowers boutique retail operators, category managers, and multi-location store supervisors to anticipate customer demand 28 days into the future, maintain optimal safety stock buffers, prevent costly stockouts, and reduce working capital tied up in excess inventory.

Unlike heavy, cost-prohibitive enterprise resource planning (ERP) platforms that require dedicated data science teams, ShelfWise delivers an intuitive, automated experience. It combines automated machine learning forecasting using LightGBM, rigorous statistical baseline comparisons, algorithmic inventory policies, and a conversational AI assistant grounded directly in store telemetry.

---

## 2. Problem Statement & Value Proposition

### 2.1 Problem Statement
1. **The Twin Hazards of Retail Inventory**: Retailers face constant pressure between two extremes:
   - **Stockouts**: When high-velocity products run out during demand surges, retailers suffer direct revenue loss, brand erosion, and customer churn.
   - **Overstock**: Over-ordering ties up precious cash flow in slow-moving inventory, accumulates holding costs, and increases the risk of markdown losses or spoilage.
2. **The Data Science Gap in Mid-Market Retail**: Enterprise retailers employ data science divisions to build custom predictive models. Independent retailers, franchise operators, and boutique chains rely heavily on static spreadsheets, rule-of-thumb ordering, or trailing averages that fail to account for promotional lift, seasonality, and lead-time variability.
3. **Legacy Tool Complexity**: Existing ERP forecasting modules are cumbersome, expensive, difficult to integrate, and opaque to operational staff on the floor.

### 2.2 Value Proposition
- **Tagline**: *"Know what to stock, before the shelf runs empty."*
- **Actionable 28-Day Visibility**: Generates 28-day daily demand projections equipped with empirical prediction interval bands so planners understand best- and worst-case demand trajectories.
- **Empirically Proven Accuracy**: Outperforms standard baseline models (Naive and Seasonal Naive) on 9 out of 10 retail locations, delivering a proven ~14.2% error reduction.
- **Dynamic Replenishment Triggers**: Replaces static reorder rules with dynamic safety stock and reorder point calculations that automatically factor in lead time and historical forecast error volatility.
- **Conversational Decision Support**: Provides a natural language assistant capable of querying inventory stock levels, causal sales drivers, and reorder requirements without requiring SQL or analytics knowledge.

---

## 3. Target User Personas

### Persona A: The Multi-Location Store Manager ("Marcus")
- **Role**: Manages 5 to 10 retail storefronts across an urban district.
- **Needs**: Needs to know every Monday morning which specific store/SKU combinations are in danger of stocking out before the next weekly distributor shipment.
- **Pain Points**: Spends hours stitching POS exports in Excel; frequently misses spikes in promotional demand.
- **ShelfWise Benefit**: Reviews the executive dashboard and inventory alert table filtered by "Stockout Risk", adjusting orders in minutes.

### Persona B: The Boutique Category Planner ("Elena")
- **Role**: Plans purchasing and merchandising for specialty apparel and packaged goods.
- **Needs**: Needs reliable forecast horizon projections to negotiate supplier purchase quantities across variable distributor lead times.
- **Pain Points**: Distributor lead times range from 7 to 14 days, making simple trailing averages inaccurate.
- **ShelfWise Benefit**: Uses 28-day prediction intervals on the Forecast page to quantify uncertainty and verify safety stock buffers.

### Persona C: The Retail Operations Director ("Devon")
- **Role**: Oversees inventory health, working capital efficiency, and shrink reduction across the company portfolio.
- **Needs**: High-level visibility into total suggested order units versus estimated excess inventory units.
- **Pain Points**: Working capital trapped in surplus stock prevents new product line rollouts.
- **ShelfWise Benefit**: Monitors portfolio-wide overstock counts and days-of-cover distributions on the Dashboard.

---

## 4. Core User Journeys & User Stories

### Journey 1: Authentication & Access
- **User Story**: *As a store manager, I want to securely log into ShelfWise using my corporate email or Google Workspace account so that I can immediately access store telemetry.*
- **Flow**:
  1. User navigates to the login page.
  2. User inputs email and password, clicks "Sign in with Google" for single sign-on, or clicks the one-click demo account filler for quick evaluation.
  3. Upon successful credential verification, the system issues JWT access and refresh tokens, establishes user state, and routes to the Dashboard.

### Journey 2: Sales Data Upload & Validation
- **User Story**: *As an inventory analyst, I want to upload new point-of-sale CSV files and receive instant validation feedback so that dirty data does not corrupt our forecast models.*
- **Flow**:
  1. User navigates to the Upload page.
  2. User drags and drops a CSV file into the dropzone (or browses local storage) and enters an optional dataset name.
  3. User clicks "Upload & Import".
  4. The system validates header schema, data types, and positive value constraints.
  5. If validation passes, records are ingested into the database, an audit trail row is created, and a success banner confirms row counts.
  6. If validation fails, a detailed error summary displays specific offending rows and validation failure reasons.

### Journey 3: Demand Forecast Generation & Benchmark Review
- **User Story**: *As a planner, I want to generate a 28-day machine learning forecast for any store and product and compare it against naive baselines so that I can trust the model's accuracy.*
- **Flow**:
  1. User navigates to the Forecast page.
  2. User selects a store and product SKU from dropdown menus.
  3. User views the latest completed run's interactive Recharts visualization: historical actuals, 28-day forecast trajectory, empirical prediction interval bands, and the cutoff point dividing actuals from projections.
  4. User inspects benchmark cards comparing LightGBM against Naive and 28-day Seasonal Naive baselines across WAPE, Bias, and RMSSE metrics.
  5. User can click "Run new forecast" to initiate a fresh training run in a background worker thread.
  6. The interface polls run status every two seconds until complete, automatically updating all charts and metrics.

### Journey 4: Inventory Alerts & Replenishment Planning
- **User Story**: *As an operations lead, I want to review automated stockout warnings and suggested reorder quantities so that I can replenish stock before shelves go empty.*
- **Flow**:
  1. User navigates to the Inventory page.
  2. User views four interactive summary cards: Stockout Risk, Reorder Now, Overstock, and Healthy (OK).
  3. User clicks any summary card to instantly filter the table to that specific severity category.
  4. User filters by store location or searches specific SKU codes.
  5. For each item, user inspects on-hand stock, lead time days, average daily forecast, lead time demand, calculated safety stock, dynamic reorder point, days of cover, and suggested order quantity.

### Journey 5: Inline On-Hand Stock Adjustment
- **User Story**: *As a floor supervisor, I want to update physical on-hand counts directly within the alert table after a stocktake without leaving the page.*
- **Flow**:
  1. User clicks the "On Hand" numeric cell for an item on the Inventory page.
  2. An inline numeric input field appears with Save and Cancel actions.
  3. User types the revised count and presses Enter or clicks the save checkmark.
  4. The system sends a partial update request, recalculates safety margins, days of cover, and status in real time, and updates the table row and summary KPI chips immediately.

### Journey 6: Conversational AI Assistance
- **User Story**: *As a store manager, I want to ask plain-language questions about impending stockouts or demand trends so that I get fast, grounded recommendations without navigating complex tables.*
- **Flow**:
  1. User navigates to the Assistant page.
  2. User clicks a starter prompt pill (e.g., "Which items will stock out soon?", "What should I reorder this week?") or types a custom question into the chat bar.
  3. The assistant triggers read-only diagnostic tools against database tables and forecast outputs.
  4. The assistant formats a grounded answer with bold key metrics, bulleted action items, and structured markdown tables.
  5. If external LLM APIs are unreachable or unconfigured, the assistant automatically switches to deterministic offline fallback logic to answer accurately.

---

## 5. System Architecture & Tech Stack

### 5.1 Technology Layers
- **Backend Framework**: Django 5 and Django REST Framework running Python 3.13.
- **Database Engine**: PostgreSQL 16 relational database storing store dimensions, product catalogs, historical sales records, dataset ingestion audits, forecast runs, forecast point projections, and stock levels.
- **Machine Learning & Analytics**: Plain Python in a dedicated analytical module with zero Django framework imports, utilizing Pandas, NumPy, Scikit-Learn, and LightGBM.
- **Frontend Application**: React 19 single-page application built with TypeScript, Vite, and Tailwind CSS v4.
- **Data Visualization**: Recharts library rendering composed multi-line, area, and reference-line charts.
- **State Management & Network Client**: TanStack React Query for declarative data fetching, caching, and background polling; Axios with request and response interceptors.
- **Iconography**: Lucide React icons.
- **Containerization & Deployment**: Docker and Docker Compose multi-container profiles, designed for deployment on Render (backend Web Service) and Vercel (frontend static hosting).

---

## 6. Functional Requirements

### 6.1 Authentication & Session Management
- **FR-AUTH-01**: The system shall support user registration via email, password, and optional full name.
- **FR-AUTH-02**: The system shall authenticate users via email and password, issuing a JSON Web Token (JWT) access token (30-minute validity) and refresh token (7-day validity).
- **FR-AUTH-03**: The system shall provide automatic refresh token rotation when API requests return HTTP 401 Unauthorized responses.
- **FR-AUTH-04**: The system shall support Google Single Sign-On (SSO) via the OpenID Connect (OIDC) authorization code flow with secure random state verification.
- **FR-AUTH-05**: The system shall provide an endpoint reporting whether SSO is enabled based on server environment configuration.
- **FR-AUTH-06**: The system shall provide a demo account quick-fill feature on the login screen when configured in the frontend environment.

### 6.2 Data Ingestion & Audit Trail
- **FR-DATA-01**: The system shall accept tabular sales datasets uploaded as UTF-8 comma-separated value (CSV) files through multipart form submission.
- **FR-DATA-02**: The system shall validate uploaded CSVs against a strict Pandera schema requiring exact column names: store, sku, date, units_sold, price, on_promo.
- **FR-DATA-03**: The system shall enforce non-null values, non-negative units sold, non-negative price, and valid ISO-8601 date formats.
- **FR-DATA-04**: The system shall reject invalid files with HTTP 400 and return descriptive, row-specific error messages.
- **FR-DATA-05**: The system shall record an audit history for every uploaded dataset, tracking filename, display name, row count, ingestion timestamp, status (pending, processing, done, failed), and error details.
- **FR-DATA-06**: The system shall provide an idempotent automated seeding command that loads demo sales records, seeds the demo account, trains an initial forecast run, and seeds inventory stock levels.

### 6.3 Demand Forecasting Engine
- **FR-FCST-01**: The system shall generate daily demand forecasts spanning a fixed 28-day forward-looking horizon per store and product SKU.
- **FR-FCST-02**: The system shall enforce time-based splitting with zero feature leakage: training set, a 28-day validation window for early stopping, and a held-out final 28-day test window for benchmark evaluation.
- **FR-FCST-03**: The system shall restrict all auto-regressive lag features and rolling aggregations to delays of 28 days or greater to avoid using ground-truth values from the evaluation window.
- **FR-FCST-04**: The system shall train an LGBMRegressor model with early stopping, categorical encoding for store and SKU dimensions, and optional OpenMP thread bounding.
- **FR-FCST-05**: The system shall calculate empirical 80% prediction intervals (10th percentile lower bound, 90th percentile upper bound) calibrated against test-window residuals.
- **FR-FCST-06**: The system shall evaluate and store standardized comparative metrics for every run:
  - Weighted Absolute Percentage Error (WAPE)
  - Forecast Bias (Mean Forecast Error / Mean Actual Demand)
  - Root Mean Squared Scaled Error (RMSSE)
- **FR-FCST-07**: The system shall benchmark LightGBM against two baseline models: Naive (carrying forward the last observed sale) and Seasonal Naive (28-day seasonal cycle carryover).
- **FR-FCST-08**: The system shall run forecast training pipelines asynchronously in a background worker thread when initiated via the API.
- **FR-FCST-09**: The system shall detect stale forecast runs that remain in "running" status for longer than 10 minutes and automatically transition them to "failed" with an interrupted message.

### 6.4 Inventory Policies & Replenishment Alerts
- **FR-INV-01**: The system shall maintain inventory stock levels linked to specific store and SKU combinations, tracking physical on-hand units and supplier lead time in days.
- **FR-INV-02**: The system shall calculate daily demand volatility (sigma_daily) as the standard deviation of residuals (actual minus forecast) on the test-window evaluation period.
- **FR-INV-03**: The system shall compute dynamic safety stock using the standard replenishment buffer formula: safety_stock = round(1.65 * sigma_daily * sqrt(lead_time_days)), where 1.65 represents a 95% service level factor.
- **FR-INV-04**: The system shall compute lead time demand as the sum of projected daily forecasts across the item's supplier lead time days.
- **FR-INV-05**: The system shall compute dynamic reorder points as: reorder_point = round(lead_time_demand + safety_stock).
- **FR-INV-06**: The system shall calculate days of cover as: days_of_cover = round(on_hand / avg_daily_forecast, 1).
- **FR-INV-07**: The system shall categorize every inventory item into one of four mutually exclusive severity statuses:
  - Stockout Risk: on_hand <= 0 OR days_of_cover <= lead_time_days.
  - Reorder Now: on_hand <= reorder_point (and not in stockout risk).
  - Overstock: days_of_cover > 21.0 days.
  - Healthy (OK): stock levels comfortably cover demand and safety margins without exceeding overstock thresholds.
- **FR-INV-08**: The system shall compute suggested replenishment order quantities as: suggested_order_qty = max(0, reorder_point - on_hand).
- **FR-INV-09**: The system shall support inline updates to on-hand stock counts via HTTP PATCH, immediately triggering status recalculation.
- **FR-INV-10**: The system shall provide an aggregate inventory summary endpoint reporting counts per status, total suggested order units, and estimated excess overstock units.

### 6.5 Grounded Conversational AI Assistant
- **FR-AI-01**: The system shall expose a conversational chat endpoint accepting multi-turn conversation message history (roles: user, assistant).
- **FR-AI-02**: The system shall ground assistant replies directly in database queries and forecast outputs using native LLM tool calling.
- **FR-AI-03**: The system shall provide four read-only diagnostic tools for assistant execution:
  - get_model_metrics: returns WAPE, bias, and RMSSE for baselines and LightGBM.
  - get_inventory_summary: returns aggregate status counts and total suggested reorder units.
  - get_alerts: returns filtered lists of items by severity status and store location.
  - get_series_forecast: returns historical actuals, forecast projections, and prediction intervals for a specified store and SKU.
- **FR-AI-04**: The system shall support Google Gemini and Anthropic Claude provider integrations selected via environment variables.
- **FR-AI-05**: The system shall implement an automatic retry mechanism when LLM providers return HTTP 429 rate limit responses, respecting retry delay headers up to 20 seconds.
- **FR-AI-06**: The system shall implement a deterministic offline fallback mode that analyzes user intent and executes Python/Pandas diagnostic tools locally when external LLM keys are absent, exhausted, or failing.

---

## 7. Application Pages & UI Specifications

### 7.1 `/login` (Sign In)
- **Purpose**: Authenticate existing users and provide access to the demo environment.
- **Layout**: Two-column responsive split screen on desktop (stacked vertically on mobile).
  - Left Panel: Rich blue gradient showcasing the ShelfWise brand identity, core value narrative, and feature highlight cards (28-day forecasts, reorder alerts, AI assistant).
  - Right Panel: Clean authentication card containing email input, password input, sign-in button, Google SSO button (when configured), and demo account auto-fill shortcut.
- **State Handling**: Inline error banners for invalid credentials; disabled button state with spinner during authentication.

### 7.2 `/register` (Sign Up)
- **Purpose**: Allow new operators to create a ShelfWise account.
- **Layout**: Centered authentication card mirroring the login design language with fields for email, full name, password, and password confirmation.
- **State Handling**: Validation messages for password mismatch, weak passwords, or duplicate email addresses.

### 7.3 `/auth/callback` (SSO Callback)
- **Purpose**: Headless listener handling the OAuth 2.0 / OpenID Connect redirect from Google.
- **Behavior**: Extracts the authorization code and state parameter, validates CSRF state, exchanges code for user profile data, writes JWT tokens to local storage, and redirects to the Dashboard.
- **State Handling**: Displays a loading spinner with explanatory text; presents a friendly error card with a return-to-login link if code exchange fails.

### 7.4 `/` (Dashboard)
- **Purpose**: Executive overview of portfolio health, forecast trajectories, and urgent replenishment priorities.
- **Layout**:
  - Context Banner: Brief portfolio description and quick-action links to Upload and Forecast views.
  - Four Top-Level KPI Cards:
    1. Forecast Accuracy: Displays LightGBM accuracy percentage (100 minus WAPE) with a caption showing exact WAPE.
    2. Stockout Risks: Urgent count of items with coverage less than supplier lead times.
    3. Suggested Orders: Total purchase order units recommended across all stores.
    4. Excess Stock: Estimated volume of units exceeding 21 days of cover.
  - Aggregated Demand Trajectory Chart: Composed Recharts chart displaying total daily historical actuals against portfolio-wide forecast projections.
  - Model Benchmark Comparison: Visual bar comparing LightGBM WAPE against the Naive baseline.
  - Most Urgent Items Table: Quick-access table showing the top 8 critical inventory alerts sorted by severity.

### 7.5 `/upload` (Data Upload & Ingestion)
- **Purpose**: Manage historical POS sales datasets and inspect schema requirements.
- **Layout**:
  - Header: Upload title, format indicator pill (CSV UTF-8).
  - Dropzone Area: Large drag-and-drop container with dashed borders, dynamic drag-hover highlight, browse button, and required schema column pill badges.
  - Dataset Name Input: Optional text field for dataset labelling.
  - Recent Uploads Table: Searchable table displaying dataset name, imported row count, ingestion timestamp, and status badges.
- **State Handling**:
  - Success banner showing exact imported row count and dataset ID.
  - Error banner displaying structured, scrollable list of Pandera validation failures.
  - Non-blocking "Syncing..." badge during table background refetches.

### 7.6 `/forecast` (Demand Forecasts)
- **Purpose**: Deep-dive store- and SKU-level 28-day machine learning demand projections.
- **Layout**:
  - Header Toolbar: Store dropdown selector, SKU dropdown selector, latest run status chip, and "Run new forecast" action button.
  - Main Prediction Chart: Recharts interactive chart featuring:
    - Solid dark slate line with points for historical actual sales.
    - Solid blue line for 28-day forecast projections.
    - Shaded translucent blue prediction interval band between lower (10th percentile) and upper (90th percentile) bounds.
    - Vertical dashed reference line labelled "Forecast starts" dividing test window actuals from future projections.
    - Interactive tooltip displaying date, forecast, lower bound, upper bound, and actual sales.
  - Model Benchmark Cards: Three comparison cards (Naive, Seasonal Naive 28d, LightGBM) displaying WAPE, Bias, and RMSSE, with the best-performing model highlighted and an explanatory text summary.
  - Future Projections Table: Tabular breakdown of the upcoming 28 days listing projected daily demand and prediction interval bounds.
- **State Handling**:
  - Polling spinner and disabled button state during model training.
  - Prominent alert banner if background training fails.

### 7.7 `/inventory` (Inventory Alerts & Replenishment)
- **Purpose**: Operational command center for monitoring stock cover, safety buffers, and order quantities.
- **Layout**:
  - Interactive Severity Summary Cards: Four clickable KPI cards representing Stockout Risk, Reorder Now, Overstock, and Healthy (OK) that act as single-click toggle filters.
  - Filter Toolbar: Store location dropdown selector, SKU text search input, and active filter pill with clear button.
  - Inventory Alerts Table: 10-column data table showing Store, SKU, On Hand (clickable for inline edit), Lead Time, Avg Daily Forecast, Safety Stock (with explanatory popover tooltip), Reorder Point (with popover tooltip), Days of Cover, Status Badge, and Suggested Order Quantity.
  - Pagination Controls: Previous and Next controls with page count indicators.
- **State Handling**:
  - Skeleton / loader state during telemetry calculation.
  - Inline input with save/cancel controls during on-hand stock edits.
  - Empty state message when active filter criteria match zero items.

### 7.8 `/assistant` (Conversational AI Assistant)
- **Purpose**: Interactive decision-support co-pilot answering grounded natural language queries.
- **Layout**:
  - Fixed-height conversation viewport engineered to avoid outer page scrolling.
  - Header Toolbar: Descriptive subtitle, neutral source badge ("Answers come from your forecast data"), and New Chat reset action.
  - Message Thread: Scrollable stream of user queries and assistant responses formatted in rich markdown with bold text, bullet lists, blockquotes, and tables.
  - Empty State Canvas: Welcoming hero graphic with four clickable starter prompt chips.
  - Sticky Input Bar: Text input field with send button, Enter-key handler, and loading indicator.
- **State Handling**:
  - Animated typing card ("Querying forecast data and generating recommendation...") during tool execution.
  - Dismissible error banner if network requests fail.

---

## 8. Roles, Permissions & Security Model

### 8.1 Role Model
- **Single Authenticated Role**: In the current built application, there is exactly one user privilege tier: Authenticated Operator.
- **No Per-User Data Isolation**: The system does not implement multi-tenant or per-user data segregation. All authenticated users share access to the same store dimensions, product catalogs, historical sales records, forecast runs, and inventory stock levels.
- **Anonymous Access Rejection**: All API endpoints under the retail, datasets, forecasts, inventory, and assistant applications strictly enforce authentication permissions; unauthenticated requests receive HTTP 401 Unauthorized.

### 8.2 Token Security
- **JWT Storage**: Tokens are stored in browser localStorage and automatically attached to outgoing HTTP requests via Axios request interceptors using the standard Bearer scheme.
- **Short-Lived Access**: Access tokens expire after 30 minutes; refresh tokens remain valid for 7 days.
- **Automatic Interception**: Expired access tokens trigger an automatic refresh handshake via Axios response interceptors; if the refresh token has expired, stored credentials are purged and the user is redirected to the login view.

### 8.3 Network & Transport Security
- **Reverse Proxy Header Trust**: The backend is configured to recognize secure HTTPS connections terminated by reverse proxies and cloud load balancers.
- **Strict Host Checking**: Allowed hosts are validated against explicit environment-configured hostnames.
- **CORS & CSRF Safeguards**: Cross-Origin Resource Sharing (CORS) and Cross-Site Request Forgery (CSRF) trusted origins are dynamically constructed from frontend URLs and explicitly allowed external origins.

---

## 9. Data Architecture & Ingestion Requirements

### 9.1 Data Adaptation & Synthesis
- **Store-Level Historical Sales**: Adapted from the public Rossmann store sales benchmark dataset, reflecting authentic multi-store demand patterns, day-of-week seasonality, and promotional lifts.
- **Simulated Dimensions**: Individual product SKUs (P1 through P5), unit price tiers ($1.99 to $9.99), and physical on-hand inventory balances are simulated to model realistic boutique retail operations across 8 to 10 store locations (e.g., S1097, S262, S335, S423, S494, S562, S682, S733, S769, S85).

### 9.2 Ingestion Schema Specifications
Every sales record ingested via CSV upload or demo seeding must strictly satisfy the following column schema:
1. `store` (string): Unique retail store location code (e.g., "S1097").
2. `sku` (string): Stock Keeping Unit product identifier (e.g., "P1").
3. `date` (date): Transaction date in ISO-8601 format (YYYY-MM-DD).
4. `units_sold` (integer/float): Quantity of items sold on the date (must be non-negative).
5. `price` (float): Unit retail sales price (must be positive).
6. `on_promo` (integer/boolean): Binary promotional flag (1 for active promotion, 0 otherwise).

### 9.3 Machine Learning Time Horizons
- **Planning Horizon**: Fixed at 28 days ahead.
- **Evaluation Splits**:
  - Test Window: The most recent 28 days of historical data are held out to measure unbiased forecast performance.
  - Validation Window: The 28 days immediately preceding the test window are used for early stopping during LightGBM training.
  - Training Set: All historical observations prior to the validation window.
- **Feature Lag Constraints**: All lag variables (e.g., lags at 28, 35, 42, 49, 56 days) and rolling window summaries are pre-shifted by at least 28 days, ensuring zero future information leaks into feature vectors.

---

## 10. External Integrations

### 10.1 Google OpenID Connect (OIDC) Single Sign-On
- **Standard**: OAuth 2.0 / OpenID Connect authorization code grant.
- **Flow**:
  1. The frontend initiates SSO by redirecting to the backend login trigger.
  2. The backend generates a cryptographically secure random state parameter, stores it in an HTTP-only state cookie, and redirects to Google's OAuth 2.0 endpoint.
  3. Upon user authorization, Google redirects to the frontend callback handler.
  4. The frontend transmits authorization code and state to the backend callback endpoint.
  5. The backend validates state integrity against the cookie, exchanges the authorization code for Google ID and access tokens, retrieves verified email identity, creates or matches the local user, and returns ShelfWise JWT tokens.
- **Configuration**: Managed via standard environment variables: client ID, client secret, issuer URL, and redirect URI.

### 10.2 Conversational AI Providers (Google Gemini & Anthropic Claude)
- **SDK & Protocol**: Official REST API clients supporting native function calling and structured tool definitions.
- **Tool Protocol**: The backend registers four function schemas with the model provider. When user intent necessitates retail telemetry, the model issues a tool call request. The backend executes the corresponding Python service locally and returns the structured JSON output to the model, which formulates the final grounded answer.
- **Rate Limit Resilience**: HTTP 429 rate limit responses trigger an automated sleep-and-retry sequence (capping backoff at 20 seconds, defaulting to 12 seconds) before falling back.
- **Offline Deterministic Fallback**: When external LLM API keys are unconfigured, expired, or rate-limited, ShelfWise automatically routes queries through an offline natural language parsing engine. This local engine matches intents (stockout inquiries, reorder queries, series trends, model accuracy questions) and returns formatted Markdown tables and summaries computed directly from database tables.

---

## 11. State Handling & Edge Cases

### 11.1 Loading States
- **Page Transitions**: Top-level route changes render lightweight spinners while React Query queries resolve.
- **Forecast Training**: When a user clicks "Run new forecast", the button disables, a spinner renders alongside "Training Pipeline...", and the latest run chip indicates active training until polling completes.
- **Inventory Updates**: Inline editing cells display mini spinners during PATCH operations; background table refreshes indicate active syncing via non-blocking status text.
- **AI Typing Indicator**: An animated typing bubble displays status notes ("Querying forecast data and generating recommendation...") while the assistant executes tool calls.

### 11.2 Empty States
- **No Datasets Uploaded**: Upload audit table renders an instructive note: *"No datasets uploaded yet. Upload your first sales CSV above."*
- **Filtered Alerts Return Zero Items**: Inventory table displays: *"No inventory items match your current filter criteria."* with clear guidance to reset filters.
- **Initial Assistant Conversation**: The Assistant page presents an illustrative hero card with four clickable prompt pills to guide users on available query types.

### 11.3 Error States
- **Pandera Schema Rejection**: Ingestion failures present a red alert card listing the count of errors and a scrollable monospace list detailing exact constraint violations.
- **Forecast Run Failures**: Interrupted or failed training runs render a red status chip ("Run #X · Failed") and display the error message in the toolbar.
- **Stale Run Recovery**: If a server restart interrupts an active forecast, the backend automatically transitions runs older than 10 minutes to "failed", preventing infinite frontend polling loops.
- **Network Failures**: API errors present dismissible alert banners with actionable error messages and retry guidance.

---

## 12. MVP Scope (Delivered Features)

The current release of ShelfWise includes the complete implementation of the following capabilities:
1. **Full Authentication System**: Email/password registration and login, JWT issuance and auto-refresh, Google OIDC single sign-on, and demo account quick-fill.
2. **Data Ingestion Engine**: Drag-and-drop CSV upload, strict Pandera schema validation, and dataset audit history.
3. **Machine Learning Pipeline**: 28-day LightGBM demand forecasting with zero feature leakage, empirical 80% prediction intervals, and automated benchmark scoring against Naive and Seasonal Naive models.
4. **Interactive Model Visualization**: Composed Recharts chart with prediction bands, actuals, forecast trajectories, cutoff line, and future projection tables.
5. **Replenishment Alert System**: Dynamic safety stock and reorder point calculations, days-of-cover tracking, four-tier status classification, suggested order volume calculations, and store/SKU filtering.
6. **Inline Inventory Editing**: Direct in-cell on-hand quantity editing with instant status recalculation.
7. **Executive Dashboard**: High-level portfolio metrics, aggregate actual vs. forecast chart, benchmark summary bar, and priority action table.
8. **Grounded AI Assistant**: Multi-turn conversational interface with native tool calling, rate limit backoff, and deterministic offline fallback.
9. **Responsive Desktop & Mobile Shell**: Persistent sidebar on desktop and off-canvas slide-out drawer on mobile viewports.
10. **Cloud Deployment Configuration**: Containerized Docker setup optimized for Render (backend) and Vercel (frontend), including automated CI testing via GitHub Actions.

---

## 13. Out-of-Scope Items & Non-Goals

The following capabilities are deliberately excluded from the current MVP release:
1. **Live POS Hardware Connectors**: No real-time webhooks or direct integrations with retail hardware (e.g., Square, Clover, Shopify POS, Lightspeed). All sales data enters via CSV upload or demo seeding.
2. **Multi-Tenancy & Per-Tenant Isolation**: No multi-tenant data partitioning or organization-based access controls. All authenticated users access a single shared operational instance.
3. **Dedicated Task Queues (Celery/Celery Beat)**: No distributed task queue or Redis-backed Celery worker pool. Background jobs (forecast training, demo loading) execute within lightweight Python daemon threads.
4. **Automated Scheduled Retraining**: No automated cron jobs or scheduled model retraining triggers. Forecast runs are triggered manually via user action or initial data seeding.
5. **Supplier Purchase Order Dispatch (EDI)**: No electronic data interchange (EDI) or direct transmission of purchase orders to external supplier systems. Suggested order quantities are advisory calculations for human review.
6. **Role-Based Access Control (RBAC)**: No fine-grained permissions (e.g., read-only viewer vs. store manager vs. administrator). All authenticated users possess equal system privileges.

---

## 14. Success Criteria & Benchmark Targets

### 14.1 Forecasting Accuracy Targets
- **WAPE Error Reduction**: LightGBM achieves an overall Weighted Absolute Percentage Error of **0.0884** (8.84%), significantly outperforming the best baseline (Seasonal Naive 28-day WAPE of **0.1030**), representing an error reduction of **14.2%**.
- **Portfolio-Wide Superiority**: LightGBM outperforms baseline models across at least **9 out of 10** individual store locations.
- **Unbiased Forecast Trajectory**: Forecast Bias remains centered near zero, ensuring the model does not systematically over-forecast or under-forecast demand.

### 14.2 Operational & Infrastructure Targets
- **Memory Footprint**: Backend container startup and background demo data ingestion consume less than **210 MiB** peak memory (verified at 201 MiB), comfortably within Render's 512 MB free tier memory boundary.
- **Rapid Port Binding**: Backend container binds Gunicorn to the listening port within **5 seconds** of launch, running data checks asynchronously to prevent cloud deployment health check timeouts.
- **Test Reliability**: The entire backend test suite (97 tests covering models, APIs, auth, seeders, and assistant logic) executes cleanly with zero failures.
- **Zero Frontend Build Errors**: The TypeScript and Vite production pipeline compiles with zero type errors.

---

## 15. Labelled Assumptions

1. **[ASSUMPTION-LEAD-TIME] Fixed Supplier Lead Times**: In the absence of an integrated supplier catalog, lead time is assumed to be deterministic and configured between 3 and 14 days per store/SKU during initial stock seeding.
2. **[ASSUMPTION-SERVICE-LEVEL] 95% Target Cycle Service Level**: The safety stock multiplier is hardcoded to 1.65 (corresponding to a one-tailed normal distribution for a 95% in-stock probability during lead time).
3. **[ASSUMPTION-OVERSTOCK-THRESHOLD] 21-Day Overstock Baseline**: Any inventory item whose on-hand quantity exceeds 21.0 days of projected demand is assumed to be in an "Overstock" condition.
4. **[ASSUMPTION-DETERMINISTIC-SEEDING] Seed Suffix 42**: When generating simulated stock levels and inventory variations, the random number generator is initialized with a deterministic seed suffix (42) to guarantee reproducible demo data distributions across container restarts.
5. **[ASSUMPTION-SINGLE-PROCESS-CONCURRENCY] Low Concurrent Worker Load**: Because forecast training runs in background threads within the Django process, the production server is assumed to run on a single Gunicorn worker with multiple threads, rather than multi-worker pre-forking, to prevent duplicate training collisions.
6. **[ASSUMPTION-OFFLINE-FALLBACK] Self-Contained Assistant Utility**: It is assumed that retail planners evaluate software in diverse environments where external LLM API credentials may not be immediately available; therefore, the deterministic offline assistant fallback is treated as a first-class feature rather than a degraded error state.

