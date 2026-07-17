from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from .models import Shop, BarberProfile
from apps.services.models import Service
from apps.portfolio.models import PortfolioPost


def home(request):
    shops = Shop.objects.filter(is_active=True).select_related("owner")[:6]
    return render(request, "pages/home.html", {"shops": shops})


class ShopListView(ListView):
    model = Shop
    template_name = "pages/shops.html"
    context_object_name = "shops"
    paginate_by = 12
    queryset = Shop.objects.filter(is_active=True).select_related("owner")


class ShopDetailView(DetailView):
    model = Shop
    template_name = "pages/shop_detail.html"
    context_object_name = "shop"
    slug_field = "slug"

    def get_queryset(self):
        return Shop.objects.filter(is_active=True).prefetch_related(
            "barbers__user", "working_hours", "services"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        shop = self.object
        ctx["services"] = shop.services.filter(is_active=True).select_related("category")
        ctx["barbers"] = shop.barbers.filter(is_accepting_bookings=True).select_related("user")
        ctx["portfolio"] = PortfolioPost.objects.filter(
            shop=shop, is_active=True
        ).order_by("-created_at")[:12]
        return ctx


class BarberDetailView(DetailView):
    model = BarberProfile
    template_name = "pages/barber_detail.html"
    context_object_name = "barber"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        barber = self.object
        ctx["services"] = Service.objects.filter(
            barbers=barber, is_active=True
        ).select_related("category")
        ctx["portfolio"] = PortfolioPost.objects.filter(
            barber=barber, is_active=True
        ).order_by("-created_at")[:9]
        return ctx
