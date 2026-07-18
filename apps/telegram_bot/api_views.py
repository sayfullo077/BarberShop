"""
Telegram WebApp REST API.
All endpoints are authenticated via Telegram WebApp initData.
"""
import hashlib
import hmac
import json
import time
import urllib.parse
from datetime import datetime, date
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.bookings.models import Appointment
from apps.bookings.services import create_appointment, get_available_slots
from apps.services.models import Service
from apps.shops.models import BarberProfile, Shop


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _validate_init_data(init_data: str) -> dict | None:
    """Validate Telegram WebApp initData signature, return user dict or None."""
    if not init_data:
        return None
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    if int(parsed.get("auth_date", 0)) < time.time() - 86400:
        return None

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, received_hash):
        return None

    try:
        return json.loads(parsed.get("user", "{}"))
    except json.JSONDecodeError:
        return None


def _get_or_create_user(tg: dict) -> User:
    tid = int(tg["id"])
    user, created = User.objects.get_or_create(
        telegram_id=tid,
        defaults={
            "username": tg.get("username") or f"tg_{tid}",
            "first_name": tg.get("first_name", ""),
            "last_name": tg.get("last_name", ""),
            "telegram_username": tg.get("username", ""),
            "is_telegram_verified": True,
            "role": User.Role.CLIENT,
        },
    )
    if not created:
        updated = {}
        if not user.is_telegram_verified:
            updated["is_telegram_verified"] = True
        if tg.get("username") and user.telegram_username != tg["username"]:
            updated["telegram_username"] = tg["username"]
        if updated:
            for k, v in updated.items():
                setattr(user, k, v)
            user.save(update_fields=list(updated.keys()))
    return user


def webapp_api(view_func):
    """
    Decorator for all WebApp API views.
    Validates Telegram initData from Authorization header.
    In DEBUG mode without a token, injects a dev user automatically.
    """
    @csrf_exempt
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Development bypass when no token configured
        if settings.DEBUG and not settings.TELEGRAM_BOT_TOKEN:
            user, _ = User.objects.get_or_create(
                username="dev_webapp",
                defaults={
                    "first_name": "Dev",
                    "role": User.Role.CLIENT,
                    "is_telegram_verified": True,
                },
            )
            request.tg_user = user
            return view_func(request, *args, **kwargs)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("tma "):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        tg_data = _validate_init_data(auth[4:])
        if tg_data is None:
            return JsonResponse({"error": "Invalid auth"}, status=401)

        request.tg_user = _get_or_create_user(tg_data)
        return view_func(request, *args, **kwargs)

    return wrapper


def _err(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": msg}, status=status)


# ---------------------------------------------------------------------------
# Shops
# ---------------------------------------------------------------------------

def _shop_card(request, s):
    """Bosh sahifa/qidiruv kartasi uchun salon ma'lumoti."""
    return {
        "id": str(s.id),
        "name": s.name,
        "slug": s.slug,
        "city": s.city,
        "address": s.address,
        "phone": s.phone,
        "logo_url": request.build_absolute_uri(s.logo.url) if s.logo else None,
        "barbers_count": s.barbers.filter(is_accepting_bookings=True).count(),
        "telegram_url": s.telegram_url,
        "instagram_url": s.instagram_url,
    }


@webapp_api
@require_GET
def shops_list(request):
    shops = (
        Shop.objects.filter(is_active=True)
        .select_related("owner")
        .prefetch_related("barbers")
    )
    return JsonResponse({"shops": [_shop_card(request, s) for s in shops]})


@webapp_api
@require_GET
def search(request):
    """Salon yoki barberni qidirish: nomi, shahar, manzil, telefon,
    usta ismi/telefoni yoki xizmat nomi bo'yicha."""
    from django.db.models import Q

    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"shops": []})

    digits = "".join(ch for ch in q if ch.isdigit())
    filt = (
        Q(name__icontains=q)
        | Q(city__icontains=q)
        | Q(address__icontains=q)
        | Q(barbers__user__first_name__icontains=q)
        | Q(barbers__user__last_name__icontains=q)
        | Q(services__name__icontains=q)
    )
    # Telefon bo'yicha (raqamlar bo'lsa raqam substring bilan)
    phone_q = digits if len(digits) >= 3 else q
    filt |= Q(phone__icontains=phone_q) | Q(barbers__user__phone__icontains=phone_q)

    shops = (
        Shop.objects.filter(is_active=True).filter(filt)
        .select_related("owner").prefetch_related("barbers").distinct()[:30]
    )
    return JsonResponse({"shops": [_shop_card(request, s) for s in shops]})


