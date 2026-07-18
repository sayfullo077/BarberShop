from django.db import models
from django.utils.text import slugify
from apps.core.models import BaseModel


class Shop(BaseModel):
    owner = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="shops",
        limit_choices_to={"role__in": ["owner", "barber"]},
    )
    name = models.CharField(max_length=200, verbose_name="Nomi")
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    city = models.CharField(max_length=100, blank=True, verbose_name="Shahar")
    address = models.TextField(verbose_name="Manzil")
    phone = models.CharField(max_length=20, verbose_name="Telefon")
    telegram_channel_id = models.CharField(
        max_length=100, blank=True,
        help_text="Portfolio uchun Telegram kanal ID (masalan: @mychanel yoki -1001234567890)",
        verbose_name="Telegram kanal ID",
    )
    logo = models.ImageField(upload_to="shops/logos/", blank=True, null=True, verbose_name="Logo")
    cover = models.ImageField(upload_to="shops/covers/", blank=True, null=True, verbose_name="Muqova")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    instagram_url = models.URLField(blank=True)
    telegram_url = models.URLField(blank=True)

    class Meta:
        verbose_name = "Salon"
        verbose_name_plural = "Salonlar"
        db_table = "shops"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class WorkingHours(BaseModel):
    DAYS = [
        (0, "Dushanba"),
        (1, "Seshanba"),
        (2, "Chorshanba"),
        (3, "Payshanba"),
        (4, "Juma"),
        (5, "Shanba"),
        (6, "Yakshanba"),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="working_hours")
    day_of_week = models.IntegerField(choices=DAYS, verbose_name="Hafta kuni")
    open_time = models.TimeField(verbose_name="Ochilish vaqti")
    close_time = models.TimeField(verbose_name="Yopilish vaqti")
    is_day_off = models.BooleanField(default=False, verbose_name="Dam olish kuni")

    class Meta:
        verbose_name = "Ish vaqti"
        verbose_name_plural = "Ish vaqtlari"
        db_table = "shop_working_hours"
        unique_together = ("shop", "day_of_week")
        ordering = ["day_of_week"]

    def __str__(self):
        return f"{self.shop.name} — {self.get_day_of_week_display()}"


class BarberProfile(BaseModel):
    class Specialization(models.TextChoices):
        MEN   = "men",   "Erkaklar"
        WOMEN = "women", "Ayollar"
        ALL   = "all",   "Hammasi"

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="barber_profile",
        limit_choices_to={"role__in": ["barber", "owner"]},
    )
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="barbers")
    bio = models.TextField(blank=True, verbose_name="Bio")
    specialization = models.CharField(
        max_length=10,
        choices=Specialization.choices,
        default=Specialization.ALL,
        verbose_name="Mutaxassislik",
    )
    experience_years = models.PositiveSmallIntegerField(default=0, verbose_name="Tajriba (yil)")
    slot_duration = models.PositiveSmallIntegerField(
        default=30,
        help_text="Bir bronlash uchun daqiqalar soni",
        verbose_name="Slot davomiyligi (daqiqa)",
    )
    is_accepting_bookings = models.BooleanField(default=True, verbose_name="Bronlash qabul qilmoqda")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Tartibi")

    class Meta:
        verbose_name = "Sartarosh profili"
        verbose_name_plural = "Sartarosh profillari"
        db_table = "barber_profiles"
        ordering = ["order", "created_at"]

    def __str__(self):
        return str(self.user)


class ShopJoinRequest(BaseModel):
    """Barber boshqa salonga qo'shilish so'rovi — salon egasi tasdiqlaydi."""

    class Status(models.TextChoices):
        PENDING  = "pending",  "Kutilmoqda"
        APPROVED = "approved", "Qabul qilindi"
        REJECTED = "rejected", "Rad etildi"

    barber = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="join_requests",
        limit_choices_to={"role__in": ["barber", "owner"]},
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="join_requests",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, verbose_name="Holat"
    )
    message = models.CharField(max_length=300, blank=True, verbose_name="Xabar")

    class Meta:
        verbose_name = "Salonga qo'shilish so'rovi"
        verbose_name_plural = "Salonga qo'shilish so'rovlari"
        db_table = "shop_join_requests"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["shop", "status"])]
        constraints = [
            models.UniqueConstraint(
                fields=["barber", "shop"],
                condition=models.Q(status="pending"),
                name="uniq_pending_join_request",
            )
        ]

    def __str__(self):
        return f"{self.barber} → {self.shop} ({self.status})"
