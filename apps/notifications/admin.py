from django.contrib import admin
from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "channel", "is_sent", "sent_at", "created_at")
    list_filter = ("notification_type", "channel", "is_sent")
    search_fields = ("user__username", "message")
    readonly_fields = ("user", "appointment", "message", "channel", "notification_type",
                       "is_sent", "sent_at", "error", "created_at")
    date_hierarchy = "created_at"
