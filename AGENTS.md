# Project: ShelfWise (Retail Demand Forecasting)

Stack: Django 5 + DRF, PostgreSQL, Celery + Redis; React + TypeScript + Vite + Tailwind (later); ML in backend/forecasting/ (plain Python, NO Django imports) using Pandas, LightGBM, scikit-learn.

Conventions: apps live in backend/apps/ (accounts, retail, datasets, forecasts, inventory); ML code is called from Django/Celery tasks; use type hints and short docstrings; never commit secrets, read config from environment variables; time series must ALWAYS use time-based splits and never leak future data into features; write a small test for every new module.

Metrics: WAPE, bias, RMSSE. Compare every model against a naive baseline.

---

## Engineering Rules & Operational Guidelines

### 1. Project & Folder Structure
- **Django Applications (`backend/apps/`)**: All web features must reside in dedicated modular apps under `backend/apps/` (`accounts`, `retail`, `datasets`, `forecasts`, `inventory`, `assistant`).
- **Decoupled Machine Learning Core (`backend/forecasting/`)**: All predictive modeling, feature engineering, and inventory replenishment mathematics must reside in `backend/forecasting/`. This module must remain **strictly pure Python with ZERO Django or web framework imports**. It interacts exclusively via Pandas DataFrames, NumPy arrays, and standard Python primitives.
- **Frontend Structure (`frontend/src/`)**: Components reside in `components/`, route views in `pages/`, shared authentication and session in `context/`, and Axios API clients in `api/`.
- **System Documentation (`docs/`)**: All architectural, relational, design, and API specifications belong in `docs/`.

### 2. Code Quality, Naming & Style
- **Python**: Follow PEP 8 conventions. Use `snake_case` for functions, methods, and variables; `PascalCase` for classes and models; `UPPER_SNAKE_CASE` for module constants. Provide short docstrings for every class, public function, and management command.
- **TypeScript**: Follow standard React and TypeScript idioms. Use `PascalCase` for components, types, and interfaces; `camelCase` for functions, hooks, and variables.
- **Documentation Integrity**: Maintain documentation integrity. Preserve all existing comments and docstrings that are unrelated to your code changes.

### 3. Component & Utility Reuse
- Before creating a new UI component, utility, or backend service, inspect and reuse existing abstractions (e.g., `Button`, `Card`, `MetricCard`, `TopBar`, standard DRF serializers, and Pandera validation schemas).
- Adhere to established architectural patterns: encapsulate business logic inside service layers (`services.py`), data validation in serializers or Pandera schemas, and HTTP coordination in views.

### 4. Dependency Management
- **Add dependencies only with explicit justification**: Do not introduce third-party libraries for trivial utilities that can be handled with standard library primitives (e.g., standard Python `secrets` and `signing` for OIDC state, native `threading` for daemon tasks).
- Any new dependency must be added to `backend/requirements.txt` or `frontend/package.json` with strict version pinning.
- Keep `requirements.txt` and `package-lock.json` in sync with installed environments at all times.

### 5. Type Safety & Static Typing
- **Backend**: Use complete Python type annotations across all function arguments, return types, and service boundaries (`typing` module or Python 3.10+ native pipe unions).
- **Frontend**: Enforce strict TypeScript typing across all API response contracts, state variables, and component props. Never use untyped `any`.

### 6. Error Handling & UI States
- **Defensive Backend Execution**: Asynchronous threads must catch and log exceptions, updating the corresponding `ForecastRun.status` to `failed` and capturing the error message to avoid orphaned `running` states.
- **Standardized API Error Envelopes**: Return consistent HTTP status codes and structured JSON error responses (`{"detail": "..."}` or field-level validation dictionaries).
- **UI State Handling**: Every user interface component interacting with asynchronous queries or mutations must explicitly handle:
  - **Loading states**: Skeleton loaders or indicators during initial fetch.
  - **Empty states**: Clear explanatory notices with actionable next steps when datasets, forecasts, or alerts are absent.
  - **Error states**: Non-intrusive banners with clear failure descriptions and retry triggers.
  - **Success states**: Immediate optimistic updates or toast notifications confirming operations.
- **Resilient Third-Party Integrations**: LLM provider calls must implement HTTP 429 retry backoff with delay extraction and fall back gracefully to the deterministic offline engine.

### 7. Security, Secrets & Environment Hygiene
- **NEVER** print, log, commit, or paste secrets, tokens, API keys, credentials, or the contents of `backend/.env`.
- **Placeholder Only in `.env.example`**: Store placeholders and variable documentation only; never place active credentials or secret values in `.env.example`.
- Read all application secrets, database credentials, and third-party API keys exclusively from environment variables.
- Store passwords strictly as PBKDF2 hashes; never persist JWT tokens or active session state in the database.

