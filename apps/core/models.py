import uuid
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class ContactMessage(BaseModel):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="contact_messages",
    )
    message = models.TextField(verbose_name="Xabar")
    telegram_username = models.CharField(max_length=100, blank=True)
    is_read = models.BooleanField(default=False, verbose_name="O'qilgan")

    class Meta:
        verbose_name = "Murojaat"
        verbose_name_plural = "Murojaatlar"
        db_table = "contact_messages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Murojaat — {self.telegram_username or 'Noma\'lum'} ({self.created_at:%d.%m.%Y})"
