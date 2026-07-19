"""
Test sozlamalari — CI va lokal `manage.py test` uchun.
Redis/Caddy/django-q cluster'siz, tez ishlaydigan izolyatsiyalangan muhit.
"""
from .base import *  # noqa

DEBUG = False

# Redis shart emas — testlarда locmem cache va DB sessiyalar.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Testlar tezroq: oddiy (tez) parol hasher.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# collectstatic'siz ham ishlashi uchun manifest storage'ni o'chiramiz.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# django-q vazifalari testда sinxron (cluster shart bo'lmasin).
Q_CLUSTER = {**globals().get("Q_CLUSTER", {}), "sync": True}

# Telegram tokeni testда bo'lmaydi — tashqi API chaqiruvlari yuz bermasin.
TELEGRAM_BOT_TOKEN = ""

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
