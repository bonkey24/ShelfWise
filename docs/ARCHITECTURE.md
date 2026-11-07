# ShelfWise Architecture Documentation

## 1. System Overview & Architectural Purpose

ShelfWise is an end-to-end retail demand forecasting and inventory replenishment intelligence platform. It bridges the gap between historical transactional data and operational procurement by generating accurate 28-day-ahead demand forecasts and translating statistical predictions directly into actionable inventory reorder recommendations.

The architecture is built around three core architectural tenets:
1. **Decoupled Machine Learning Core**: The predictive modeling and statistical engine resides in an isolated, pure Python package with zero web framework dependencies. It interacts with data solely through standard tabular primitives (Pandas DataFrames) and plain Python types.
2. **Lean, Single-Tier Asynchronous Execution**: Computationally intensive model training and evaluation runs as isolated daemon threads within the application runtime, avoiding the operational overhead and memory footprint of an external worker cluster while maintaining an interactive, responsive web user interface.
3. **Resilient Production Footprint**: The application is designed for cloud-native deployment on containerized PaaS platforms (Render) and modern edge CDNs (Vercel), supporting automatic fallback mechanisms for external AI integrations and graceful cold-start handling.

---

## 2. Technology Stack & Architectural Decisions

The ShelfWise platform leverages a modern, cohesive stack chosen specifically for maintainability, strict typing, analytical efficiency, and operational simplicity.

| Layer | Technology | Version | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | Django / Django REST Framework (DRF) | 5.1+ / 3.15+ | Mature ORM with native transaction management, comprehensive security controls, robust relational modeling, and predictable RESTful API routing. |
| **Relational Database** | PostgreSQL | 16 | ACID-compliant transactional persistence, optimized indexing on composite business keys (store ID, SKU, date), and seamless time-series queries. |
| **Data Validation** | Pandera | 0.20+ | Schema enforcement at runtime for tabular datasets, providing defensive boundary checks on ingested CSV files before persistence. |
| **Machine Learning Engine** | LightGBM | 4.5+ | High-performance gradient boosted decision trees with native categorical feature support, superior memory efficiency, fast training times, and deterministic predictions. |
| **Baseline Modeling & Evaluation** | Scikit-Learn | 1.6+ | Standardized metric computation, cross-evaluation pipelines, and tabular transformation utilities. |
| **Data Manipulation** | Pandas & NumPy | 2.2+ / 2.1+ | Vectorized tabular operations, temporal windowing, feature lags, and statistical variance modeling. |
| **Frontend Framework** | React | 19 | Declarative user interfaces, efficient component rendering, and seamless reconciliation of interactive data grids. |
| **Type Safety** | TypeScript | 5.7+ | Strict static typing across API contracts, domain entities, forecast payloads, and chart data structures. |
| **Build & Tooling** | Vite | 6.1+ | Near-instantaneous Hot Module Replacement (HMR) during local development and optimized, minified production assets. |
| **Styling Engine** | Tailwind CSS | 4.0 | Utility-first CSS engine enabling consistent tokenized color palettes, typography scales, responsive layouts, and zero runtime overhead. |
| **Client State & Cache** | TanStack Query (React Query) | 5.66+ | Declarative server-state caching, automatic background refetching, exponential polling during forecast generation, and optimistic cache invalidation. |
| **Client Routing** | React Router | 7.1+ | Client-side routing with deep link support, authentication guards, and fallback redirects. |
| **Data Visualization** | Recharts | 2.15+ | Responsive SVG-based charting for time-series projections, historical actuals, and confidence bands. |
| **Icons & Indicators** | Lucide React | 0.475+ | Clean, uniform icon system providing visual indicators for inventory statuses, navigation, and metrics. |
| **AI / LLM Integration** | Google Gemini (via google-genai) | 1.0+ | Advanced tool-calling capabilities allowing natural language queries to execute structured database queries against forecast and inventory metrics. |
| **HTTP Client** | Axios | 1.7+ | Predictable client-side HTTP communication with centralized interceptors for automatic JWT token rotation and error handling. |
| **Containerization** | Docker & Docker Compose | Multi-platform | Reproducible development and deployment environments encapsulating Python, system dependencies (libgomp), and service configurations. |
| **Production Hosting** | Render (Backend) / Vercel (Frontend) | Cloud PaaS / Edge CDN | Low-maintenance deployment topology combining containerized web services with edge-cached single-page application distribution. |

---

## 3. High-Level Component Diagram

The following text diagram details the runtime relationship between client interfaces, edge routing, application services, persistence tiers, and external third-party providers.