@webapp_api
@require_GET
def shop_detail(request, slug):
    shop = get_object_or_404(Shop, slug=slug, is_active=True)

    services = list(
        shop.services.filter(is_active=True)
        .select_related("category")
        .values("id", "name", "duration", "price", "description", "category__name")
    )
    barbers = []
    for b in shop.barbers.filter(is_accepting_bookings=True).select_related("user"):
        barbers.append({
            "id": str(b.id),
            "name": b.user.get_full_name() or b.user.username,
            "experience_years": b.experience_years,
            "slot_duration": b.slot_duration,
            "avatar_url": request.build_absolute_uri(b.user.avatar.url) if b.user.avatar else None,
            "bio": b.bio,
        })
    working_hours = []
    for wh in shop.working_hours.all():
        working_hours.append({
            "day": wh.day_of_week,
            "day_name": wh.get_day_of_week_display(),
            "open": wh.open_time.strftime("%H:%M") if not wh.is_day_off else None,
            "close": wh.close_time.strftime("%H:%M") if not wh.is_day_off else None,
            "is_day_off": wh.is_day_off,
        })

    return JsonResponse({
        "id": str(shop.id),
        "name": shop.name,
        "slug": shop.slug,
        "city": shop.city,
        "address": shop.address,
        "phone": shop.phone,
        "latitude": float(shop.latitude) if shop.latitude is not None else None,
        "longitude": float(shop.longitude) if shop.longitude is not None else None,
        "description": shop.description,
        "logo_url": request.build_absolute_uri(shop.logo.url) if shop.logo else None,
        "cover_url": request.build_absolute_uri(shop.cover.url) if shop.cover else None,
        "telegram_url": shop.telegram_url,
        "instagram_url": shop.instagram_url,
        "services": [
            {
                "id": str(s["id"]),
                "name": s["name"],
                "duration": s["duration"],
                "price": str(s["price"]),
                "description": s["description"] or "",
                "category": s["category__name"] or "",
            }
            for s in services
        ],
        "barbers": barbers,
        "working_hours": working_hours,
    })


# ---------------------------------------------------------------------------
# Slots
# ---------------------------------------------------------------------------

@webapp_api
@require_GET
def slots_api(request):
    barber_id = request.GET.get("barber_id")
    date_str = request.GET.get("date")
    if not barber_id or not date_str:
        return _err("barber_id va date kerak")
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return _err("Noto'g'ri sana formati")
    if selected_date < date.today():
        return JsonResponse({"slots": [], "slot_duration": 30})

    barber = get_object_or_404(BarberProfile, id=barber_id, is_accepting_bookings=True)
    slots = get_available_slots(barber, selected_date)
    return JsonResponse({
        "slots": [s.strftime("%H:%M") for s in slots],
        "slot_duration": barber.slot_duration,
    })


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@webapp_api
@require_POST
def booking_create(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return _err("JSON kerak")

    # Toza JSON xato qaytaramiz (get_object_or_404 HTML 404 sahifa berardi —
    # frontend uni JSON deb o'qib "Unexpected token '<'" xatosini olardi).
    barber = BarberProfile.objects.filter(
        id=data.get("barber_id"), is_accepting_bookings=True
    ).select_related("shop").first()
    if not barber:
        return _err("Sartarosh topilmadi yoki bron qabul qilmayapti", status=404)
    service = Service.objects.filter(
        id=data.get("service_id"), is_active=True, shop=barber.shop
    ).first()
    if not service:
        return _err("Xizmat topilmadi. Iltimos, xizmatni qayta tanlang", status=404)

    try:
        selected_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
        start_time = datetime.strptime(data["time"], "%H:%M").time()
    except (KeyError, ValueError):
        return _err("Sana yoki vaqt noto'g'ri")

    # Rolsiz foydalanuvchini mijoz qilamiz. MUHIM: barber/owner rolini
    # o'zgartirmaymiz — barber ham mijoz sifatida bron qila oladi, lekin
    # o'z barber rolini yo'qotmasligi kerak.
    user = request.tg_user
    user_updates = []
    if user.role not in (User.Role.CLIENT, User.Role.OWNER, User.Role.BARBER):
        user.role = User.Role.CLIENT
        user_updates.append("role")

    # Telefon majburiy — mijoz bilan bog'lanish uchun (kamida 7 ta raqam)
    phone = (data.get("phone") or "").strip()
    if sum(c.isdigit() for c in phone) < 7:
        return _err("Telefon raqami majburiy")
    if phone != user.phone:
        user.phone = phone[:20]
        user_updates.append("phone")
    if user_updates:
        user.save(update_fields=user_updates)

    try:
        appt = create_appointment(
            client=user,
            barber=barber,
            service=service,
            date=selected_date,
            start_time=start_time,
        )
    except ValueError as e:
        return _err(str(e), status=409)

    from django_q.tasks import async_task
    async_task("apps.notifications.tasks.send_booking_confirmation", str(appt.id))

    return JsonResponse({
        "ok": True,
        "appointment_id": str(appt.id),
        "date": appt.date.strftime("%d.%m.%Y"),
        "time": appt.start_time.strftime("%H:%M"),
        "service": appt.service.name,
        "shop": appt.shop.name,
    })


@webapp_api
@require_GET
def my_bookings(request):
    appts = (
        Appointment.objects.filter(client=request.tg_user)
        .select_related("shop", "service", "barber__user")
        .order_by("-date", "-start_time")[:30]
    )
    data = []
    for a in appts:
        data.append({
            "id": str(a.id),
            "shop_name": a.shop.name,
            "service_name": a.service.name,
            "barber_name": a.barber.user.get_full_name() or a.barber.user.username,
            "date": a.date.strftime("%d.%m.%Y"),
            "date_iso": a.date.isoformat(),
            "time": a.start_time.strftime("%H:%M"),
            "end_time": a.end_time.strftime("%H:%M"),
            "status": a.status,
            "status_display": a.get_status_display(),
            "price": str(a.service.price),
            "can_cancel": a.status in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED),
        })
    return JsonResponse({"appointments": data})


