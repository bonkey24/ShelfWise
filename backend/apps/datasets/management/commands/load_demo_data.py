"""Management command to load demo sales data, seed demo user, run initial forecast, and seed stock."""

import os
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.datasets.services import ingest_sales_csv
from apps.forecasts.models import ForecastRun
from apps.forecasts.services import run_forecast
from apps.retail.models import Sale


class Command(BaseCommand):
    """Seed initial demo data including sales records, demo user, baseline forecast run, and inventory."""

    help = (
        "Idempotently loads demo sales dataset, creates demo user if missing, "
        "ensures a completed forecast run exists, and seeds inventory stock levels."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Custom path to sample sales CSV (overrides DEMO_DATA_PATH).",
        )

    def handle(self, *args, **options):
        self.stdout.write("Checking demo dataset initialization...")

        # 1. Import sales data if no Sale rows exist
        if not Sale.objects.exists():
            # Search order:
            # 1. Custom CLI argument --file (if provided)
            # 2. DEMO_DATA_PATH env var (if provided)
            # 3. /data/sample_sales.csv (Docker volume mount)
            # 4. /app/demo_data/sample_sales.csv (embedded inside container image)
            # 5. Local development fallback paths
            search_paths = []
            if options.get("file"):
                search_paths.append(Path(options["file"]))
            if os.environ.get("DEMO_DATA_PATH"):
                search_paths.append(Path(os.environ["DEMO_DATA_PATH"]))
            search_paths.append(Path("/data/sample_sales.csv"))
            search_paths.append(Path("/app/demo_data/sample_sales.csv"))

            # Local development fallbacks
            base_dir = getattr(settings, "BASE_DIR", Path("."))
            search_paths.extend([
                base_dir / "demo_data" / "sample_sales.csv",
                base_dir / ".." / "data" / "sample_sales.csv",
                base_dir / "data" / "sample_sales.csv",
                Path("data/sample_sales.csv"),
                Path("../data/sample_sales.csv"),
            ])

            csv_path = None
            for p in search_paths:
                if p.exists():
                    csv_path = p
                    break

            if csv_path:
                self.stdout.write(f"Importing initial sales CSV from {csv_path}...")
                dataset, count = ingest_sales_csv(str(csv_path), dataset_name="sample_sales.csv")
                self.stdout.write(f"Successfully imported {count} sales records from {csv_path} (Dataset ID: {dataset.id}).")
            else:
                self.stdout.write(self.style.WARNING("Demo CSV not found in search paths; skipping initial sales import."))
        else:
            self.stdout.write("Sale rows already exist; skipping sales CSV import.")

        # 2. Ensure demo user exists
        User = get_user_model()
        demo_email = "demo@shelfwise.app"
        demo_password = "Demo@12345"
        user = User.objects.filter(email=demo_email).first()
        if not user:
            user = User.objects.create_user(
                username=demo_email,
                email=demo_email,
                password=demo_password,
                is_active=True,
            )
            self.stdout.write(f"Created demo user: {demo_email}")
        else:
            user.set_password(demo_password)
            user.save(update_fields=["password"])
            self.stdout.write(f"Ensured demo user credentials for: {demo_email}")

        # 3. Ensure a completed forecast run exists so dashboard has data
        done_run = ForecastRun.objects.filter(status="done").first()
        if not done_run and Sale.objects.exists():
            self.stdout.write("No completed forecast run found. Running initial forecast synchronously...")
            run = ForecastRun.objects.create(status="running", horizon_days=28)
            run_forecast(run.id)
            self.stdout.write(f"Initial forecast run completed (Run ID: {run.id}).")
        elif done_run:
            self.stdout.write(f"Completed forecast run already exists (Run ID: {done_run.id}).")
        else:
            self.stdout.write("No sales data available to run forecast.")

        # 4. Seed stock levels
        self.stdout.write("Seeding stock levels...")
        call_command("seed_stock")
        self.stdout.write("Demo data initialization complete.")

