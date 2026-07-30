from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Category, Product, Restaurant, StaffMember


class ProductBulkActionTestCase(TestCase):
    """Covers restaurants/views.py::product_bulk_action - lets an admin/owner
    apply one action to a batch of selected products at once."""

    def setUp(self):
        self.owner = User.objects.create_user(username='bulkowner', password='pw12345!', subscription_plan='pro')
        self.restaurant = Restaurant.objects.create(user=self.owner, name='Bulk Test Restaurant')

        self.employee = User.objects.create_user(username='bulkemployee', password='pw12345!')
        StaffMember.objects.create(user=self.employee, restaurant=self.restaurant, role='employee')

        self.category = Category.objects.create(restaurant=self.restaurant, name='Mains')
        self.other_category = Category.objects.create(restaurant=self.restaurant, name='Drinks')
        self.p1 = Product.objects.create(category=self.category, name='Burger', price=Decimal('10.00'), is_available=False)
        self.p2 = Product.objects.create(category=self.category, name='Fries', price=Decimal('4.00'), is_available=False)

        self.other_owner = User.objects.create_user(username='bulkother', password='pw12345!', subscription_plan='pro')
        self.other_product = Product.objects.create(
            category=Category.objects.create(restaurant=Restaurant.objects.create(user=self.other_owner, name='Other'), name='Other Mains'),
            price=Decimal('5.00'),
        )

        self.url = reverse('product_bulk_action')

    def test_mark_available(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, {'bulk_action': 'mark_available', 'product_ids': [self.p1.id, self.p2.id]})
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertTrue(self.p1.is_available)
        self.assertTrue(self.p2.is_available)

    def test_move_category(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, {
            'bulk_action': 'move_category', 'product_ids': [self.p1.id], 'target_category': self.other_category.id,
        })
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.category_id, self.other_category.id)

    def test_delete(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, {'bulk_action': 'delete', 'product_ids': [self.p1.id, self.p2.id]})
        self.assertEqual(Product.objects.filter(category__restaurant=self.restaurant).count(), 0)

    def test_cannot_touch_another_restaurants_products(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, {'bulk_action': 'delete', 'product_ids': [self.other_product.id]})
        self.assertTrue(Product.objects.filter(pk=self.other_product.id).exists())

    def test_employee_forbidden(self):
        self.client.force_login(self.employee)
        response = self.client.post(self.url, {'bulk_action': 'mark_available', 'product_ids': [self.p1.id]})
        self.assertEqual(response.status_code, 403)
        self.p1.refresh_from_db()
        self.assertFalse(self.p1.is_available)

    def test_rejects_get(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
