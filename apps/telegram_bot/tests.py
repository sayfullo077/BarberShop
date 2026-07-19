"""
Ko'rinish darvozasi (moderatsiya) va ishonch balli (Bayesian reyting) testlari.
_public_shops_qs — chala/soxta/bloklangan salonlar omma oldida ko'rinmasligi kafolati.
"""
from django.test import TestCase

from apps.telegram_bot.api_views import _public_shops_qs, _trust_score, _ranked
from apps.core.test_utils import make_shop, make_service


class PublicShopsGateTests(TestCase):
    def _visible_shop(self):
        """Barcha shartlarni qanoatlantiruvchi salon (ko'rinishi kerak)."""
        shop = make_shop()  # owner phone_verified=True, is_blocked=False
        make_service(shop, is_active=True)
        return shop

    def test_fully_valid_shop_is_visible(self):
        shop = self._visible_shop()
        self.assertIn(shop, _public_shops_qs())

    def test_shop_without_active_service_is_hidden(self):
        shop = make_shop()
        make_service(shop, is_active=False)
        self.assertNotIn(shop, _public_shops_qs())

    def test_unverified_phone_owner_is_hidden(self):
        shop = self._visible_shop()
        shop.owner.phone_verified = False
        shop.owner.save()
        self.assertNotIn(shop, _public_shops_qs())

    def test_blocked_owner_is_hidden(self):
        shop = self._visible_shop()
        shop.owner.is_blocked = True
        shop.owner.save()
        self.assertNotIn(shop, _public_shops_qs())

    def test_suspended_shop_is_hidden(self):
        shop = self._visible_shop()
        shop.is_suspended = True
        shop.save()
        self.assertNotIn(shop, _public_shops_qs())

    def test_inactive_shop_is_hidden(self):
        shop = self._visible_shop()
        shop.is_active = False
        shop.save()
        self.assertNotIn(shop, _public_shops_qs())


class TrustScoreTests(TestCase):
    def test_no_ratings_returns_prior_mean(self):
        shop = make_shop()  # rating_avg=0, rating_count=0
        # Bayesian: bahosiz salon PRIOR_MEAN (4.2) oladi
        self.assertAlmostEqual(_trust_score(shop), 4.2)

    def test_ratings_pull_score_toward_average(self):
        shop = make_shop()
        shop.rating_avg = 5.0
        shop.rating_count = 10
        shop.save()
        score = _trust_score(shop)
        # 5.0 ga yaqin, lekin prior tufayli 5.0 dan past
        self.assertGreater(score, 4.2)
        self.assertLess(score, 5.0)

    def test_many_ratings_dominate_prior(self):
        few = make_shop()
        few.rating_avg, few.rating_count = 5.0, 1
        few.save()
        many = make_shop()
        many.rating_avg, many.rating_count = 5.0, 100
        many.save()
        # Ko'p baholi 5.0 prior'ni yengib, kam baholidan yuqori ball oladi
        self.assertGreater(_trust_score(many), _trust_score(few))

    def test_ranked_orders_by_trust_score_desc(self):
        low = make_shop()
        low.rating_avg, low.rating_count = 3.0, 20
        low.save()
        high = make_shop()
        high.rating_avg, high.rating_count = 4.8, 20
        high.save()
        ranked = _ranked([low, high])
        self.assertEqual(ranked[0], high)
        self.assertEqual(ranked[1], low)