```
+-----------------------------------------------------------------------------------+
|                                   USER BROWSER                                    |
|                                                                                   |
|   +---------------------------------------------------------------------------+   |
|   |                       React 19 Single Page Application                     |   |
|   |  - Auth State (localStorage)         - TanStack Query Polling & Cache     |   |
|   |  - Route Guards & Pages              - Recharts Visualizations            |   |
|   |  - Axios Interceptors (JWT Refresh)  - Assistant Chat UI                  |   |
|   +---------------------------------------------------------------------------+   |
+--------------------------+------------------------------------+-------------------+
                           | Static Assets & SPA Routing        | REST API Calls &
                           | (HTTPS)                            | Auth Requests (HTTPS)
                           v                                    v
            +------------------------------+     +-------------------------------+
            |        VERCEL EDGE CDN       |     |      RENDER DOCKER SERVICE    |
            |                              |     |                               |
            | - Edge CDN Asset Delivery    |     | - Single Gunicorn Process     |
            | - vercel.json SPA Rewrite    |     |   (1 Worker, 4 Sync Threads)  |
            | - Fallback to /index.html    |     | - Dynamic PORT Binding        |
            +------------------------------+     | - Django 5.1 / DRF Layer      |
                                                 | - SECURE_PROXY_SSL_HEADER     |
                                                 +---------------+---------------+
                                                                 |
                                +--------------------------------+-------------------------------+
                                |                                |                               |
                                v                                v                               v
                +-------------------------------+ +-----------------------------+ +-----------------------------+
                |     POSTGRESQL 16 (RENDER)    | |    IN-PROCESS THREAD RUNNER | |  EXTERNAL API INTEGRATIONS  |
                |                               | |                             | |                             |
                | - User & Token Records        | | - Background Forecast Thread| | - Google OIDC Endpoints     |
                | - Historical Sales (CSV Data) | | - Stale Run Timeout Checker | |   (OAuth Token & Profile)   |
                | - Forecast Runs & Metadata    | | - Non-blocking In-Memory    | | - Google Gemini API         |
                | - Model Metric Benchmarks     | |   Execution                 | |   (Tool-Calling Assistant)  |
                | - Daily Forecast Values       | +--------------+--------------+ +-----------------------------+
                | - Inventory Alert Overrides   |                |
                +-------------------------------+                | Dispatches DataFrames
                                                                 v
                                                +-------------------------------+
                                                |     PURE FORECASTING ENGINE   |
                                                |    (backend/forecasting/)     |
                                                |                               |
                                                | - Zero Django Imports         |
                                                | - Feature Engineering (>=28d) |
                                                | - 3-Way Sequential Split      |
                                                | - Naive & Seasonal Baselines  |
                                                | - LightGBM Regressor          |
                                                | - Empirical Residual Bands    |
                                                | - Inventory Safety Formulas   |
                                                +-------------------------------+
```

---

## 4. Repository & Folder Structure

The repository is organized cleanly by architectural tier. The web backend, decoupled forecasting package, frontend application, deployment definitions, and automated test suites are partitioned into dedicated hierarchies.

```
ShelfWise/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Dual-job CI pipeline (Postgres service, Python 3.13, Node 22)
├── backend/
│   ├── apps/
│   │   ├── accounts/              # User model, JWT authentication endpoints, Google OIDC flow
│   │   ├── assistant/             # Natural language chat, Gemini tool-calling engine, offline fallback
│   │   ├── datasets/              # Sales record storage, Pandera CSV validation, upload management
│   │   ├── forecasts/             # Forecast run lifecycle, DB serialization, background thread runner
│   │   └── inventory/             # Dynamic alert calculations, stock policies, user overrides
│   ├── core/
│   │   ├── asgi.py                # ASGI application entrypoint
│   │   ├── exceptions.py          # Unified DRF exception handler & standardized error envelopes
│   │   ├── settings.py            # Environment-driven Django configuration
│   │   ├── urls.py                # Root URL dispatcher and OpenAPI documentation routing
│   │   └── wsgi.py                # WSGI entrypoint for Gunicorn production server
│   ├── demo_data/
│   │   └── sample_sales.csv       # Container fallback dataset for automated demo seeding
│   ├── forecasting/               # PURE PYTHON MACHINE LEARNING PACKAGE (NO DJANGO IMPORTS)
│   │   ├── __init__.py            # Package exports
│   │   ├── baseline.py            # Naive (T-28) and Seasonal Naive (t-28) benchmark models
│   │   ├── features.py            # Calendar extraction, direct lag generation (>=28), shifted rolling stats
│   │   ├── inventory.py           # Safety stock, reorder point, days of cover, status classification
│   │   ├── metrics.py             # WAPE, Bias, RMSSE, and MAE calculation functions
│   │   ├── model.py               # LightGBM training wrapper with early stopping and prediction bands
│   │   ├── run_forecast.py        # Top-level orchestration pipeline accepting and returning DataFrames
│   │   ├── split.py               # Sequential temporal three-way train/validation/test splitter
│   │   └── tests/                 # Unit tests for the ML engine (including temporal leakage checks)
│   ├── Dockerfile                 # Multi-stage production container build with libgomp1
│   ├── docker-entrypoint.sh       # Container initialization (migrations, background demo load, Gunicorn)
│   ├── manage.py                  # Django administrative utility
│   ├── pytest.ini                 # Pytest configuration and database test environment setup
│   └── requirements.txt           # Python dependency manifest
├── data/
│   └── sample_sales.csv           # Local development source dataset (Rossmann store subset)
├── docs/
│   ├── ARCHITECTURE.md            # System architecture, data flow, and design specifications
│   ├── DESIGN.md                  # Design system tokens, UI layout specifications, component guidelines
│   └── PRD.md                     # Product requirements document, business domain, and scope
├── frontend/
│   ├── design-reference/          # UI mockups and UX reference specifications
│   ├── src/
│   │   ├── api/                   # Axios client instance, auth interceptors, and typed API services
│   │   ├── components/            # Reusable UI primitives (Button, Card, Input, MetricCard, TopBar)
│   │   ├── context/               # AuthContext providing session state and authentication hooks
│   │   ├── pages/                 # Route page components (Dashboard, Forecast, Inventory, Upload, Chat)
│   │   ├── App.tsx                # Client-side router definition and global query providers
│   │   ├── index.css              # Tailwind CSS v4 directives and design token variables
│   │   └── main.tsx               # Application bootstrap and DOM mounting
│   ├── package.json               # Frontend dependencies and npm scripts
│   ├── tsconfig.json              # TypeScript compilation rules
│   ├── vercel.json                # Single-page application URL rewrite configuration
│   └── vite.config.ts             # Vite bundler configuration and local dev server proxy
├── docker-compose.yml             # Local multi-service orchestration (Postgres, Redis, Backend, Frontend)
└── README.md                      # Project overview, setup guides, and operational documentation
```

