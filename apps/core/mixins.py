from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class OwnerRequiredMixin(LoginRequiredMixin):
    """Allow access only to shop owners."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role != "owner":
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class BarberRequiredMixin(LoginRequiredMixin):
    """Allow access only to barbers."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role not in ("barber", "owner"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
