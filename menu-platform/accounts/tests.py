from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from . import billing
from .models import Payment, User


class RecordPaymentFromTransactionTestCase(TestCase):
    """Paddle can deliver a transaction.payment_failed event before the
    transaction.completed event for the same transaction (e.g. an initial
    decline followed by a successful retry). The local Payment row must end
    up reflecting the transaction's final state, not whichever event arrived
    first - see accounts/billing.py::record_payment_from_transaction."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='payer', password='pw12345!', paddle_customer_id='ctm_test123',
        )

    def _transaction(self, **overrides):
        # No 'items' - price_id_to_plan() then falls back to user.subscription_plan,
        # so this test doesn't depend on real Paddle price ids being configured.
        transaction = {
            'id': 'txn_test1',
            'customer_id': 'ctm_test123',
            'currency_code': 'USD',
            'details': {'totals': {'grand_total': '1900'}},
        }
        transaction.update(overrides)
        return transaction

    def test_later_completed_event_overwrites_earlier_failed_event(self):
        billing.record_payment_from_transaction(self._transaction(), failed=True)
        payment = billing.record_payment_from_transaction(self._transaction(), failed=False)

        self.assertEqual(Payment.objects.filter(transaction_id='txn_test1').count(), 1)
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.amount, Decimal('19.00'))
        self.assertEqual(payment.failure_reason, '')

    def test_later_failed_event_overwrites_earlier_completed_event(self):
        billing.record_payment_from_transaction(self._transaction(), failed=False)
        payment = billing.record_payment_from_transaction(self._transaction(), failed=True)

        self.assertEqual(Payment.objects.filter(transaction_id='txn_test1').count(), 1)
        self.assertEqual(payment.status, 'failed')
        self.assertTrue(payment.failure_reason)


class BetaModeTestCase(TestCase):
    """While billing isn't live yet (BETA_MODE=True), every account should get
    full access regardless of plan or trial status - see
    accounts/models.py::User.has_active_subscription/has_ordering/etc."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='beta_user', password='pw12345!',
            subscription_plan='basic', subscription_active=False,
            subscription_ends=timezone.now() - timedelta(days=1),
        )

    @override_settings(BETA_MODE=True)
    def test_lapsed_basic_account_gets_full_access_in_beta(self):
        self.assertTrue(self.user.has_active_subscription())
        self.assertTrue(self.user.has_ordering())
        self.assertTrue(self.user.has_stats_dashboard())
        self.assertTrue(self.user.has_staff_management())

    @override_settings(BETA_MODE=False)
    def test_lapsed_basic_account_is_still_gated_outside_beta(self):
        self.assertFalse(self.user.has_active_subscription())
        self.assertFalse(self.user.has_ordering())
        self.assertFalse(self.user.has_stats_dashboard())
        self.assertFalse(self.user.has_staff_management())