---

## 5. Data Ingestion & Core Data Flows

### A. CSV Ingestion & Validation Flow

The dataset ingestion pipeline ensures that uploaded transactional records conform strictly to the required time-series schema before being written to PostgreSQL.

```
[ User Browser ]
       |
       | 1. POST /api/datasets/upload/ (multipart/form-data)
       v
[ Django Dataset View ]
       |
       | 2. Stream uploaded file into memory
       v
[ Pandera Ingestion Schema Validator ]
       |
       |-- Check required columns: Store, Date, Sales, Customers, Open, Promo, StateHoliday, SchoolHoliday
       |-- Verify data types: Integer store IDs, ISO-8601 dates, non-negative numeric sales/customers
       |-- Validate categorical constraints: Open (0/1), Promo (0/1), StateHoliday strings
       |
       +---> [ Validation Error ]: Immediate HTTP 400 Bad Request with column-level error breakdown
       |
       v (Validation Succeeded)
[ Bulk Database Ingestion ]
       |
       | 3. Atomic database transaction:
       |    - Bulk insert or update Dataset records
       |    - Record historical SalesRecord rows indexed by (Store, Date)
       |    - Log dataset metadata (row count, min date, max date, file name)
       v
[ Database Persistence: PostgreSQL ]
       |
       v
[ HTTP 201 Response with Dataset Summary to Browser ]
```

### B. Forecast Training & Run Flow

Training and projection execution occurs asynchronously in a dedicated Python daemon thread. The web client receives an immediate acknowledgment and polls the backend until computation is complete.

```
[ User Browser ]
       |
       | 1. POST /api/forecasts/run/
       v
[ Django Forecast View ]
       |
       | 2. Check for active runs (status = "running" and started within last 10 minutes)
       |    - If active run exists: Return HTTP 409 Conflict
       | 3. Create ForecastRun database record (status = "pending")
       | 4. Spawn background daemon thread (forecast_runner_thread)
       | 5. Return HTTP 202 Accepted (run_id, status = "pending")
       v
[ Background Daemon Thread ]
       |
       | 6. Update ForecastRun status to "running"
       | 7. Query historical SalesRecord rows from PostgreSQL ordered by Date
       | 8. Convert QuerySet into pure Pandas DataFrame
       | 9. Invoke forecasting.run_forecast.generate_forecast(df):
       |    |-- Temporal Split: Train (earliest to T-56), Val (T-56 to T-28), Test (T-28 to T)
       |    |-- Generate direct lag features (>= 28 days) and shifted rolling statistics
       |    |-- Train LightGBM model with early stopping on validation split
       |    |-- Evaluate holdout test window against Naive and Seasonal Naive baselines
       |    |-- Compute WAPE, Bias, RMSSE, and MAE benchmarks
       |    |-- Calculate empirical 80% prediction interval from test residual distribution
       |    \-- Project future 28 days for each active Store/SKU series
       | 10. Receive structured results dictionary (DataFrames + Metric Dictionaries)
       | 11. Atomic database write:
       |     - Bulk insert ForecastValue rows (predicted mean, lower 80%, upper 80%)
       |     - Update ForecastRun with metrics JSON and status = "done"
       |     (If exception occurs: update status = "failed" with captured error message)
       v
[ Database Persistence: PostgreSQL ]
       ^
       | 12. GET /api/forecasts/latest/ or GET /api/forecasts/{id}/status/
       |     (Client polls every 2 seconds via TanStack Query)
       |
[ User Browser Updates UI upon status = "done" ]
```

### C. Dynamic Inventory Alerts Flow

Inventory recommendations and replenishment alerts are calculated dynamically on demand using the active forecast run and current stock positions.

```
[ User Browser ]
       |
       | 1. GET /api/inventory/alerts/ (or /summary/)
       v
[ Django Inventory View ]
       |
       | 2. Query latest successful ForecastRun (status = "done")
       | 3. Query all SKU/Store combinations with current inventory balances and lead times
       | 4. Fetch 28-day daily forecast values and model residuals for active series
       v
[ Inventory Computation Engine ]
       |
       | 5. For each inventory series:
       |    - Calculate average daily projected demand
       |    - Determine lead-time demand over configured vendor lead time (default: 7 days)
       |    - Compute daily demand forecast standard deviation (sigma_daily)
       |    - Calculate safety stock using the normal service factor (Z = 1.65 for 95% service level)
       |    - Compute Reorder Point = Lead Time Demand + Safety Stock
       |    - Calculate Days of Cover = On Hand / Average Daily Demand
       |    - Evaluate Stock Status:
       |         * Stockout Risk: On Hand <= Safety Stock
       |         * Reorder Now: On Hand <= Reorder Point (and > Safety Stock)
       |         * Overstock: Days of Cover > 45 days
       |         * Healthy (OK): On Hand > Reorder Point and Days of Cover <= 45 days
       |    - Calculate Suggested Order Quantity = max(0, Reorder Point - On Hand)
       v
[ Django REST Framework Serializer ]
       |
       | 6. Format JSON payload with urgency sorting (Stockout Risk first)
       v
[ HTTP 200 OK Response with Enriched Alert Objects ]
```

