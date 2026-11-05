"""User profile model extending Django auth User."""

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Profile metadata for a user, tracking the authentication provider."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    auth_provider = models.CharField(
        max_length=50,
        default="email",
        help_text="Origin of the account, e.g. 'email' or 'sso'.",
    )

    def __str__(self) -> str:
        return f"{self.user.username} ({self.auth_provider})"


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """Automatically ensure a UserProfile exists for every User."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
