import json
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from restaurants.models import Category, Product, ProductOption, PromoCode, Restaurant, RestaurantTable
from .models import Order


class CreateOrderApiTestCase(TestCase):
    """Covers orders/views.py::create_order_api - the anonymous, public,
    money-handling endpoint reachable by anyone who scans a table QR code."""

    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(
            username='owner', password='pw12345!', subscription_plan='pro',
        )
        self.restaurant = Restaurant.objects.create(
            user=self.owner, name='Test Restaurant', allow_ordering=True, tax_rate=Decimal('10.00'),
        )

        self.other_owner = User.objects.create_user(
            username='other_owner', password='pw12345!', subscription_plan='pro',
        )
        self.other_restaurant = Restaurant.objects.create(user=self.other_owner, name='Other Restaurant')

        self.category = Category.objects.create(restaurant=self.restaurant, name='Mains')
        self.product = Product.objects.create(category=self.category, name='Burger', price=Decimal('10.00'))
        self.option = ProductOption.objects.create(product=self.product, name='Extra cheese', price_adjustment=Decimal('1.50'))

        self.table = RestaurantTable.objects.create(restaurant=self.restaurant, table_type='table', number='5')

        self.other_product = Product.objects.create(
            category=Category.objects.create(restaurant=self.other_restaurant, name='Other Mains'),
            price=Decimal('5.00'),
        )

        self.url = reverse('create_order_api', args=[self.restaurant.qr_code_token])

    def post(self, data):
        return self.client.post(self.url, data=json.dumps(data), content_type='application/json')

    def valid_payload(self, **overrides):
        payload = {
            'table_number': self.table.number,
            'table_type': self.table.table_type,
            'items': [{'product_id': self.product.id, 'quantity': 2, 'options': [self.option.id]}],
        }
        payload.update(overrides)
        return payload

    def test_creates_order_with_server_side_pricing(self):
        response = self.post(self.valid_payload())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['success'])

        order = Order.objects.get(pk=body['order_id'])
        # (10.00 + 1.50) * 2 = 23.00 subtotal, +10% tax = 25.30 total
        self.assertEqual(order.subtotal, Decimal('23.00'))
        self.assertEqual(order.tax, Decimal('2.30'))
        self.assertEqual(order.total, Decimal('25.30'))
        self.assertEqual(order.order_items.count(), 1)
        self.assertEqual(order.order_items.first().price, Decimal('11.50'))

    def test_client_supplied_price_is_ignored(self):
        payload = self.valid_payload(items=[{
            'product_id': self.product.id, 'quantity': 1, 'options': [], 'price': '0.01',
        }])
        response = self.post(payload)
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(pk=response.json()['order_id'])
        self.assertEqual(order.subtotal, self.product.price)

    def test_rejects_product_from_another_restaurant(self):
        payload = self.valid_payload(items=[{'product_id': self.other_product.id, 'quantity': 1, 'options': []}])
        response = self.post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertEqual(Order.objects.count(), 0)

    def test_rejects_missing_table(self):
        payload = self.valid_payload(table_number='does-not-exist')
        response = self.post(payload)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Order.objects.count(), 0)

    def test_rejects_when_ordering_not_allowed(self):
        self.restaurant.allow_ordering = False
        self.restaurant.save()
        response = self.post(self.valid_payload())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Order.objects.count(), 0)

    def test_rejects_when_plan_lacks_ordering(self):
        self.owner.subscription_plan = 'basic'
        self.owner.save()
        response = self.post(self.valid_payload())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Order.objects.count(), 0)

    def test_applies_valid_promo_code(self):
        PromoCode.objects.create(restaurant=self.restaurant, code='SAVE10', discount_percent=10)
        payload = self.valid_payload(promo_code='save10')
        response = self.post(payload)
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(pk=response.json()['order_id'])
        self.assertEqual(order.promo_code, 'SAVE10')
        self.assertEqual(order.discount, Decimal('2.30'))  # 10% of 23.00

    def test_rejects_invalid_promo_code(self):
        payload = self.valid_payload(promo_code='NOPE')
        response = self.post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_rejects_invalid_quantity(self):
        payload = self.valid_payload(items=[{'product_id': self.product.id, 'quantity': 0, 'options': []}])
        response = self.post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_rejects_empty_items(self):
        response = self.post(self.valid_payload(items=[]))
        self.assertEqual(response.status_code, 400)

    def test_rejects_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_rate_limit_blocks_after_threshold(self):
        for _ in range(10):
            response = self.post(self.valid_payload())
            self.assertEqual(response.status_code, 200)

        response = self.post(self.valid_payload())
        self.assertEqual(response.status_code, 429)