---

## 6. Decoupled Forecasting Module (`backend/forecasting/`)

The machine learning engine in `backend/forecasting/` enforces a strict architectural boundary: **it contains zero imports of Django, DRF, or web framework components.**

### Pure Python & Tabular Contract
- **Input Contract**: The module accepts exclusively standard Pandas DataFrames, standard NumPy arrays, and native Python scalars (integers, floats, dictionaries).
- **Output Contract**: The module returns clean Python dictionaries containing native data structures, scalar performance metrics, and Pandas DataFrames representing future projections and confidence intervals.
- **Independence**: The entire directory can be extracted, packaged as an independent wheel, or run in standalone command-line scripts without Django installed or configured.

### Translation Layer
Django acts purely as a data ingestion, query serialization, and persistence boundary:
- `apps.forecasts.services`: Queries historical ORM models, formats database rows into a standardized Pandas DataFrame, and passes it to `forecasting.run_forecast`.
- `apps.forecasts.services`: Receives output DataFrames from the forecasting engine and deserializes them into `ForecastValue` and `ForecastRun` database models.
- `apps.inventory.services`: Bridges stock models and forecast time-series into the pure math functions in `forecasting.inventory`.

### Isolated Verification
Because the forecasting package is decoupled from the web runtime, its test suite (`backend/forecasting/tests/`) executes rapidly without initializing a database or spinning up the Django settings registry.

---

## 7. Forecasting & Inventory Engine Design

### A. 28-Day-Ahead Direct Multi-Step Planning Horizon
ShelfWise is built specifically for retail replenishment, where purchase orders must be placed well in advance of delivery. A standard recursive one-day-ahead model propagates compounding forecast errors over a 28-day lead period. 

To resolve this, ShelfWise implements a **direct multi-step planning horizon**:
- All feature engineering enforces a minimum lag of **28 days** (`lag >= 28`).
- At forecast execution time $T$, no feature uses any observation occurring after $T - 28$.
- All 28 future projection days ($T+1$ through $T+28$) are predicted directly in a single inference pass without recursive feedback loops or future ground-truth leakage.

### B. Strict Temporal Feature Engineering
Feature transformations are strictly backward-looking and pre-shifted:
- **Direct Lags**: Lags at 28, 35, 42, 49, and 56 days preserve weekly cyclic alignment while ensuring zero data from within the replenishment lead window is utilized.
- **Pre-Shifted Rolling Statistics**: Rolling 7-day and 28-day demand means and standard deviations are computed over series that are explicitly pre-shifted by 28 days.
- **Calendar & Exogenous Attributes**: Day of week, day of month, month, promotional indicator (Promo), state holiday classification, and school holiday indicators.
- **Categorical Encodings**: Store identifiers and SKU codes are mapped to categorical types, enabling LightGBM to build optimal split histograms directly.

### C. Three-Way Sequential Temporal Split
To avoid data leakage inherent in random k-fold cross validation on time-series data, the model uses an ordered, three-way temporal split:
1. **Training Set**: Earliest available historical observations up to $T - 56$.
2. **Validation Set**: Observations from $T - 56$ to $T - 28$, utilized exclusively for LightGBM early stopping to prevent gradient boosting over-fitting.
3. **Holdout Test Set**: The final 28 observed historical days ($T - 28$ to $T$), reserved strictly for final out-of-sample model evaluation against naive benchmarks.

### D. Benchmark Baselines
Every trained LightGBM model is evaluated against two standard reference baselines computed on the holdout test window:
- **Naive Baseline**: Carries forward the most recent known observation prior to the forecast window (observation at $T - 28$) across all 28 projection days.
- **Seasonal Naive Baseline**: Carries forward the corresponding day from the preceding 28-day seasonal cycle (repeating the pattern observed between $T - 56$ and $T - 28$).

### E. Model Metrics & Evaluation
Models are evaluated across four primary time-series metrics:
- **WAPE (Weighted Absolute Percentage Error)**: Aggregate absolute error normalized by total actual volume:
  $$\text{WAPE} = \frac{\sum |y_t - \hat{y}_t|}{\sum y_t}$$
- **Bias (Tracking Signal / Mean Error Ratio)**: Directional skew indicating systematic over-forecasting or under-forecasting:
  $$\text{Bias} = \frac{\sum (\hat{y}_t - y_t)}{\sum y_t}$$
- **RMSSE (Root Mean Squared Scaled Error)**: Scale-free metric comparing model RMSE to the in-sample seasonal naive baseline RMSE.
- **MAE (Mean Absolute Error)**: Average absolute magnitude of daily forecasting errors.

### F. LightGBM Configuration & Concurrency Control
- Model: `LGBMRegressor` optimizing Huber loss or mean squared error.
- Early Stopping: Configured with a patience of 20 rounds evaluated against the validation split.
- Concurrency Control: LightGBM OpenMP thread usage is constrained via the `LIGHTGBM_NUM_THREADS` environment variable (default: 2 threads) to prevent CPU core starvation and thread contention in containerized environments.

