from django.contrib import admin
from apps.accounts.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "auth_provider")
    search_fields = ("user__email", "user__username")