@webapp_api
@require_POST
def booking_cancel(request, appointment_id):
    appt = get_object_or_404(
        Appointment, id=appointment_id, client=request.tg_user
    )
    if appt.status not in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
        return _err("Bu bronni bekor qilib bo'lmaydi")

    appt.cancel()

    from django_q.tasks import async_task
    async_task("apps.notifications.tasks.send_cancellation_notice", str(appt.id))

    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------

@webapp_api
@require_GET
def me(request):
    u = request.tg_user
    has_barber = hasattr(u, "barber_profile")
    owned_shop = None
    is_shop_owner = False
    if has_barber:
        shop = u.barber_profile.shop
        is_shop_owner = shop.owner_id == u.id
        if is_shop_owner:
            owned_shop = {"slug": shop.slug, "name": shop.name}
    return JsonResponse({
        "id": str(u.id),
        "name": u.get_full_name() or u.username,
        "role": u.role,
        "phone": u.phone,
        "is_barber": u.is_barber,
        "is_shop_owner": is_shop_owner,
        "owned_shop": owned_shop,
        "barber_profile": {
            "shop_slug": u.barber_profile.shop.slug,
            "shop_name": u.barber_profile.shop.name,
            "is_owner": is_shop_owner,
            "specialization": u.barber_profile.specialization,
            "experience_years": u.barber_profile.experience_years,
            "is_accepting_bookings": u.barber_profile.is_accepting_bookings,
        } if has_barber else None,
    })


# ---------------------------------------------------------------------------
# Barber Registration
# ---------------------------------------------------------------------------

# Standart xizmat shablonlari
PREDEFINED_SERVICES = [
    {"name": "Soch kesish",           "duration": 30,  "price": 50000,  "group": "men"},
    {"name": "Soqol olish",           "duration": 20,  "price": 30000,  "group": "men"},
    {"name": "Soch + Soqol",          "duration": 45,  "price": 70000,  "group": "men"},
    {"name": "Bolalar soch kesish",   "duration": 20,  "price": 35000,  "group": "men"},
    {"name": "Soch yuvish + quritish","duration": 30,  "price": 25000,  "group": "all"},
    {"name": "Qosh tartib berish",    "duration": 15,  "price": 20000,  "group": "all"},
    {"name": "Ayollar soch kesish",   "duration": 60,  "price": 80000,  "group": "women"},
    {"name": "Ayollar soch bo'yash",  "duration": 90,  "price": 150000, "group": "women"},
    {"name": "Ko'k qo'yish",          "duration": 120, "price": 200000, "group": "women"},
    {"name": "Perm (jingalak)",       "duration": 90,  "price": 180000, "group": "women"},
    {"name": "Soch laminatsiyasi",    "duration": 90,  "price": 250000, "group": "women"},
    {"name": "Yuz parvarishi",        "duration": 45,  "price": 60000,  "group": "all"},
]


@webapp_api
@require_GET
def predefined_services(request):
    return JsonResponse({"services": PREDEFINED_SERVICES})


