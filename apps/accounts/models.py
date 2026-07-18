from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "client", "Mijoz"
        BARBER = "barber", "Sartarosh"
        OWNER = "owner", "Salon egasi"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CLIENT)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    phone_verified = models.BooleanField(default=False, verbose_name="Telefon tasdiqlangan")
    is_blocked = models.BooleanField(default=False, verbose_name="Bloklangan")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    language = models.CharField(max_length=5, default="uz", choices=[("uz", "O'zbek"), ("ru", "Русский")])
    is_telegram_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        db_table = "users"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_barber(self):
        return self.role in (self.Role.BARBER, self.Role.OWNER)