### 8. Database & API Access
- **Server-Side Enforcement**: All authorization, parameter validation, and replenishment math must be calculated and validated server-side. Never rely on client assertions.
- **Parameterized SQL**: Use Django ORM queries exclusively. Never concatenate raw SQL strings.
- **Relational Integrity**: Enforce unique constraints and composite indexes aligned with operational query access patterns.
- **Database Migrations**: Generate and commit explicit Django migrations (`python manage.py makemigrations`) for every model or schema modification. Verify that models and migrations match (`python manage.py makemigrations --check`).

### 9. Forecasting & Time-Series Rules
- **Series Alignment**: Always join forecasts to actuals by **`(store, sku, date)`**, NEVER by array position or row index.
- **Zero Future Leakage**: Time series models must strictly enforce time-based splits. No future observations may leak into training features, rolling windows, or inference routines.
- **Direct Multi-Step Horizon & Minimum Lag**: All lag features must be $\ge 28$ days; rolling statistics must be explicitly pre-shifted by 28 days to match the 28-day replenishment horizon.
- **Evaluation Discipline**: Model evaluation (WAPE, bias, RMSSE, MAE) and baseline comparisons must be calibrated exclusively on the held-out final 28-day window.

### 10. Testing & Verification Discipline
- **Write Tests for Every New Module**: Every new service, model, or algorithm must include corresponding unit or integration tests.
- **Preserve Leakage Detection**: Always keep the temporal leakage test suite (`backend/forecasting/tests/test_leakage.py`) passing.
- **Mandatory Verification**: Before concluding any task, always verify changes locally:
  - Backend: `backend\venv\Scripts\pytest.exe backend`
  - Frontend: `npm --prefix frontend run build`

### 11. Change Discipline
- **Inspect Before Modifying**: Read and analyze existing code and tests before making changes.
- **No Unrelated Rewrites**: Keep changes scoped directly to the user's request. Do not refactor unrelated code or alter forecasting mathematics unless a genuine defect is proven.
- **No Git Commands**: Never execute git commands (`git add`, `git commit`, `git push`, `git status`, etc.) unless explicitly commanded by the user.
- **Reporting**: Always report all files changed and any failed commands encountered during execution.

### 12. PowerShell-Specific Command Conventions
- Always write commands targeting PowerShell (the active operating system shell is Windows).
- Use Windows path separators (`\`) when invoking local scripts and executables (e.g., `backend\venv\Scripts\pytest.exe`).
- When piping in PowerShell commands, escape variables (such as `` `$ ``) inside double-quoted strings or use single quotes (`'...'`) to prevent unintended variable expansion.
- Prefer native PowerShell cmdlets (`Copy-Item`, `Get-ChildItem`, `Test-Path`, `Select-String`) over Unix aliases.

### 13. Documentation Maintenance
- Whenever system behavior, database schema, API contracts, or forecasting logic change, update the corresponding documents in `docs/` (`PRD.md`, `DESIGN.md`, `ARCHITECTURE.md`, `DATABASE.md`, `API.md`).

### 14. Deployment & Production Notes
- **Container Path**: In Docker builds, paths are relative to `backend/` (Render Dockerfile path set to `Dockerfile` with root directory `backend`).
- **Dynamic Port Binding**: Gunicorn must dynamically bind to `0.0.0.0:${PORT:-8000}`.
- **Environment Isolation**: Never rely on a committed `.env` file in containerized or cloud environments. Production configuration must be provided via environment variables.

---

## Documentation Index

The `docs/` directory contains comprehensive, code-free system documentation:

- [docs/PRD.md](file:///c:/Users/pitay/Desktop/ShelfWise/docs/PRD.md): Product requirements document, business domain, user journeys, target personas, and scope.
- [docs/DESIGN.md](file:///c:/Users/pitay/Desktop/ShelfWise/docs/DESIGN.md): Design system tokens (colors, typography, spacing), reusable components, layouts, and accessibility notes.
- [docs/ARCHITECTURE.md](file:///c:/Users/pitay/Desktop/ShelfWise/docs/ARCHITECTURE.md): System architecture, component relationships, data flows, forecasting design, testing, CI, and deployment topology.
- [docs/DATABASE.md](file:///c:/Users/pitay/Desktop/ShelfWise/docs/DATABASE.md): Relational schema, PostgreSQL configuration, tables, Mermaid ER diagram, indexes, migrations, seeding, and disaster recovery.
- [docs/API.md](file:///c:/Users/pitay/Desktop/ShelfWise/docs/API.md): Complete REST API specification covering endpoints, request/response examples, throttling, and offline fallback.
