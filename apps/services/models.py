from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import BaseModel


class ServiceCategory(BaseModel):
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, related_name="service_categories"
    )
    name = models.CharField(max_length=100, verbose_name="Nomi")
    icon = models.CharField(max_length=60, blank=True, help_text="Flaticon class nomi")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Xizmat kategoriyasi"
        verbose_name_plural = "Xizmat kategoriyalari"
        db_table = "service_categories"
        ordering = ["order"]

    def __str__(self):
        return f"{self.shop.name} — {self.name}"


class Service(BaseModel):
    shop = models.ForeignKey(
        "shops.Shop", on_delete=models.CASCADE, related_name="services"
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
    )
    barbers = models.ManyToManyField(
        "shops.BarberProfile", related_name="services", blank=True
    )
    name = models.CharField(max_length=200, verbose_name="Nomi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    duration = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(5)],
        help_text="Daqiqalarda",
        verbose_name="Davomiyligi (daqiqa)",
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Narxi (so'm)",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Xizmat"
        verbose_name_plural = "Xizmatlar"
        db_table = "services"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.shop.name})"

    @property
    def duration_display(self):
        if self.duration < 60:
            return f"{self.duration} daqiqa"
        h, m = divmod(self.duration, 60)
        return f"{h}:{m:02d} soat"