### G. Empirical Prediction Intervals
Instead of assuming a normal Gaussian error distribution, ShelfWise computes **empirical prediction intervals**:
- Residuals ($e_t = y_t - \hat{y}_t$) are computed across all series in the holdout test window.
- The 10th percentile residual ($q_{0.10}$) and 90th percentile residual ($q_{0.90}$) are extracted from the empirical error distribution.
- For future projections, the 80% confidence corridor is defined as:
  $$\text{Lower Band}_t = \max(0, \hat{y}_t + q_{0.10})$$
  $$\text{Upper Band}_t = \max(0, \hat{y}_t + q_{0.90})$$
This guarantees realistic, asymmetric uncertainty bounds that accurately reflect real-world retail demand volatility.

### H. Inventory Replenishment & Safety Stock Formulas
The inventory subsystem translates statistical demand forecasts into procurement decisions using standard stochastic inventory theory:
- **Forecast Daily Demand ($\bar{d}$)**: Mean daily forecast over the 28-day horizon.
- **Lead Time Demand ($\text{LTD}$)**: Projected demand accumulated over the vendor lead time (default: $L = 7\text{ days}$):
  $$\text{LTD} = \bar{d} \times L$$
- **Daily Demand Volatility ($\sigma_{\text{daily}}$)**: Standard deviation of forecast residuals on the holdout test window.
- **Safety Stock ($\text{SS}$)**: Buffer stock protecting against demand variation during lead time at a 95% cycle service level ($Z = 1.65$):
  $$\text{SS} = \text{round}\left(1.65 \times \sigma_{\text{daily}} \times \sqrt{L}\right)$$
- **Reorder Point ($\text{ROP}$)**: The inventory threshold triggering a replenishment order:
  $$\text{ROP} = \text{round}\left(\text{LTD} + \text{SS}\right)$$
- **Days of Cover**: Realized runway of current on-hand stock:
  $$\text{Days of Cover} = \text{round}\left(\frac{\text{On Hand}}{\bar{d}}, 1\right)$$
- **Suggested Order Quantity**:
  $$\text{Suggested Order} = \max(0, \text{ROP} - \text{On Hand})$$

#### Inventory Health Classifications
1. **Stockout Risk** (`critical` / red): $\text{On Hand} \le \text{Safety Stock}$ (urgent stock depletion imminent).
2. **Reorder Now** (`warning` / orange): $\text{On Hand} \le \text{ROP}$ and $\text{On Hand} > \text{Safety Stock}$ (procurement required to protect buffer).
3. **Overstock** (`info` / purple): $\text{Days of Cover} > 45\text{ days}$ (excess working capital locked in inventory).
4. **Healthy** (`success` / green): $\text{On Hand} > \text{ROP}$ and $\text{Days of Cover} \le 45\text{ days}$.

---

## 8. Authentication & Authorization Architecture

ShelfWise supports dual authentication methods: traditional email/password credentials and federated Google Single Sign-On via OpenID Connect (OIDC).

### A. JWT Token Lifecycle & Interceptor Rotation
1. **Authentication**: Users submit credentials to `/api/auth/login/` and receive a short-lived HMAC-signed JWT access token (valid for 15 minutes) and a long-lived refresh token (valid for 7 days).
2. **Client Persistence**: Tokens are stored in browser `localStorage`.
3. **Authorization Header**: Outgoing requests include the Bearer token:
   `Authorization: Bearer <access_token>`
4. **Automatic Silent Refresh**: The Axios client interceptor intercepts any HTTP 401 Unauthorized response, pauses queued requests, dispatches a refresh request to `/api/auth/token/refresh/`, updates `localStorage`, and retries the original request with the fresh token.
5. **Token Revocation**: Refresh tokens are blacklisted upon explicit user sign-out or token rotation.

### B. Hand-Written Google OIDC Flow
The application implements the standard OAuth 2.0 / OpenID Connect authorization code grant without bloated external client libraries:
1. **Authorization Initiation**: Browser initiates authentication via `/api/auth/google/url/`, receiving the configured Google consent URL embedded with client ID, required scopes (`openid`, `email`, `profile`), and a cryptographically secure random `state` parameter.
2. **State Verification Cookie**: The backend sets an `HttpOnly`, `SameSite=Lax` cookie storing the hashed state token to prevent Cross-Site Request Forgery (CSRF).
3. **Callback Processing**: Google redirects the user to the frontend callback route (`/auth/callback`), which forwards the `code` and `state` parameters to `/api/auth/google/callback/`.
4. **Validation & Token Exchange**:
   - The backend validates the callback `state` against the signed cookie.
   - The backend makes a direct server-to-server POST to Google's token endpoint (`https://oauth2.googleapis.com/token`) exchanging the authorization code for an ID token and access token.
   - The backend retrieves user identity from Google's userinfo endpoint (`https://openidconnect.googleapis.com/v1/userinfo`).
5. **User Provisioning & Issuance**: The backend retrieves or auto-provisions the user account in PostgreSQL and returns standard ShelfWise JWT access and refresh tokens.

### C. Access Control Model
- Single authenticated role: Any authenticated user has full access to view, upload, trigger forecasts, and adjust inventory settings.
- No multi-tenant data partitioning: All authenticated users share the common dataset and active forecast run.

