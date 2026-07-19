"""
Testlar uchun umumiy obyekt yaratuvchilar (kichik factory'lar).
Modellarнинг majburiy maydonlarини to'ldiradi — testlar faqat muhim farqni ko'rsatsin.
"""
from datetime import time

from apps.accounts.models import User
from apps.shops.models import Shop, BarberProfile, WorkingHours
from apps.services.models import Service

_counter = {"n": 0}


def _uniq():
    _counter["n"] += 1
    return _counter["n"]


def make_owner(*, phone_verified=True, is_blocked=False, **kw):
    n = _uniq()
    return User.objects.create(
        username=f"owner{n}",
        role=User.Role.OWNER,
        telegram_id=100000 + n,
        phone="+998901112233",
        phone_verified=phone_verified,
        is_blocked=is_blocked,
        **kw,
    )


def make_client(**kw):
    n = _uniq()
    return User.objects.create(
        username=f"client{n}",
        role=User.Role.CLIENT,
        telegram_id=900000 + n,
        **kw,
    )


def make_shop(owner=None, *, is_active=True, is_suspended=False, **kw):
    owner = owner or make_owner()
    n = _uniq()
    return Shop.objects.create(
        owner=owner,
        name=kw.pop("name", f"Salon {n}"),
        address="Toshkent",
        phone="+998901112233",
        is_active=is_active,
        is_suspended=is_suspended,
        **kw,
    )


def make_barber(shop=None, *, slot_duration=30, **kw):
    shop = shop or make_shop()
    return BarberProfile.objects.create(
        user=shop.owner,
        shop=shop,
        slot_duration=slot_duration,
        **kw,
    )


def make_service(shop=None, *, duration=30, price=50000, is_active=True, **kw):
    shop = shop or make_shop()
    n = _uniq()
    return Service.objects.create(
        shop=shop,
        name=kw.pop("name", f"Xizmat {n}"),
        duration=duration,
        price=price,
        is_active=is_active,
        **kw,
    )


def set_working_hours(shop, day_of_week, *, open_h=9, close_h=18, day_off=False):
    return WorkingHours.objects.create(
        shop=shop,
        day_of_week=day_of_week,
        open_time=time(open_h, 0),
        close_time=time(close_h, 0),
        is_day_off=day_off,
    )
