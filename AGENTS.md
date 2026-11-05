# Project: ShelfWise (Retail Demand Forecasting)

Stack: Django 5 + DRF, PostgreSQL, Celery + Redis; React + TypeScript + Vite + Tailwind (later); ML in backend/forecasting/ (plain Python, NO Django imports) using Pandas, LightGBM, scikit-learn.

Conventions: apps live in backend/apps/ (accounts, retail, datasets, forecasts, inventory); ML code is called from Django/Celery tasks; use type hints and short docstrings; never commit secrets, read config from environment variables; time series must ALWAYS use time-based splits and never leak future data into features; write a small test for every new module.

Metrics: WAPE, bias, RMSSE. Compare every model against a naive baseline.

