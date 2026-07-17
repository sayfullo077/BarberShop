from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "phone", "role", "is_telegram_verified", "is_active", "date_joined")
    list_filter = ("role", "is_telegram_verified", "is_active", "language")
    search_fields = ("username", "email", "phone", "telegram_username", "telegram_id")
    ordering = ("-date_joined",)
    fieldsets = UserAdmin.fieldsets + (
        (
            "Qo'shimcha ma'lumotlar",
            {
                "fields": (
                    "role",
                    "telegram_id",
                    "telegram_username",
                    "phone",
                    "avatar",
                    "language",
                    "is_telegram_verified",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Qo'shimcha",
            {"fields": ("role", "phone", "telegram_id")},
        ),
    )
