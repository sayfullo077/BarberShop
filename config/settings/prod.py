from .base import *  # noqa
from decouple import config, Csv

DEBUG = False

# ── Sentry (xato monitoring) ──────────────────────────────
# SENTRY_DSN bo'sh bo'lsa butunlay o'chiq (hech narsa yuborilmaydi).
# Maxfiylik: send_default_pii=False (IP/foydalanuvchi ma'lumoti yubormaydi),
# before_send maxfiy qiymatlarni tozalaydi.
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    def _sentry_before_send(event, hint):
        try:
            extra = event.get("extra") or {}
            for k in ("TELEGRAM_BOT_TOKEN", "SECRET_KEY", "DB_PASSWORD", "SUPPORT_CHAT_ID"):
                extra.pop(k, None)
        except Exception:
            pass
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        send_default_pii=False,
        traces_sample_rate=config("SENTRY_TRACES_RATE", default=0.0, cast=float),
        environment=config("SENTRY_ENV", default="production"),
        before_send=_sentry_before_send,
    )

# Reverse-proxy (Caddy/nginx) orqasida — HTTPS ni to'g'ri aniqlash uchun
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# CSRF: Telegram WebApp domendan POST qiladi (bron, bekor) — bo'lmasa 403 xato
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://barber.it-services.uz",
    cast=Csv(),
)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@barbershop.uz")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs/error.log",  # noqa
            "formatter": "verbose",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "WARNING",
    },
}