---

## 9. Asynchronous Task Execution & Lifecycle

Rather than requiring an external worker process (such as Celery) and an intermediary broker (such as Redis or RabbitMQ) for the core forecast pipeline, ShelfWise executes long-running training routines within **in-process Python daemon threads**.

### A. Execution Mechanism
- When a forecast run is initiated via `POST /api/forecasts/run/`, the request thread validates constraints, writes an initial database record (`status = "pending"`), and spawns a daemon `threading.Thread`.
- The HTTP response (`202 Accepted`) returns immediately with the job identifier.
- The thread runs in the background of the Gunicorn web process, updating the database record to `status = "running"`, executing the forecasting pipeline, and finally writing `status = "done"` with metrics or `status = "failed"` on unhandled exceptions.

### B. Concurrency Guard & Stale Run Cleanup
To protect server resources and maintain consistency:
1. **Single Active Run Enforcement**: Before launching a thread, the view inspects the database for existing runs with `status = "running"`. If one exists and was started within the last 10 minutes, the request is rejected with HTTP 409 Conflict.
2. **Stale Run Auto-Recovery**: Any historical run lingering in `status = "running"` for longer than 10 minutes (indicating the host process was restarted or killed during computation) is automatically marked as `status = "failed"` with an error message indicating execution timeout.
3. **Process Restart Resilience**: When the Docker container or Gunicorn process initializes, stale runs are reconciled before accepting traffic.

---

## 10. AI Assistant & Tool-Calling Architecture

The ShelfWise Assistant provides a natural-language interface allowing store managers to interrogate forecasting performance, review stockouts, and analyze replenishment recommendations.

### A. Multi-Turn Conversation Protocol
- Client communicates with `/api/assistant/chat/` sending conversational message arrays.
- The backend coordinates with Google Gemini (`google-genai` SDK) using structured function declarations.

### B. Read-Only Tool Contracts
The LLM does not execute arbitrary database queries. It has access exclusively to four secure, deterministic, read-only Python tool functions:
1. `get_model_metrics`: Returns WAPE, bias, RMSSE, and baseline comparisons for the active forecast run.
2. `get_inventory_summary`: Returns global inventory health counts (stockout risk count, reorder count, healthy count, overstock count).
3. `get_alerts`: Returns filtered lists of active inventory alerts categorized by severity level.
4. `get_series_forecast`: Returns 28-day daily forecast values and empirical prediction bands for a specified store and SKU.

### C. Tool Execution Loop
1. User prompt and conversation history are dispatched to Gemini along with tool declarations.
2. Gemini returns a response requesting execution of one or more tool calls.
3. The backend executes the corresponding Python service functions against PostgreSQL, formats the results into structured JSON, and returns the tool output to Gemini.
4. Gemini synthesizes the structured data into an actionable, conversational markdown response.

### D. Offline Fallback & Rate Limit Resilience
To guarantee system availability in environments with missing API keys, network isolation, or API rate limits:
- **Rate Limit Backoff**: When external LLM calls encounter HTTP 429 (Too Many Requests), the assistant implements exponential backoff with jitter (up to 20 seconds).
- **Deterministic Offline Fallback**: If the `GEMINI_API_KEY` is unset, or if API calls fail after retry attempts, the assistant automatically switches to a deterministic pattern-matching fallback engine. The offline engine detects keywords (e.g., "metric", "accuracy", "wape", "alert", "stockout", "reorder", "forecast") and directly invokes the read-only tool services, returning formatted operational answers without external network dependencies.

---

## 11. Environment Configuration

All operational configuration is managed strictly through environment variables. Zero hardcoded secrets, database credentials, or API keys are committed to the repository.

| Environment Variable | Description & Default Value |
| :--- | :--- |
| `DEBUG` | Boolean flag enabling debug mode (`False` in production). |
| `SECRET_KEY` / `DJANGO_SECRET_KEY` | Cryptographic secret for signing Django sessions, cookies, and tokens. |
| `ALLOWED_HOSTS` | Comma-separated list of hostnames authorized to reach the application. |
| `DB_NAME` | PostgreSQL database name (default: `shelfwise`). |
| `DB_USER` | PostgreSQL database username (default: `shelfwise`). |
| `DB_PASSWORD` | PostgreSQL database user password. |
| `DB_HOST` | PostgreSQL host address (e.g., `localhost` or cloud internal host). |
| `DB_PORT` | PostgreSQL port (default: `5432` or local development `5433`). |
| `PORT` | Container network port binding (default: `8000`). |
| `FRONTEND_URL` | Base URL of the deployed frontend for CORS and CSRF authorization. |
| `EXTRA_ALLOWED_ORIGINS` | Optional comma-separated origins for preview or staging environments. |
| `CORS_ALLOWED_ORIGINS` | Origins permitted to make cross-origin HTTP requests. |
| `CSRF_TRUSTED_ORIGINS` | Origins trusted for safe state-changing requests. |
| `SECURE_PROXY_SSL_HEADER` | Header indicating SSL termination behind reverse proxy (`HTTP_X_FORWARDED_PROTO, https`). |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client identifier for Google Single Sign-On. |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret for Google Single Sign-On. |
| `GOOGLE_REDIRECT_URI` | Frontend callback endpoint for Google OIDC redirection. |
| `GEMINI_API_KEY` | Google Gemini API key for natural language assistant tool-calling. |
| `LIGHTGBM_NUM_THREADS` | Maximum OpenMP thread pool allocation for LightGBM (default: `2`). |
| `DEMO_DATA_PATH` | Explicit filesystem path for container initialization demo dataset. |

