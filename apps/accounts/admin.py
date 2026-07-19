from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "phone", "role", "phone_verified", "is_blocked", "is_active", "date_joined")
    list_filter = ("role", "phone_verified", "is_blocked", "is_telegram_verified", "is_active", "language")
    search_fields = ("username", "email", "phone", "telegram_username", "telegram_id")
    ordering = ("-date_joined",)
    actions = ["block_users", "unblock_users"]
    fieldsets = UserAdmin.fieldsets + (
        (
            "Qo'shimcha ma'lumotlar",
            {
                "fields": (
                    "role",
                    "telegram_id",
                    "telegram_username",
                    "phone",
                    "phone_verified",
                    "is_blocked",
                    "avatar",
                    "language",
                    "is_telegram_verified",
                )
            },
        ),
    )

    @admin.action(description="BLOKLASH (salonlari yashirinadi)")
    def block_users(self, request, queryset):
        n = queryset.update(is_blocked=True)
        self.message_user(request, f"{n} ta foydalanuvchi bloklandi.")

    @admin.action(description="Blokdan chiqarish")
    def unblock_users(self, request, queryset):
        n = queryset.update(is_blocked=False)
        self.message_user(request, f"{n} ta foydalanuvchi blokdan chiqarildi.")
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Qo'shimcha",
            {"fields": ("role", "phone", "telegram_id")},
        ),
    )
