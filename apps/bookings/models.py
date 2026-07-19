from datetime import datetime, timedelta
from django.db import models
from django.utils import timezone
from apps.core.models import BaseModel


class Appointment(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        CONFIRMED = "confirmed", "Tasdiqlangan"
        CANCELLED = "cancelled", "Bekor qilindi"
        COMPLETED = "completed", "Bajarildi"
        NO_SHOW = "no_show", "Kelmadi"
        EXPIRED = "expired", "Muddati o'tdi"

    #: Bron hali faol (band) hisoblanadigan holatlar
    ACTIVE_STATUSES = (Status.PENDING, Status.CONFIRMED)

    client = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="appointments",
        limit_choices_to={"role": "client"},
    )
    barber = models.ForeignKey(
        "shops.BarberProfile",
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    service = models.ForeignKey(
        "services.Service",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    date = models.DateField(verbose_name="Sana")
    start_time = models.TimeField(verbose_name="Boshlanish vaqti")
    end_time = models.TimeField(verbose_name="Tugash vaqti")
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING, verbose_name="Holat"
    )
    client_note = models.TextField(blank=True, verbose_name="Mijoz izohi")
    barber_note = models.TextField(blank=True, verbose_name="Sartarosh izohi")
    reminded_5m = models.BooleanField(default=False)
    reminded_1h = models.BooleanField(default=False)
    reminded_24h = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Bron"
        verbose_name_plural = "Bronlar"
        db_table = "appointments"
        ordering = ["-date", "-start_time"]
        indexes = [
            models.Index(fields=["barber", "date"]),
            models.Index(fields=["client", "date"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.client} → {self.barber} | {self.date} {self.start_time}"

    @property
    def start_datetime(self):
        return datetime.combine(self.date, self.start_time)

    @property
    def end_datetime(self):
        return datetime.combine(self.date, self.end_time)

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES

    @property
    def is_upcoming(self):
        return self.is_active and self.start_datetime > datetime.now()

    def confirm(self):
        self.status = self.Status.CONFIRMED
        self.save(update_fields=["status", "updated_at"])

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])

    def complete(self):
        self.status = self.Status.COMPLETED
        self.save(update_fields=["status", "updated_at"])

    def expire(self):
        """Vaqti o'tgan/tasdiqlanmagan bronni avtomatik yopish."""
        self.status = self.Status.EXPIRED
        self.save(update_fields=["status", "updated_at"])


class BlockedSlot(BaseModel):
    """Sartarosh dam olishi yoki band bo'lgan vaqt."""

    barber = models.ForeignKey(
        "shops.BarberProfile",
        on_delete=models.CASCADE,
        related_name="blocked_slots",
    )
    date = models.DateField(verbose_name="Sana")
    start_time = models.TimeField(verbose_name="Boshlanish vaqti")
    end_time = models.TimeField(verbose_name="Tugash vaqti")
    reason = models.CharField(max_length=200, blank=True, verbose_name="Sabab")

    class Meta:
        verbose_name = "Bloklangan vaqt"
        verbose_name_plural = "Bloklangan vaqtlar"
        db_table = "blocked_slots"
        indexes = [models.Index(fields=["barber", "date"])]

    def __str__(self):
        return f"{self.barber} bloklangan: {self.date} {self.start_time}–{self.end_time}"


class Review(BaseModel):
    """Mijoz bajarilgan bron uchun barberга baho beradi (1-5 yulduz)."""

    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name="review",
    )
    client = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="reviews_given",
    )
    barber = models.ForeignKey(
        "shops.BarberProfile", on_delete=models.CASCADE, related_name="reviews",
    )
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(verbose_name="Baho (1-5)")
    comment = models.TextField(blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name = "Sharh"
        verbose_name_plural = "Sharhlar"
        db_table = "reviews"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shop", "-created_at"]),
            models.Index(fields=["barber"]),
        ]

    def __str__(self):
        return f"{self.client} → {self.barber}: {self.rating}★"