---

## 12. Error Handling & Fault Tolerance

ShelfWise employs defensive error-handling patterns across all system layers:

### A. Centralized API Exception Envelopes
All DRF views route unhandled exceptions through a custom exception handler (`backend/core/exceptions.py`):
- Guarantees uniform JSON error envelopes: `{"error": "<human_readable_message>", "code": "<status_slug>", "details": {...}}`.
- Converts Pandera `SchemaError` exceptions into clean HTTP 400 Bad Request responses with detailed field-level validation reports.
- Maps database integrity conflicts to HTTP 409 Conflict.
- Logs unexpected internal server errors (HTTP 500) with full stack traces while masking internal infrastructure details from API clients.

### B. Machine Learning & Ingestion Safeguards
- **Schema Validation**: CSV uploads failing type, range, or missing-column checks are rejected prior to database insertion.
- **Empty Dataset Protections**: The forecasting pipeline validates that input DataFrames contain sufficient historical observations and unique series before initiating training.
- **Thread Exception Isolation**: Exceptions occurring inside the background forecasting thread are trapped, logged, and written to the `ForecastRun.error_message` column, ensuring the job status moves cleanly to `failed` rather than hanging indefinitely.

### C. Client-Side Error Boundaries & Query Retries
- TanStack Query is configured with smart retry logic (skipping retries on 4xx client errors while retrying transient 5xx network blunders).
- Dynamic error banners display actionable recovery guidance on network loss, upload rejection, or expired sessions.

---

## 13. Security Posture & Known Architectural Boundaries

### A. Current Security Controls
- **JWT Cryptographic Signing**: HS256-signed tokens with strict expiration windows.
- **CSRF Protection & OIDC State Verification**: Cryptographically random state tokens stored in `HttpOnly`, `SameSite=Lax` cookies during OAuth handshakes.
- **Input Sanitization & Parameterization**: Django ORM ensures all database queries use parameterized SQL, eliminating SQL injection risks.
- **Proxy SSL Header Trust**: Strict enforcement of `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` ensures redirects and secure cookies function correctly behind Render and cloud load balancers.

### B. Known Architectural Limitations
1. **Shared Multi-User Data Domain**: There is currently no per-user or per-organization data isolation. All authenticated users access and modify a single unified dataset and active forecast run.
2. **Client-Side Token Persistence**: Tokens are stored in browser `localStorage`. While standard for modern decoupled single-page applications, this requires strict Cross-Site Scripting (XSS) hygiene.
3. **Client-Side Logout**: Token invalidation relies on the client discarding stored tokens and notifying the blacklist endpoint; expired access tokens remain cryptographically valid until their 15-minute lifespan terminates.

---

## 14. Quality Assurance & Automated Testing Architecture

ShelfWise enforces rigorous automated testing covering data integrity, machine learning algorithms, API contracts, and absence of temporal data leakage.

### A. Test Suite Composition (97 Automated Tests)
The comprehensive test suite is partitioned into two distinct test domains:
1. **Web & Integration Tests (`backend/apps/*/tests/`)**:
   - Model persistence, schema validations, and cascade operations.
   - API endpoints, JWT authentication flows, and permission enforcements.
   - Pandera CSV dataset validation logic and ingestion handlers.
   - Dynamic inventory alert calculations and stock override actions.
   - Assistant tool routing and deterministic offline fallback responses.
2. **Decoupled Forecasting Tests (`backend/forecasting/tests/`)**:
   - Feature lag calculations and rolling statistical transformations.
   - Sequential three-way temporal splitting boundaries.
   - Naive and Seasonal Naive baseline projection mathematics.
   - LightGBM model training, early stopping validation, and residual interval extraction.
   - Metric computations (WAPE, Bias, RMSSE, MAE).

### B. Temporal Data Leakage Test Suite (`test_leakage.py`)
A critical requirement in time-series forecasting is verifying that future data does not contaminate training or inference features. The test suite includes dedicated leakage tests that:
- Inspect feature matrices to verify that every lag feature satisfies $\text{lag} \ge 28$.
- Confirm that rolling window calculations are strictly shifted by 28 days.
- Ensure that synthetic post-cutoff spikes introduced into test-window actuals have zero statistical effect on historical training feature values.

---

## 15. Containerization & Docker Architecture

The deployment architecture is fully containerized to ensure reproducibility across local development and production environments.

### A. Production Dockerfile
- **Base Image**: `python:3.13-slim` providing a lightweight Linux environment.
- **System Dependencies**: Installs `libgomp1` (OpenMP runtime library required by LightGBM) and `curl` for container health probes.
- **Layer Optimization**: Copies dependency definitions and installs wheels before copying application code to leverage Docker layer caching.
- **Container Assets**: Includes bundled demo dataset at `/app/demo_data/sample_sales.csv`.

### B. Entrypoint Script (`docker-entrypoint.sh`)
The container entrypoint handles lifecycle initialization sequentially:
1. **Database Migration**: Executes `python manage.py migrate --noinput` synchronously.
2. **Background Demo Seeding**: Spawns an asynchronous background process executing `python manage.py load_demo_data` (looking sequentially at `DEMO_DATA_PATH`, `/data/sample_sales.csv`, and `/app/demo_data/sample_sales.csv`). This prevents database seeding from blocking port binding.
3. **Process Execution**: Replaces the shell process with `exec gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4 --timeout 120`.

