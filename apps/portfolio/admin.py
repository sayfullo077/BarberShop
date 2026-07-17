from django.contrib import admin
from .models import PortfolioPost


@admin.register(PortfolioPost)
class PortfolioPostAdmin(admin.ModelAdmin):
    list_display = ("shop", "barber", "file_type", "caption_short", "is_active", "created_at")
    list_filter = ("shop", "file_type", "is_active")
    search_fields = ("shop__name", "caption", "barber__user__username")
    list_editable = ("is_active",)
    readonly_fields = ("telegram_file_id", "telegram_file_unique_id", "telegram_message_id", "created_at")

    @admin.display(description="Izoh")
    def caption_short(self, obj):
        return obj.caption[:60] if obj.caption else "—"
