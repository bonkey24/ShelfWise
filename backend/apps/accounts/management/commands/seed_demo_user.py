"""Management command to seed a demo user account idempotently."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Seed demo user account demo@shelfwise.app with password Demo@12345."""

    help = "Seed demo user (demo@shelfwise.app) idempotently."

    def handle(self, *args, **options):
        email = "demo@shelfwise.app"
        password = "Demo@12345"

        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": "Demo User",
            },
        )
        user.set_password(password)
        user.email = email
        user.is_active = True
        user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created demo user {email}.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully updated demo user {email}.")
            )

