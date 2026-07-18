from django.db import migrations


def grandfather(apps, schema_editor):
    """Mavjud barber/owner'larни haqiqiy telefonلی bo'lsa (>=7 raqam) tasdiqlangan
    deb belgilaymiz — yangi darvoza tufayli ular ro'yxatdan g'oyib bo'lmasin.
    Chala/soxta (masalan 'asd' — 0 raqam) tasdiqlanmaydi, yashirin qoladi."""
    User = apps.get_model("accounts", "User")
    for u in User.objects.filter(role__in=["barber", "owner"]).exclude(phone=""):
        digits = sum(ch.isdigit() for ch in (u.phone or ""))
        if digits >= 7:
            u.phone_verified = True
            u.save(update_fields=["phone_verified"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_is_blocked_user_phone_verified"),
    ]
    operations = [
        migrations.RunPython(grandfather, noop),
    ]
