"""Creates a Paddle Product + Price for each subscription plan (basic/pro/business)
and prints the resulting Price ids to paste into .env as PADDLE_PRICE_BASIC/PRO/BUSINESS.

Referenced from accounts/billing.py::price_for_plan and the checkout view - until
these env vars are set, the checkout page shows "Not available yet" for every plan.

Safe to re-run: any plan whose PADDLE_PRICE_* env var is already set is skipped,
so this never creates duplicate Products/Prices in Paddle.
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts import billing
from accounts.models import PLAN_PRICES


class Command(BaseCommand):
    help = 'Creates Paddle Products/Prices for each subscription plan and prints the Price ids to add to .env.'

    def handle(self, *args, **options):
        if not settings.PADDLE_API_KEY:
            raise CommandError('PADDLE_API_KEY is not set. Add your Paddle sandbox API key to .env first.')

        existing_price_ids = {
            'basic': settings.PADDLE_PRICE_BASIC,
            'pro': settings.PADDLE_PRICE_PRO,
            'business': settings.PADDLE_PRICE_BUSINESS,
        }

        results = {}
        for plan, price_usd in PLAN_PRICES.items():
            if existing_price_ids.get(plan):
                self.stdout.write(f'{plan}: already configured ({existing_price_ids[plan]}), skipping.')
                results[plan] = existing_price_ids[plan]
                continue

            try:
                product = self._create_product(plan)
                price = self._create_price(product['id'], plan, price_usd)
            except requests.RequestException as exc:
                detail = exc.response.text if getattr(exc, 'response', None) is not None else str(exc)
                raise CommandError(f'Failed to create Paddle product/price for "{plan}": {detail}')

            results[plan] = price['id']
            self.stdout.write(self.style.SUCCESS(f'{plan}: created product {product["id"]} / price {price["id"]}'))

        self.stdout.write('')
        self.stdout.write('Add these to your .env (only the newly created ones need updating):')
        self.stdout.write(f'PADDLE_PRICE_BASIC={results.get("basic", "")}')
        self.stdout.write(f'PADDLE_PRICE_PRO={results.get("pro", "")}')
        self.stdout.write(f'PADDLE_PRICE_BUSINESS={results.get("business", "")}')

    def _create_product(self, plan):
        response = requests.post(
            f'{billing._api_base()}/products',
            headers=billing._headers(),
            json={
                'name': f'MenuHub {plan.capitalize()}',
                'tax_category': 'saas',
                'custom_data': {'plan_code': plan},
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()['data']

    def _create_price(self, product_id, plan, price_usd):
        response = requests.post(
            f'{billing._api_base()}/prices',
            headers=billing._headers(),
            json={
                'product_id': product_id,
                'description': f'MenuHub {plan.capitalize()} - monthly',
                'unit_price': {'amount': str(price_usd * 100), 'currency_code': 'USD'},
                'billing_cycle': {'interval': 'month', 'frequency': 1},
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()['data']
