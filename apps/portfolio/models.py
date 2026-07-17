from django.db import models
from apps.core.models import BaseModel


class PortfolioPost(BaseModel):
    """
    Media post synced from a Telegram channel.
    We store only metadata — actual media lives on Telegram servers (free, unlimited).
    file_id is a persistent Telegram file identifier used to build download URLs via Bot API.
    """

    class FileType(models.TextChoices):
        PHOTO = "photo", "Rasm"
        VIDEO = "video", "Video"

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="portfolio_posts",
    )
    barber = models.ForeignKey(
        "shops.BarberProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portfolio_posts",
    )
    telegram_message_id = models.BigIntegerField(verbose_name="Telegram xabar ID")
    telegram_file_id = models.CharField(max_length=300, verbose_name="Telegram fayl ID")
    telegram_file_unique_id = models.CharField(
        max_length=100, unique=True, verbose_name="Unikal fayl ID"
    )
    file_type = models.CharField(
        max_length=10, choices=FileType.choices, default=FileType.PHOTO
    )
    caption = models.TextField(blank=True, verbose_name="Izoh")
    thumbnail_file_id = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Ko'rsatilsin")
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Portfolio post"
        verbose_name_plural = "Portfolio postlar"
        db_table = "portfolio_posts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shop", "is_active"]),
            models.Index(fields=["barber", "is_active"]),
        ]

    def __str__(self):
        return f"{self.shop.name} | {self.file_type} | {self.telegram_message_id}"
