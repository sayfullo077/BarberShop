from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("telegram_username", "short_message", "has_file", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("telegram_username", "message", "user__username")
    readonly_fields = ("user", "message", "attachment", "telegram_username", "created_at")
    list_editable = ("is_read",)

    @admin.display(description="Xabar")
    def short_message(self, obj):
        return (obj.message[:60] + "…") if len(obj.message) > 60 else (obj.message or "—")

    @admin.display(boolean=True, description="Fayl")
    def has_file(self, obj):
        return bool(obj.attachment)
