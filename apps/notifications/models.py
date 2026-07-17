from django.db import models
from apps.core.models import BaseModel


class NotificationLog(BaseModel):
    class Type(models.TextChoices):
        BOOKING_CONFIRMED = "booking_confirmed", "Bron tasdiqlandi"
        REMINDER_1H = "reminder_1h", "1 soatlik eslatma"
        REMINDER_24H = "reminder_24h", "24 soatlik eslatma"
        CANCELLED = "cancelled", "Bekor qilindi"
        CUSTOM = "custom", "Boshqa"

    class Channel(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        SMS = "sms", "SMS"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notification_logs",
    )
    appointment = models.ForeignKey(
        "bookings.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    message = models.TextField()
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        db_table = "notification_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_sent"]),
            models.Index(fields=["appointment"]),
        ]

    def __str__(self):
        return f"{self.user} | {self.notification_type} | {self.channel}"