@webapp_api
@csrf_exempt
def barber_register(request):
    """
    POST: Barber sifatida ro'yxatdan o'tish.
    Creates Shop + BarberProfile for the current user.
    """
    if request.method != "POST":
        return _err("POST kerak", 405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return _err("JSON xato")

    u = request.tg_user

    first_name = (body.get("first_name") or "").strip()
    last_name  = (body.get("last_name") or "").strip()
    phone      = (body.get("phone") or "").strip()
    city       = (body.get("city") or "").strip()
    bio        = (body.get("bio") or "").strip()
    spec       = body.get("specialization", "all")
    exp        = int(body.get("experience_years", 0))

    if not first_name or not city:
        return _err("Ism va shahar majburiy")

    if spec not in ("men", "women", "all"):
        return _err("Noto'g'ri mutaxassislik")

    from django.utils.text import slugify
    import uuid as uuid_mod
    from apps.shops.models import Shop, BarberProfile

    # Foydalanuvchini yangilash
    u.first_name = first_name
    u.last_name  = last_name
    if phone:
        u.phone = phone
    u.role = User.Role.BARBER
    u.save(update_fields=["first_name", "last_name", "phone", "role"])

    shop_id    = (body.get("shop_id") or "").strip()
    shop_name  = (body.get("shop_name") or "").strip()
    shop_addr  = (body.get("shop_address") or city).strip()

    from apps.shops.models import WorkingHours
    from datetime import time as dtime

    def _make_solo_shop():
        """Barber uchun shaxsiy (mustaqil) salon yaratadi."""
        new_name = shop_name or (f"{first_name} {last_name}".strip() + " Barber")
        base_slug = slugify(new_name) or f"barber-{str(uuid_mod.uuid4())[:8]}"
        slug_val, counter = base_slug, 1
        while Shop.objects.filter(slug=slug_val).exists():
            slug_val = f"{base_slug}-{counter}"
            counter += 1
        s = Shop.objects.create(
            owner=u, name=new_name, slug=slug_val,
            address=shop_addr, phone=phone or "", description=bio,
        )
        for day in range(6):
            WorkingHours.objects.create(
                shop=s, day_of_week=day,
                open_time=dtime(9, 0), close_time=dtime(19, 0),
            )
        WorkingHours.objects.create(
            shop=s, day_of_week=6,
            open_time=dtime(10, 0), close_time=dtime(17, 0),
        )
        return s

    def _request_join(target_shop_id):
        """Mavjud salonga qo'shilish so'rovini yaratadi. (shop, error) qaytaradi."""
        from apps.shops.models import ShopJoinRequest
        try:
            target = Shop.objects.get(id=target_shop_id, is_active=True)
        except Shop.DoesNotExist:
            return None
        if target.owner_id != u.id and u.barber_profile.shop_id != target.id:
            ShopJoinRequest.objects.get_or_create(
                barber=u, shop=target,
                status=ShopJoinRequest.Status.PENDING,
                defaults={"message": bio[:300]},
            )
            from django_q.tasks import async_task
            jr = ShopJoinRequest.objects.filter(
                barber=u, shop=target, status=ShopJoinRequest.Status.PENDING
            ).first()
            if jr:
                async_task("apps.notifications.tasks.notify_join_request", str(jr.id))
        return target

    # Agar allaqachon barber bo'lsa — profilini yangilash; salon tanlansa so'rov yuboriladi
    if hasattr(u, "barber_profile"):
        bp = u.barber_profile
        bp.bio = bio
        bp.specialization = spec
        bp.experience_years = exp
        bp.save(update_fields=["bio", "specialization", "experience_years"])
        if shop_id:
            target = _request_join(shop_id)
            if target is None:
                return _err("Salon topilmadi", 404)
            return JsonResponse({"ok": True, "shop_slug": bp.shop.slug,
                                 "created": False, "join_requested": True,
                                 "target_shop": target.name})
        return JsonResponse({"ok": True, "shop_slug": bp.shop.slug, "created": False})

    # Yangi barber — har doim shaxsiy (mustaqil) salon bilan boshlaydi
    shop = _make_solo_shop()
    bp = BarberProfile.objects.create(
        user=u, shop=shop, bio=bio, specialization=spec,
        experience_years=exp, slot_duration=30,
    )
    # Agar mavjud salon tanlagan bo'lsa — o'shanga qo'shilish so'rovi
    join_requested = False
    if shop_id:
        target = _request_join(shop_id)
        join_requested = target is not None

    return JsonResponse({"ok": True, "shop_slug": shop.slug,
                         "created": True, "join_requested": join_requested}, status=201)


# ---------------------------------------------------------------------------
# Barber: Service Management
# ---------------------------------------------------------------------------

@webapp_api
@csrf_exempt
def barber_services(request):
    """GET: barber xizmatlari ro'yxati. POST: yangi xizmat qo'shish."""
    u = request.tg_user
    if not u.is_barber or not hasattr(u, "barber_profile"):
        return _err("Barber emas", 403)

    bp = u.barber_profile
    shop = bp.shop

    if request.method == "GET":
        svcs = shop.services.filter(is_active=True).order_by("order", "name")
        return JsonResponse({"services": [
            {"id": str(s.id), "name": s.name, "duration": s.duration, "price": str(s.price)}
            for s in svcs
        ]})

    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return _err("JSON xato")

        name     = (body.get("name") or "").strip()
        duration = int(body.get("duration", 30))
        price    = body.get("price", 0)

        if not name:
            return _err("Xizmat nomi majburiy")
        if duration < 5:
            return _err("Davomiylik kamida 5 daqiqa")

        from apps.services.models import Service
        svc = Service.objects.create(
            shop=shop, name=name, duration=duration, price=price
        )
        svc.barbers.add(bp)
        return JsonResponse({
            "ok": True,
            "id": str(svc.id),
            "name": svc.name,
            "duration": svc.duration,
            "price": str(svc.price),
        }, status=201)

    return _err("Method not allowed", 405)


@webapp_api
@csrf_exempt
def barber_service_delete(request, service_id):
    """DELETE: barber xizmatini o'chirish."""
    u = request.tg_user
    if not u.is_barber or not hasattr(u, "barber_profile"):
        return _err("Barber emas", 403)

    from apps.services.models import Service
    svc = get_object_or_404(Service, id=service_id, shop=u.barber_profile.shop)
    svc.delete()
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# Barber Dashboard
# ---------------------------------------------------------------------------

@csrf_exempt
@webapp_api
def barber_toggle_accepting(request):
    """Bronlash qabul qilishni yoqish/o'chirish."""
    u = request.tg_user
    if not u.is_barber or not hasattr(u, "barber_profile"):
        return _err("Barber emas", 403)
    body = json.loads(request.body or b"{}")
    bp = u.barber_profile
    bp.is_accepting_bookings = bool(body.get("is_accepting", not bp.is_accepting_bookings))
    bp.save(update_fields=["is_accepting_bookings"])
    return JsonResponse({"is_accepting": bp.is_accepting_bookings})


@webapp_api
def barber_dashboard(request):
    """Barber uchun: bugungi/kelayotgan bronlar va statistika."""
    u = request.tg_user
    if not u.is_barber or not hasattr(u, "barber_profile"):
        return _err("Barber emas", 403)

    from django.utils import timezone
    bp = u.barber_profile
    today = timezone.localdate()

    upcoming = Appointment.objects.filter(
        barber=bp,
        date__gte=today,
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
    ).select_related("client", "service").order_by("date", "start_time")[:20]

    data = []
    for a in upcoming:
        data.append({
            "id": str(a.id),
            "client_name": a.client.get_full_name() or a.client.username,
            "client_phone": a.client.phone,
            "service_name": a.service.name,
            "date": a.date.strftime("%d.%m.%Y"),
            "time": a.start_time.strftime("%H:%M"),
            "end_time": a.end_time.strftime("%H:%M"),
            "price": str(a.service.price),
            "status": a.status,
            "status_display": a.get_status_display(),
        })

    total_today = Appointment.objects.filter(
        barber=bp, date=today,
        status__in=[Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED],
    ).count()

    from apps.shops.models import ShopJoinRequest
    is_owner = bp.shop.owner_id == u.id
    pending_requests = (
        ShopJoinRequest.objects.filter(
            shop=bp.shop, status=ShopJoinRequest.Status.PENDING
        ).count() if is_owner else 0
    )

    return JsonResponse({
        "shop_name": bp.shop.name,
        "shop_slug": bp.shop.slug,
        "shop_address": bp.shop.address,
        "shop_logo_url": request.build_absolute_uri(bp.shop.logo.url) if bp.shop.logo else None,
        "is_owner": is_owner,
        "pending_requests": pending_requests,
        "name": u.get_full_name() or u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "phone": u.phone,
        "bio": bp.bio,
        "specialization": bp.specialization,
        "experience_years": bp.experience_years,
        "avatar_url": request.build_absolute_uri(u.avatar.url) if u.avatar else None,
        "is_accepting": bp.is_accepting_bookings,
        "today_count": total_today,
        "upcoming": data,
    })


# ---------------------------------------------------------------------------
# Image Upload
# ---------------------------------------------------------------------------

@csrf_exempt
@webapp_api
def upload_image(request):
    """Rasm yuklash — avatar yoki salon logo uchun."""
    if request.method != "POST":
        return _err("POST kerak", 405)
    f = request.FILES.get("file")
    if not f:
        return _err("'file' maydoni kerak")
    if f.size > 5 * 1024 * 1024:
        return _err("Fayl hajmi 5MB dan oshmasin")
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if f.content_type not in allowed:
        return _err("Faqat JPEG, PNG yoki WebP ruxsat etilgan")

    import os
    from django.core.files.storage import default_storage
    ext = os.path.splitext(f.name)[1] or ".jpg"
    path = default_storage.save(f"uploads/{request.tg_user.id}{ext}", f)
    url = request.build_absolute_uri(f"/media/{path}")
    return JsonResponse({"ok": True, "url": url})


@csrf_exempt
@webapp_api
def upload_avatar(request):
    """Foydalanuvchi avatarini yuklash."""
    if request.method != "POST":
        return _err("POST kerak", 405)
    f = request.FILES.get("avatar")
    if not f:
        return _err("'avatar' fayli kerak")
    if f.size > 5 * 1024 * 1024:
        return _err("Fayl 5MB dan oshmasin")
    u = request.tg_user
    u.avatar.delete(save=False)
    u.avatar = f
    u.save(update_fields=["avatar"])
    return JsonResponse({"ok": True, "url": request.build_absolute_uri(u.avatar.url)})


@csrf_exempt
@webapp_api
def upload_shop_logo(request):
    """Salon logotipini yuklash."""
    if request.method != "POST":
        return _err("POST kerak", 405)
    shop, err = _owner_shop_or_error(request)
    if err:
        return err
    f = request.FILES.get("logo")
    if not f:
        return _err("'logo' fayli kerak")
    if f.size > 5 * 1024 * 1024:
        return _err("Fayl 5MB dan oshmasin")
    shop.logo.delete(save=False)
    shop.logo = f
    shop.save(update_fields=["logo"])
    return JsonResponse({"ok": True, "url": request.build_absolute_uri(shop.logo.url)})


@csrf_exempt
@webapp_api
def update_barber_profile(request):
    """Barber profili va salon ma'lumotlarini yangilash."""
    if request.method != "POST":
        return _err("POST kerak", 405)
    u = request.tg_user
    if not u.is_barber or not hasattr(u, "barber_profile"):
        return _err("Barber emas", 403)

    body = json.loads(request.body or b"{}")
    bp = u.barber_profile

    # User fields
    updated_user = []
    for field in ("first_name", "last_name", "phone"):
        val = (body.get(field) or "").strip()
        if val:
            setattr(u, field, val)
            updated_user.append(field)
    if updated_user:
        u.save(update_fields=updated_user)

    # Avatar
    avatar_url = body.get("avatar_url", "")

    # BarberProfile fields
    bp_updated = []
    if body.get("bio") is not None:
        bp.bio = body["bio"].strip()
        bp_updated.append("bio")
    if body.get("specialization") in ("men", "women", "all"):
        bp.specialization = body["specialization"]
        bp_updated.append("specialization")
    if body.get("experience_years") is not None:
        bp.experience_years = int(body["experience_years"] or 0)
        bp_updated.append("experience_years")
    if bp_updated:
        bp.save(update_fields=bp_updated)

    # Shop fields
    shop = bp.shop
    shop_updated = []
    for field in ("name", "address", "phone"):
        val = (body.get(f"shop_{field}") or "").strip()
        if val:
            setattr(shop, field, val)
            shop_updated.append(field)
    if shop_updated:
        shop.save(update_fields=shop_updated)

    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# Shop management (owner only)
# ---------------------------------------------------------------------------

def _owner_shop_or_error(request):
    """Return (shop, None) if current user owns a shop, else (None, error)."""
    u = request.tg_user
    if not hasattr(u, "barber_profile"):
        return None, _err("Barber emas", 403)
    shop = u.barber_profile.shop
    if shop.owner_id != u.id:
        return None, _err("Faqat salon egasi o'zgartira oladi", 403)
    return shop, None


@csrf_exempt
@webapp_api
def shop_update(request):
    """Salon ma'lumotlarini yangilash (egasi uchun): nomi, tavsif, manzil, tel."""
    if request.method != "POST":
        return _err("POST kerak", 405)
    shop, err = _owner_shop_or_error(request)
    if err:
        return err
    body = json.loads(request.body or b"{}")

    updated = []
    name = (body.get("name") or "").strip()
    if name:
        shop.name = name[:200]
        updated.append("name")
    for field in ("city", "address", "phone", "description", "instagram_url", "telegram_url"):
        if body.get(field) is not None:
            setattr(shop, field, (body.get(field) or "").strip())
            updated.append(field)

    # Joylashuv (ixtiyoriy) — lat/lng birga keladi yoki tozalanadi
    if "latitude" in body or "longitude" in body:
        lat, lng = body.get("latitude"), body.get("longitude")
        if lat in (None, "") or lng in (None, ""):
            shop.latitude = shop.longitude = None
        else:
            try:
                lat_f, lng_f = float(lat), float(lng)
                if not (-90 <= lat_f <= 90 and -180 <= lng_f <= 180):
                    return _err("Koordinatalar noto'g'ri")
                shop.latitude, shop.longitude = round(lat_f, 6), round(lng_f, 6)
            except (TypeError, ValueError):
                return _err("Koordinatalar noto'g'ri")
        updated += ["latitude", "longitude"]

    if updated:
        shop.save(update_fields=updated)
    return JsonResponse({"ok": True, "slug": shop.slug, "name": shop.name})


@csrf_exempt
@webapp_api
def upload_shop_cover(request):
    """Salon muqova (cover) rasmini yuklash — egasi uchun."""
    if request.method != "POST":
        return _err("POST kerak", 405)
    shop, err = _owner_shop_or_error(request)
    if err:
        return err
    f = request.FILES.get("cover")
    if not f:
        return _err("'cover' fayli kerak")
    if f.size > 5 * 1024 * 1024:
        return _err("Fayl 5MB dan oshmasin")
    shop.cover.delete(save=False)
    shop.cover = f
    shop.save(update_fields=["cover"])
    return JsonResponse({"ok": True, "url": request.build_absolute_uri(shop.cover.url)})


@csrf_exempt
@webapp_api
def shop_delete(request):
    """Salonni butunlay o'chirish (egasi uchun) — sartaroshlar ham o'chadi (CASCADE)."""
    if request.method != "POST":
        return _err("POST kerak", 405)
    shop, err = _owner_shop_or_error(request)
    if err:
        return err
    barbers_count = shop.barbers.count()
    # Bronlarni avval o'chiramiz: Appointment.service PROTECT bo'lgani uchun
    # aks holda salon o'chishida Service cascade ProtectedError beradi.
    Appointment.objects.filter(shop=shop).delete()
    shop.delete()  # Service, BarberProfile, WorkingHours, JoinRequest lar CASCADE bilan o'chadi
    # Egadan barber rolini olib tashlaymiz (endi salonsiz)
    u = request.tg_user
    if u.role == User.Role.BARBER:
        u.role = User.Role.CLIENT
        u.save(update_fields=["role"])
    return JsonResponse({"ok": True, "deleted_barbers": barbers_count})


# ---------------------------------------------------------------------------
# Salonga qo'shilish so'rovlari (join requests)
# ---------------------------------------------------------------------------

@csrf_exempt
@webapp_api
def join_request_create(request):
    """Barber boshqa salonga qo'shilish so'rovini yuboradi."""
    if request.method != "POST":
        return _err("POST kerak", 405)
    from apps.shops.models import Shop, ShopJoinRequest
    u = request.tg_user
    if not hasattr(u, "barber_profile"):
        return _err("Avval barber sifatida ro'yxatdan o'ting", 403)

    body = json.loads(request.body or b"{}")
    shop_id = (body.get("shop_id") or "").strip()
    try:
        shop = Shop.objects.get(id=shop_id, is_active=True)
    except Shop.DoesNotExist:
        return _err("Salon topilmadi", 404)

    if shop.owner_id == u.id or u.barber_profile.shop_id == shop.id:
        return _err("Siz allaqachon shu salondasiz")

    existing = ShopJoinRequest.objects.filter(
        barber=u, shop=shop, status=ShopJoinRequest.Status.PENDING
    ).first()
    if existing:
        return _err("So'rov allaqachon yuborilgan, javob kutilmoqda")

    jr = ShopJoinRequest.objects.create(
        barber=u, shop=shop,
        message=(body.get("message") or "").strip()[:300],
    )

    # Salon egasiga xabar
    from django_q.tasks import async_task
    async_task("apps.notifications.tasks.notify_join_request", str(jr.id))

    return JsonResponse({"ok": True, "request_id": str(jr.id)}, status=201)


@webapp_api
@require_GET
def my_join_requests(request):
    """Barberning o'z so'rovlari holati."""
    from apps.shops.models import ShopJoinRequest
    u = request.tg_user
    reqs = ShopJoinRequest.objects.filter(barber=u).select_related("shop")[:20]
    return JsonResponse({"requests": [{
        "id": str(r.id),
        "shop_name": r.shop.name,
        "status": r.status,
        "status_display": r.get_status_display(),
    } for r in reqs]})


@webapp_api
@require_GET
def join_requests_list(request):
    """Salon egasi uchun: kutilayotgan qo'shilish so'rovlari."""
    from apps.shops.models import ShopJoinRequest
    shop, err = _owner_shop_or_error(request)
    if err:
        return err
    reqs = ShopJoinRequest.objects.filter(
        shop=shop, status=ShopJoinRequest.Status.PENDING
    ).select_related("barber")
    data = [{
        "id": str(r.id),
        "barber_name": r.barber.get_full_name() or r.barber.username,
        "barber_phone": r.barber.phone,
        "message": r.message,
        "experience_years": getattr(getattr(r.barber, "barber_profile", None), "experience_years", 0),
    } for r in reqs]
    return JsonResponse({"requests": data, "count": len(data)})


@csrf_exempt
@webapp_api
def join_request_respond(request, request_id):
    """Salon egasi so'rovni qabul qiladi yoki rad etadi."""
    if request.method != "POST":
        return _err("POST kerak", 405)
    from apps.shops.models import ShopJoinRequest
    shop, err = _owner_shop_or_error(request)
    if err:
        return err
    body = json.loads(request.body or b"{}")
    action = body.get("action")
    try:
        jr = ShopJoinRequest.objects.select_related("barber", "shop").get(
            id=request_id, shop=shop, status=ShopJoinRequest.Status.PENDING
        )
    except ShopJoinRequest.DoesNotExist:
        return _err("So'rov topilmadi", 404)

    if action == "approve":
        barber_user = jr.barber
        bp = getattr(barber_user, "barber_profile", None)
        old_shop = bp.shop if bp else None
        if bp:
            bp.shop = shop
            bp.save(update_fields=["shop"])
        jr.status = ShopJoinRequest.Status.APPROVED
        jr.save(update_fields=["status", "updated_at"])
        # Barberning eski shaxsiy (bo'sh) salonini tozalash
        if old_shop and old_shop.id != shop.id and old_shop.owner_id == barber_user.id \
                and old_shop.barbers.count() == 0:
            old_shop.delete()
        # Boshqa kutilayotgan so'rovlarini bekor qilish
        ShopJoinRequest.objects.filter(
            barber=barber_user, status=ShopJoinRequest.Status.PENDING
        ).exclude(id=jr.id).update(status=ShopJoinRequest.Status.REJECTED)
        from django_q.tasks import async_task
        async_task("apps.notifications.tasks.notify_join_response", str(jr.id))
        return JsonResponse({"ok": True, "status": "approved"})

    elif action == "reject":
        jr.status = ShopJoinRequest.Status.REJECTED
        jr.save(update_fields=["status", "updated_at"])
        from django_q.tasks import async_task
        async_task("apps.notifications.tasks.notify_join_response", str(jr.id))
        return JsonResponse({"ok": True, "status": "rejected"})

    return _err("action noto'g'ri (approve/reject)")


# ---------------------------------------------------------------------------
# Support / Contact
# ---------------------------------------------------------------------------

@csrf_exempt
@webapp_api
def support_message(request):
    """Foydalanuvchidan xabar qabul qilish."""
    if request.method != "POST":
        return _err("POST kerak", 405)
    body = json.loads(request.body or b"{}")
    msg = (body.get("message") or "").strip()
    if not msg:
        return _err("Xabar bo'sh bo'lishi mumkin emas")
    if len(msg) > 2000:
        return _err("Xabar 2000 belgidan oshmasin")

    u = request.tg_user
    from apps.core.models import ContactMessage
    cm = ContactMessage.objects.create(
        user=u,
        message=msg,
        telegram_username=u.telegram_username or u.username,
    )

    # Async email notification
    from django_q.tasks import async_task
    async_task("apps.telegram_bot.api_views._send_support_email", str(cm.id))

    return JsonResponse({"ok": True})


def _send_support_email(cm_id: str):
    """Background task: support emailni yuborish."""
    from apps.core.models import ContactMessage
    from django.core.mail import send_mail
    from django.conf import settings
    try:
        cm = ContactMessage.objects.select_related("user").get(id=cm_id)
        user_info = f"@{cm.telegram_username}" if cm.telegram_username else "Noma'lum"
        send_mail(
            subject=f"[BarberShop] Yangi murojaat — {user_info}",
            message=f"Foydalanuvchi: {user_info}\nVaqt: {cm.created_at:%d.%m.%Y %H:%M}\n\nXabar:\n{cm.message}",
            from_email=settings.EMAIL_HOST_USER or "noreply@barbershop.uz",
            recipient_list=[settings.SUPPORT_EMAIL],
            fail_silently=True,
        )
    except Exception:
        pass
