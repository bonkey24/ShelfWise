# ShelfWise API Specification

## 1. Overview & Architectural Principles

The ShelfWise API is a RESTful interface built with Django 5.1 and Django REST Framework (DRF). It exposes endpoints for user authentication, sales dataset ingestion, store and product catalog management, asynchronous demand forecasting, stochastic inventory replenishment alerts, and conversational natural-language assistance.

- **Base URL**: `https://shelfwise-2aol.onrender.com` (Production) / `http://localhost:8000` (Local)
- **API Prefix**: `/api/`
- **Data Format**: `application/json` (except `/api/datasets/upload/` which accepts `multipart/form-data`)
- **Interactive Documentation**: Interactive Swagger UI is available at `/api/docs/`, powered by the OpenAPI 3.0.3 schema at `/api/schema/`.

---

## 2. Authentication & Authorization Model

### Authentication Scheme
Authentication uses JSON Web Tokens (JWT) adhering to RFC 7519 via `rest_framework_simplejwt`:
- **Access Tokens**: Short-lived (valid for 30 minutes), transmitted via the HTTP `Authorization` header:
  ```http
  Authorization: Bearer <access_token>
  ```
- **Refresh Tokens**: Long-lived (valid for 7 days), submitted to `/api/auth/refresh/` to obtain a new access token without re-entering credentials.
- **Default Permissions**: All endpoints require `IsAuthenticated` by default unless explicitly documented as `AllowAny` (public).

### Authorization & Tenancy
- **Shared Data Domain**: ShelfWise implements a single-tenant shared domain. All datasets, retail stores, products, historical sales, forecast runs, and inventory records are accessible to any authenticated user.
- **Role Model**: There is a single authenticated role. Any user with a valid JWT access token possesses full read and write permissions across all domain resources.

---

## 3. Global Error Handling & Response Formats

The API returns standard HTTP status codes alongside structured JSON error responses.

### A. Field Validation Errors (HTTP 400 Bad Request)
Returned when payload fields fail validation. Response maps field names to error messages:
```json
{
  "email": [
    "Enter a valid email address."
  ],
  "password": [
    "This field may not be blank."
  ]
}
```

### B. General & Authentication Errors (HTTP 401 / 403 / 404)
Returned when credentials are invalid, access is forbidden, or a requested resource is missing:
```json
{
  "detail": "Invalid email or password."
}
```

### C. Rate Limit Throttling (HTTP 429 Too Many Requests)
Returned when the conversational assistant rate limit (20 requests per minute) is exceeded:
```json
{
  "detail": "Request was throttled. Expected available in 42 seconds."
}
```

---

## 4. Authentication Endpoints (`/api/auth/`)

### Register User
- **Method & Path**: `POST /api/auth/register/`
- **Purpose**: Creates a new user account with email and password, initializes a linked user profile, and immediately issues JWT access and refresh tokens.
- **Authentication**: Public (`AllowAny`)
- **Request Body**:
  ```json
  {
    "email": "retailer@example.com",
    "password": "StrongPassword123!",
    "name": "Jane Storeowner"
  }
  ```
- **Validation Rules**:
  - `email`: Required, valid email format, must be unique in `auth_user`.
  - `password`: Required, minimum 1 character (standard Django password validation rules apply).
  - `name`: Optional string (stored in `first_name`).
- **Response (HTTP 201 Created)**:
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 2,
      "email": "retailer@example.com",
      "name": "Jane Storeowner",
      "auth_provider": "email"
    }
  }
  ```

---

### User Login
- **Method & Path**: `POST /api/auth/login/`
- **Purpose**: Authenticates email and password credentials, returning JWT access and refresh tokens alongside user profile metadata.
- **Authentication**: Public (`AllowAny`)
- **Request Body**:
  ```json
  {
    "email": "retailer@example.com",
    "password": "StrongPassword123!"
  }
  ```
- **Response (HTTP 200 OK)**:
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 2,
      "email": "retailer@example.com",
      "name": "Jane Storeowner",
      "auth_provider": "email"
    }
  }
  ```