### C. Docker Compose Architecture
- **Base Services**: PostgreSQL 16 (exposed locally on port 5433) and Redis 7 (port 6379).
- **Profile "app"**: Orchestrates the containerized backend web service and Vite frontend client for full-stack local integration testing.

---

## 16. Continuous Integration (CI) Pipeline

Automated continuous integration is executed via GitHub Actions (`.github/workflows/ci.yml`) on every push and pull request to the `main` branch.

```
                    GITHUB ACTIONS CI PIPELINE
                                |
        +-----------------------+-----------------------+
        |                                               |
        v                                               v
[ BACKEND CI JOB ]                              [ FRONTEND CI JOB ]
- Runner: ubuntu-latest                         - Runner: ubuntu-latest
- Service: PostgreSQL 16                        - Setup: Node.js 22
  (Health check: pg_isready)                    - Cache: npm dependencies (~/.npm)
- Setup: Python 3.13                            - Execution:
- System: sudo apt-get install -y libgomp1        1. npm ci (in frontend/)
- Cache: pip dependencies (~/.cache/pip)          2. npm run build (in frontend/)
- Execution:                                      (Ensures TypeScript typecheck
  1. pip install -r backend/requirements.txt       and Vite minification pass)
  2. pytest backend (97 tests pass)
```

---

## 17. Production Deployment Topology

The production architecture is deployed across specialized cloud infrastructure:

```
[ User Traffic ]
       |
       +---> [ https://shelf-wise-seven.vercel.app ] ----> Vercel Edge CDN (Vite SPA)
       |
       \---> [ https://shelfwise-2aol.onrender.com ] ----> Render Docker Web Service (Django)
                                                                    |
                                                                    v
                                                           Render Managed PostgreSQL
```

### A. Frontend on Vercel
- Hosted as a high-performance Single Page Application on Vercel Edge CDN.
- Configured with `vercel.json` rewrites (`{"source": "/(.*)", "destination": "/index.html"}`), allowing direct navigation and browser reloads on deep client routes (e.g., `/forecast`, `/inventory`, `/upload`).

### B. Backend on Render
- Deployed as a Docker web service using the root directory `backend`.
- Bound dynamically to the platform-provided network port via `${PORT:-8000}`.
- Configured with `SECURE_PROXY_SSL_HEADER` to terminate SSL securely at the cloud load balancer.
- Backed by a managed Render PostgreSQL 16 instance.

### C. Cold-Start Mitigation & Operational Characteristics
- On free-tier cloud instances, the backend web service spins down after periods of inactivity.
- Initial cold-start requests may experience a 50-60 second spin-up latency.
- The React application displays informational status banners during cold starts and retries initial handshakes automatically.

---

## 18. Future Scalability & Architecture Evolution

While the current single-tier architecture is optimized for low operational complexity and cost efficiency, the system is designed to evolve cleanly as data scale and concurrent tenant demands increase:

```
+-----------------------------------------------------------------------------------+
|                        FUTURE TARGET PRODUCTION ARCHITECTURE                      |
|                                                                                   |
|  +--------------------+        +--------------------+        +-----------------+  |
|  |  React Frontend    |        |  Django API Web    |        | Redis Broker &  |  |
|  |  (Vercel Edge CDN) | -----> |  (Multi-Worker)    | -----> | Result Backend  |  |
|  +--------------------+        +--------------------+        +--------+--------+  |
|                                                                       |           |
|                                +--------------------------------------+           |
|                                v                                                  |
|                    +-----------------------+                                      |
|                    | Celery Worker Cluster |                                      |
|                    | (Distributed Workers) |                                      |
|                    +-----------+-----------+                                      |
|                                |                                                  |
|        +-----------------------+-----------------------+                          |
|        v                                               v                          |
|  +---------------------------+                   +-----------------------------+  |
|  | PostgreSQL 16 Database    |                   | Model Registry & S3 Storage |  |
|  | (Row-Level Tenant Schema) |                   | (Serialized LightGBM Models)|  |
|  +---------------------------+                   +-----------------------------+  |
+-----------------------------------------------------------------------------------+
```

### Roadmap Initiatives
1. **Distributed Task Queue (Celery + Redis)**:
   - Transition long-running forecast jobs from local daemon threads to a distributed Celery worker pool.
   - Utilize Redis as a reliable message broker and result backend, supporting horizontal scaling of compute workers independently from web API workers.
2. **Scheduled Automated Retraining**:
   - Introduce scheduled Celery Beat crons to trigger periodic model retraining and metric benchmarking upon new sales data ingestion.
3. **Multi-Tenant Data Partitioning**:
   - Implement organization-level tenant keys across datasets, forecasts, and inventory models, providing strict row-level security and isolated forecasting workspaces.
4. **Model Drift Monitoring & Feature Re-evaluation**:
   - Establish automated tracking of WAPE, bias, and residual distributions over time to detect concept drift and trigger automated alerts when model accuracy degrades.
5. **Model Registry & Asset Storage**:
   - Persist serialized model binaries (`booster_.txt` or ONNX format) to cloud object storage (e.g., AWS S3 or Google Cloud Storage) to enable instant inference and historical model version rollbacks.

