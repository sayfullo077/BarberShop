# BarberShop — Serverga joylash (deploy)

Bir komanda bilan ishga tushadi: PostgreSQL, Redis, Django (gunicorn),
django-q (fon vazifalari) va Caddy (avtomatik HTTPS).

## Talablar
- Ubuntu/Debian server, **Docker** + **Docker Compose** o'rnatilgan.
- Domen **barber.it-services.uz** ning A-record'i shu server IP'siga qaratilgan.
- 80 va 443 portlar ochiq (Caddy Let's Encrypt sertifikatini avtomatik oladi).
- Telegram bot tokeni (@BotFather).

## Qadamlar

```bash
# 1. Loyihani serverga oling
git clone <repo> barbershop && cd barbershop
#    (yoki papkani rsync/scp bilan tashlang)

# 2. Env faylni tayyorlang
cp .env.prod.example .env
nano .env          # SECRET_KEY, DB_PASSWORD, TELEGRAM_BOT_TOKEN, admin parol...

# 3. BITTA KOMANDA — hammasi ishga tushadi
docker compose up -d --build
```

Tayyor. Birinchi ishga tushishda avtomatik bajariladi:
migratsiyalar → statik fayllar → davriy vazifalar (eslatma/expiry) →
admin superuser yaratiladi → HTTPS sertifikat olinadi.
Telegram bot **`bot` servisida polling rejimida** avtomatik ishga tushadi
(webhook sozlash SHART EMAS).

`https://barber.it-services.uz` ochiladi. Admin: `https://barber.it-services.uz/admin/`.

## BotFather sozlamasi
1. Bot tokenini `.env` dagi `TELEGRAM_BOT_TOKEN` ga qo'ying.
2. `.env` da `TELEGRAM_WEBAPP_URL=https://barber.it-services.uz/` bo'lsin.
3. `@BotFather` → **Bot Settings → Menu Button** → URL: `https://barber.it-services.uz/`
   (mini-ilova shu tugmadan ochiladi). `/start` tugmasi ham WebApp'ni ochadi.

## Foydali komandalar

```bash
docker compose logs -f web          # web loglar
docker compose logs -f bot          # Telegram bot (polling) loglar
docker compose logs -f qcluster     # fon vazifalar (eslatmalar)
docker compose exec web python manage.py createsuperuser      # qo'shimcha admin
docker compose restart bot          # botni qayta ishga tushirish
docker compose down                 # to'xtatish
docker compose up -d --build        # yangilangach qayta deploy
```

## Eslatma
- `.env` ni hech qachon git'ga qo'ymang (`.gitignore` da).
- Kod yangilangach: `git pull && docker compose up -d --build`.
- Ma'lumotlar `postgres_data` va `media_data` volume'larda saqlanadi (deploy'da yo'qolmaydi).