- **Error (HTTP 401 Unauthorized)**:
  ```json
  {
    "detail": "Invalid email or password."
  }
  ```

---

### Refresh Token
- **Method & Path**: `POST /api/auth/refresh/`
- **Purpose**: Exchanges a valid unexpired refresh token for a new access token.
- **Authentication**: Public (`AllowAny`)
- **Request Body**:
  ```json
  {
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Response (HTTP 200 OK)**:
  ```json
  {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Error (HTTP 401 Unauthorized)**:
  ```json
  {
    "detail": "Token is invalid or expired",
    "code": "token_not_valid"
  }
  ```

---

### Current User Profile
- **Method & Path**: `GET /api/auth/me/`
- **Purpose**: Retrieves the account profile and identity provider metadata of the currently authenticated session.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Response (HTTP 200 OK)**:
  ```json
  {
    "id": 2,
    "email": "retailer@example.com",
    "name": "Jane Storeowner",
    "auth_provider": "email"
  }
  ```

---

### SSO Configuration Status
- **Method & Path**: `GET /api/auth/sso/config/`
- **Purpose**: Informs the frontend client whether Google OpenID Connect (OIDC) Single Sign-On is configured and available.
- **Authentication**: Public (`AllowAny`)
- **Response (HTTP 200 OK)**:
  ```json
  {
    "enabled": false,
    "login_url": "/api/auth/sso/login/"
  }
  ```

---

### SSO Login Initiation
- **Method & Path**: `GET /api/auth/sso/login/`
- **Purpose**: Generates a cryptographically signed CSRF state token (10-minute validity) and issues an HTTP 302 redirect to the Google OIDC authorization consent endpoint.
- **Authentication**: Public (`AllowAny`)
- **Response (HTTP 302 Found)**:
  - Redirects browser to: `https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=...&redirect_uri=...&scope=openid+email+profile&state=...`
- **Error (HTTP 400 Bad Request)**:
  ```json
  {
    "detail": "SSO is not configured."
  }
  ```

---

### SSO Callback Handler
- **Method & Path**: `GET /api/auth/sso/callback/`
- **Purpose**: Handles identity provider redirection. Validates the state parameter against CSRF attacks, exchanges authorization code for provider tokens, retrieves verified profile claims, provisions or retrieves the Django user, sets `auth_provider = "sso"`, and issues ShelfWise JWT tokens.
- **Authentication**: Public (`AllowAny`)
- **Query Parameters**:
  - `code`: Authorization code from identity provider.
  - `state`: Signed CSRF state parameter.
- **Response**:
  - If `FRONTEND_URL` is set: Redirects browser (HTTP 302) to `{FRONTEND_URL}/auth/callback#access={access}&refresh={refresh}`.
  - If `FRONTEND_URL` is unset: Returns HTTP 200 JSON with access and refresh tokens:
    ```json
    {
      "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "user": {
        "id": 3,
        "email": "user@gmail.com",
        "name": "Google User",
        "auth_provider": "sso"
      }
    }
    ```

---

## 5. Datasets Endpoints (`/api/datasets/`)

### List Datasets
- **Method & Path**: `GET /api/datasets/`
- **Purpose**: Returns a list of all historical uploaded CSV datasets, ordered by creation date (newest first).
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Response (HTTP 200 OK)**:
  ```json
  [
    {
      "id": 1,
      "name": "sample_sales.csv",
      "file": "/media/uploads/sample_sales.csv",
      "rows_imported": 20000,
      "status": "success",
      "error": "",
      "created_at": "2026-11-02T12:00:00Z"
    }
  ]
  ```

---

### Upload Sales CSV Dataset
- **Method & Path**: `POST /api/datasets/upload/`
- **Purpose**: Ingests a transactional sales CSV file. Validates column schema, null constraints, and types using Pandera, then atomically inserts or updates Store, Product, and Sale records in PostgreSQL.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Content-Type**: `multipart/form-data`
- **Form Data Fields**:
  - `file`: CSV file (required).
  - `name`: Dataset display name (optional, defaults to uploaded filename).
- **Required CSV Columns & Constraints**:
  - `store`: Store identifier string (e.g., `S1097`).
  - `sku`: Product SKU identifier string (e.g., `P1`).
  - `date`: ISO-8601 calendar date (`YYYY-MM-DD`).
  - `units_sold`: Non-negative numeric sales volume.
  - `price`: Unit price numeric value (optional, nullable).
  - `on_promo`: Boolean indicator (`True`/`False` or `1`/`0`).
- **Response (HTTP 201 Created)**:
  ```json
  {
    "id": 2,
    "name": "rossmann_q3_sales.csv",
    "file": "/media/uploads/rossmann_q3_sales.csv",
    "rows_imported": 15420,
    "status": "success",
    "error": "",
    "created_at": "2026-11-07T14:30:00Z"
  }
  ```
- **Error (HTTP 400 Bad Request)**:
  ```json
  {
    "errors": [
      "Missing required columns: {'sku', 'date'}"
    ],
    "dataset": {
      "id": 3,
      "name": "invalid_data.csv",
      "file": "/media/uploads/invalid_data.csv",
      "rows_imported": 0,
      "status": "failed",
      "error": "Missing required columns: {'sku', 'date'}",
      "created_at": "2026-11-07T14:31:00Z"
    }
  }
  ```

---

## 6. Retail Catalog Endpoints (`/api/retail/`)

### List Stores
- **Method & Path**: `GET /api/retail/stores/`
- **Purpose**: Returns all registered retail store locations, ordered by store code.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Response (HTTP 200 OK)**:
  ```json
  [
    {
      "id": 1,
      "code": "S1097",
      "name": "Store #1097 (Main Street)"
    },
    {
      "id": 2,
      "code": "S2048",
      "name": "Store #2048 (Northside Branch)"
    }
  ]
  ```

---

### List Products
- **Method & Path**: `GET /api/retail/products/`
- **Purpose**: Returns all registered products in the merchandising catalog, ordered by SKU.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Response (HTTP 200 OK)**:
  ```json
  [
    {
      "id": 1,
      "sku": "P1",
      "name": "Product 1",
      "category": "Pharmacy"
    },
    {
      "id": 2,
      "sku": "P2",
      "name": "Product 2",
      "category": "Beauty & Care"
    }
  ]
  ```

---

## 7. Forecasting Endpoints (`/api/forecasts/`)

### Start Forecast Run
- **Method & Path**: `POST /api/forecasts/run/`
- **Purpose**: Spawns an asynchronous Python daemon thread that queries historical sales data, executes feature engineering (lags $\ge 28$ days), trains LightGBM with early stopping on validation data, benchmarks holdout metrics against naive baselines, and generates 28-day projections with 80% empirical prediction intervals.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Request Body**:
  ```json
  {
    "horizon_days": 28,
    "dataset_id": 1
  }
  ```
  *(Both fields optional; `horizon_days` defaults to 28; `dataset_id` defaults to latest dataset).*
- **Response (HTTP 202 Accepted)**:
  ```json
  {
    "id": 5,
    "status": "running",
    "horizon_days": 28,
    "dataset": 1,
    "metrics": {},
    "error": "",
    "created_at": "2026-11-07T16:00:00Z",
    "finished_at": null
  }
  ```

---

### List Forecast Runs
- **Method & Path**: `GET /api/forecasts/`
- **Purpose**: Retrieves all historical forecast runs ordered by creation date descending (`-created_at`). Automatically triggers stale-run recovery for any job remaining in `running` status for longer than 10 minutes.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Response (HTTP 200 OK)**:
  ```json
  [
    {
      "id": 5,
      "status": "done",
      "horizon_days": 28,
      "dataset": 1,
      "metrics": {
        "LightGBM": {
          "WAPE": 0.0884,
          "Bias": -0.012,
          "RMSSE": 0.84,
          "MAE": 42.1
        },
        "Seasonal Naive (28d)": {
          "WAPE": 0.1032,
          "Bias": 0.005,
          "RMSSE": 1.00,
          "MAE": 49.3
        },
        "Naive": {
          "WAPE": 0.2371,
          "Bias": -0.081,
          "RMSSE": 2.15,
          "MAE": 113.8
        }
      },
      "error": "",
      "created_at": "2026-11-07T16:00:00Z",
      "finished_at": "2026-11-07T16:01:14Z"
    }
  ]
  ```

---

### Get Forecast Run Details
- **Method & Path**: `GET /api/forecasts/{id}/`
- **Purpose**: Retrieves status, completion timestamp, evaluation metrics, and error information for a specific forecast run. Used by the client to poll during execution.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Path Parameters**:
  - `id`: Integer primary key of the `ForecastRun`.
- **Response (HTTP 200 OK)**:
  ```json
  {
    "id": 5,
    "status": "done",
    "horizon_days": 28,
    "dataset": 1,
    "metrics": {
      "LightGBM": {
        "WAPE": 0.0884,
        "Bias": -0.012,
        "RMSSE": 0.84,
        "MAE": 42.1
      }
    },
    "error": "",
    "created_at": "2026-11-07T16:00:00Z",
    "finished_at": "2026-11-07T16:01:14Z"
  }
  ```
- **Error (HTTP 404 Not Found)**:
  ```json
  {
    "detail": "No ForecastRun matches the given query."
  }
  ```

---

### Get Forecast Run Overview Time Series
- **Method & Path**: `GET /api/forecasts/{id}/overview/`
- **Purpose**: Returns portfolio-level aggregate time-series data summing actuals and forecasts across all stores and SKUs. Used to render the primary dashboard timeline comparison chart.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Path Parameters**:
  - `id`: Integer primary key of the `ForecastRun`.
- **Response (HTTP 200 OK)**:
  ```json
  {
    "run_id": 5,
    "status": "done",
    "metrics": {
      "LightGBM": { "WAPE": 0.0884, "Bias": -0.012, "RMSSE": 0.84 }
    },
    "first_future_date": "2026-11-08",
    "total_daily": [
      {
        "date": "2026-10-11",
        "forecast": 12450.0,
        "actual": 12890.0
      },
      {
        "date": "2026-11-08",
        "forecast": 13120.0,
        "actual": null
      }
    ],
    "dates": [
      "2026-10-11",
      "2026-11-08"
    ]
  }
  ```

---

### Get Forecast Run Series Results
- **Method & Path**: `GET /api/forecasts/{id}/results/`
- **Purpose**: Retrieves granular daily forecast points, 80% empirical confidence bounds (`lower`, `upper`), and holdout ground-truth actuals for specific store and SKU series.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Path Parameters**:
  - `id`: Integer primary key of the `ForecastRun`.
- **Query Parameters (Filtering)**:
  - `store`: Filter by store code (e.g., `?store=S1097`).
  - `sku`: Filter by product SKU (e.g., `?sku=P1`).
- **Response (HTTP 200 OK)**:
  ```json
  [
    {
      "id": 1420,
      "store": "S1097",
      "sku": "P1",
      "date": "2026-11-08",
      "forecast": 48.5,
      "lower": 38.2,
      "upper": 58.7,
      "actual": null
    }
  ]
  ```

---

## 8. Inventory Management Endpoints (`/api/inventory/`)

### Inventory Alerts
- **Method & Path**: `GET /api/inventory/alerts/`
- **Purpose**: Dynamically computes replenishment alerts, lead-time demand, safety stock, reorder point, days of cover, and suggested replenishment order quantities for store/SKU series based on a forecast run and current stock positions.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Query Parameters**:
  - `run`: Forecast run ID (optional; defaults to latest completed run).
  - `status`: Filter by risk classification: `stockout_risk`, `reorder_now`, `overstock`, or `ok`.
  - `store`: Filter by store code (e.g., `S1097`).
  - `limit`: Maximum count of returned records (pagination).
  - `offset`: Starting index offset (pagination).
- **Response (HTTP 200 OK)**:
  ```json
  [
    {
      "store": "S1097",
      "sku": "P1",
      "status": "stockout_risk",
      "on_hand": 18.0,
      "lead_time_days": 7,
      "days_of_cover": 2.1,
      "lead_time_demand": 60.0,
      "safety_stock": 25.0,
      "reorder_point": 85.0,
      "suggested_order_qty": 67.0
    },
    {
      "store": "S1097",
      "sku": "P2",
      "status": "reorder_now",
      "on_hand": 55.0,
      "lead_time_days": 5,
      "days_of_cover": 6.8,
      "lead_time_demand": 40.0,
      "safety_stock": 18.0,
      "reorder_point": 58.0,
      "suggested_order_qty": 3.0
    }
  ]
  ```

---

### Inventory Portfolio Summary
- **Method & Path**: `GET /api/inventory/summary/`
- **Purpose**: Returns aggregate inventory counts grouped by status, total suggested replenishment order units, and estimated excess units across the retail portfolio.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Query Parameters**:
  - `run`: Forecast run ID (optional; defaults to latest completed run).
- **Response (HTTP 200 OK)**:
  ```json
  {
    "run_id": 5,
    "counts": {
      "stockout_risk": 4,
      "reorder_now": 3,
      "ok": 8,
      "overstock": 5
    },
    "status_counts": {
      "stockout_risk": 4,
      "reorder_now": 3,
      "ok": 8,
      "overstock": 5
    },
    "total_suggested_order_units": 842.0,
    "estimated_overstock_units": 1250.0
  }
  ```

---

### List Stock Levels
- **Method & Path**: `GET /api/inventory/stock/`
- **Purpose**: Lists current physical stock balances, supplier lead times, and target service levels for each store/SKU pair.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Query Parameters (Filtering)**:
  - `store`: Filter by store code (e.g., `?store=S1097`).
  - `sku`: Filter by product SKU (e.g., `?sku=P1`).
- **Response (HTTP 200 OK)**:
  ```json
  [
    {
      "id": 1,
      "store": "S1097",
      "sku": "P1",
      "on_hand": 18.0,
      "lead_time_days": 7,
      "service_level": 0.95,
      "updated_at": "2026-11-07T12:00:00Z"
    }
  ]
  ```

---

### Retrieve Stock Level Detail
- **Method & Path**: `GET /api/inventory/stock/{id}/`
- **Purpose**: Retrieves a single stock position record by primary key.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Path Parameters**:
  - `id`: Integer primary key of the `StockLevel`.
- **Response (HTTP 200 OK)**:
  ```json
  {
    "id": 1,
    "store": "S1097",
    "sku": "P1",
    "on_hand": 18.0,
    "lead_time_days": 7,
    "service_level": 0.95,
    "updated_at": "2026-11-07T12:00:00Z"
  }
  ```

---

### Update Stock Level (Partial Update)
- **Method & Path**: `PATCH /api/inventory/stock/{id}/`
- **Purpose**: Partially updates inventory parameters (on-hand quantity, delivery lead time, or target service level) for a store/SKU pair. Immediately impacts subsequent alert and replenishment calculations.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Path Parameters**:
  - `id`: Integer primary key of the `StockLevel`.
- **Request Body (all fields optional for PATCH)**:
  ```json
  {
    "on_hand": 90.0,
    "lead_time_days": 5,
    "service_level": 0.98
  }
  ```
- **Validation Rules**:
  - `on_hand`: Numeric value, minimum `0.0`.
  - `lead_time_days`: Integer, minimum `1`.
  - `service_level`: Float, range `0.001` to `0.999` (e.g., `0.95` represents 95%).
- **Response (HTTP 200 OK)**:
  ```json
  {
    "id": 1,
    "store": "S1097",
    "sku": "P1",
    "on_hand": 90.0,
    "lead_time_days": 5,
    "service_level": 0.98,
    "updated_at": "2026-11-07T17:15:00Z"
  }
  ```

---

## 9. Assistant Conversational Endpoint (`/api/assistant/`)

### Chat with ShelfWise Assistant
- **Method & Path**: `POST /api/assistant/chat/`
- **Purpose**: Grounded conversational assistant interface that translates user queries into structured tool executions against forecast metrics, inventory summaries, active alerts, and time-series projections.
- **Authentication**: Bearer JWT (`IsAuthenticated`)
- **Throttling & Rate Limits**:
  - Rate limit: **20 requests per minute** per authenticated user (`AssistantUserRateThrottle`).
  - HTTP 429 response is triggered if the rate limit is exceeded.
- **Input Constraints & Validation**:
  - `messages`: Required non-empty array of message objects.
  - Maximum messages: **20 messages** per conversation request.
  - Allowed roles: `'user'` or `'assistant'`.
  - Content length: Non-empty string, maximum **2000 characters** per message.
- **Request Body**:
  ```json
  {
    "messages": [
      {
        "role": "user",
        "content": "Which items have the highest stockout risk right now?"
      }
    ]
  }
  ```
- **Response (HTTP 200 OK)**:
  ```json
  {
    "reply": "### ⚠️ Critical Stockout Risks\n\nThere are currently **4 SKU locations** facing imminent stockout risk:\n\n| Store | SKU | On Hand | Lead Time | Days Cover | Suggested Order |\n|---|---|---|---|---|---|\n| S1097 | P1 | 18 | 7d | 2.1d | **+67** |\n| S1097 | P4 | 12 | 5d | 1.8d | **+45** |\n\nImmediate replenishment purchase orders are recommended to avoid stock depletion.\n\n*Note: Stock levels are simulated demo data.*",
    "tools_used": [
      "get_inventory_summary",
      "get_alerts"
    ]
  }
  ```
- **Error (HTTP 400 Bad Request)**:
  ```json
  {
    "error": "Exceeded maximum limit of 20 messages."
  }
  ```

---

## 10. External API Integrations, 429 Retry & Offline Fallback

The assistant subsystem interfaces with third-party Large Language Model providers via native function calling:

### Supported Providers & Models
- **Google Gemini**: Via Google Generative Language API (`https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`). Default model: `gemini-3.5-flash`.
- **Anthropic Claude**: Via Messages API (`https://api.anthropic.com/v1/messages`). Default model: `claude-3-5-sonnet-20241022`.

### Read-Only Data Tools Registered with the LLM
The LLM cannot execute arbitrary SQL queries. It is registered exclusively with 5 deterministic, read-only Python tools:
1. `get_model_metrics()`: Returns WAPE, bias, RMSSE, and baseline benchmarks.
2. `get_inventory_summary(run_id=None)`: Returns portfolio counts and aggregate order units.
3. `get_alerts(status=None, store=None, limit=10, run_id=None)`: Returns filtered inventory alerts.
4. `get_series_forecast(store, sku, run_id=None)`: Returns 28-day projections, confidence intervals, promo days, and stock on hand.
5. `list_stores_and_skus()`: Returns active store codes and product SKUs.

### Rate Limiting & HTTP 429 Retry Handling
When calling external LLM APIs:
- The provider wrapper (`apps.assistant.providers.post_with_retry`) detects HTTP 429 status codes.
- It parses the retry delay from either the `Retry-After` HTTP header or the Google RPC `RetryInfo.retryDelay` error payload.
- It enforces a minimum delay of 12.0s and caps delays at **20.0 seconds**, ensuring that the entire multi-turn tool call completes within a 60-second total execution budget.

### Deterministic Offline Fallback Mode
If an external API call fails (network timeout, rate limit exceeded, invalid credentials) or if `LLM_PROVIDER=none`:
- The system automatically triggers the rule-based fallback engine (`apps.assistant.services.rule_based_fallback`).
- The fallback engine inspects regex patterns and keyword intents (`stockout`, `reorder`, `accuracy`/`wape`, specific series like `S1097 P1`), executes the appropriate local database tools, and formats structured Markdown replies.
- All offline responses append the signature indicator `(offline mode)`.

> [!NOTE]
> **Production Deployment Execution Mode**:
> In the live public deployment on Render, the backend is intentionally configured with `LLM_PROVIDER=none`. The assistant operates in 100% deterministic offline fallback mode. No external API keys or network calls to Google Gemini or Anthropic are required in production.

---

## 11. Environment Configuration Variables

The API reads all operational configuration from environment variables. No secrets or tokens are hardcoded.

| Variable Name | Required | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `DEBUG` | No | `False` | Enables Django debug mode and detailed error traces. |
| `SECRET_KEY` / `DJANGO_SECRET_KEY` | Yes | None | Cryptographic key for JWT and session signing. |
| `ALLOWED_HOSTS` | Yes | `localhost,127.0.0.1` | Comma-delimited hostnames accepted by the API. |
| `DB_NAME` | Yes | `shelfwise` | PostgreSQL database name. |
| `DB_USER` | Yes | `shelfwise` | PostgreSQL database user. |
| `DB_PASSWORD` | Yes | None | PostgreSQL database user password. |
| `DB_HOST` | Yes | `localhost` | PostgreSQL host address (e.g. cloud internal host). |
| `DB_PORT` | No | `5432` | PostgreSQL network port (local Docker uses `5433`). |
| `PORT` | No | `8000` | Gunicorn container port binding. |
| `FRONTEND_URL` | No | `http://localhost:5173` | Base frontend URL for CORS, CSRF, and OIDC redirect. |
| `CORS_ALLOWED_ORIGINS` | No | Built from `FRONTEND_URL` | Permitted cross-origin resource sharing origins. |
| `CSRF_TRUSTED_ORIGINS` | No | Built from `FRONTEND_URL` | Origins trusted for state-modifying requests. |
| `SECURE_PROXY_SSL_HEADER` | No | Set in production | Header indicating reverse proxy SSL termination. |
| `OIDC_ISSUER` | No | None | Google OpenID Connect issuer URL. |
| `OIDC_CLIENT_ID` | No | None | Google OAuth 2.0 client identifier. |
| `OIDC_CLIENT_SECRET` | No | None | Google OAuth 2.0 client secret. |
| `OIDC_REDIRECT_URI` | No | None | Authorized redirect URI for Google OIDC callback. |
| `LLM_PROVIDER` | No | `none` | LLM provider: `gemini`, `anthropic`, or `none`. |
| `LLM_API_KEY` | No | None | API key for Gemini or Anthropic. |
| `LLM_MODEL` | No | `gemini-3.5-flash` | Model identifier string. |
| `LIGHTGBM_NUM_THREADS` | No | `2` | Maximum OpenMP thread pool allocation for LightGBM. |
| `DEMO_DATA_PATH` | No | None | Path to demo sales CSV for automatic seeding. |

---

## 12. Data Privacy & Security Notes

- **Password Hashing**: User passwords submitted via `/api/auth/register/` and `/api/auth/login/` are never logged, stored in plaintext, or returned in API responses. They are hashed using PBKDF2 with SHA-256 before persistence.
- **Client-Side Token Storage**: Stateless JWT access and refresh tokens are managed in browser `localStorage`. No active session tokens are stored in the database.
- **Single-Tenant Scope**: All retail data is shared across all registered accounts. Users should not upload confidential, proprietary, or personally identifiable sales records to the shared demonstration instance.
- **Ephemeral SSO Tokens**: Google OIDC authorization codes and ID tokens are consumed in-flight over HTTPS to verify user email and identity, and are immediately discarded.

