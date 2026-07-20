from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import User
from restaurants.models import Restaurant, Category, Product

# Fixed demo usernames, never exposed to real signups - safe to hardcode and idempotently
# re-run. These accounts have no usable login (random unset password) and allow_ordering
# is left off, so no real order/email flow can be triggered by a visitor on these pages.
DEMO_RESTAURANTS = [
    {
        'username': 'demo_cafe',
        'name': 'Aroma Coffee House',
        'description': 'A neighborhood cafe menu, built with MenuHub in a few minutes.',
        'categories': [
            {
                'name': 'Coffee',
                'products': [
                    ('Espresso', 'Double shot, rich and bold.', '2.50', {}),
                    ('Cappuccino', 'Espresso, steamed milk, thick foam.', '3.50', {}),
                    ('Iced Latte', 'Espresso over ice with cold milk.', '4.00', {}),
                ],
            },
            {
                'name': 'Breakfast',
                'products': [
                    ('Avocado Toast', 'Sourdough, smashed avocado, chili flakes, lemon.', '7.50', {'is_vegan': True}),
                    ('Greek Yogurt Bowl', 'Greek yogurt, honey, granola, seasonal fruit.', '6.50', {'is_vegetarian': True}),
                ],
            },
            {
                'name': 'Pastries',
                'products': [
                    ('Almond Croissant', 'Butter croissant, almond cream, sliced almonds.', '4.50', {'is_vegetarian': True}),
                    ('Chocolate Muffin', 'Rich cocoa muffin with dark chocolate chunks.', '3.75', {'is_vegetarian': True}),
                ],
            },
        ],
    },
    {
        'username': 'demo_taverna',
        'name': 'Elia Taverna',
        'description': 'A traditional taverna menu, updated the same day the daily specials change.',
        'categories': [
            {
                'name': 'Starters',
                'products': [
                    ('Tzatziki', 'Greek yogurt, cucumber, garlic, olive oil.', '5.00', {'is_vegetarian': True, 'is_gluten_free': True}),
                    ('Grilled Octopus', 'Charcoal-grilled octopus with lemon and oregano.', '14.00', {'is_gluten_free': True}),
                    ('Saganaki', 'Pan-seared cheese, flambeed with brandy.', '8.50', {'is_vegetarian': True}),
                ],
            },
            {
                'name': 'Mains',
                'products': [
                    ('Moussaka', 'Layered eggplant, potato, and beef with bechamel.', '13.50', {}),
                    ('Grilled Sea Bream', 'Whole fish, grilled, with olive oil and lemon.', '18.00', {'is_gluten_free': True}),
                    ('Souvlaki Plate', 'Grilled pork skewers, pita, fries, tzatziki.', '12.00', {}),
                ],
            },
            {
                'name': 'Salads',
                'products': [
                    ('Greek Salad', 'Tomato, cucumber, onion, olives, feta.', '8.00', {'is_vegetarian': True, 'is_gluten_free': True}),
                ],
            },
        ],
    },
    {
        'username': 'demo_beachbar',
        'name': 'Ammos Beach Bar',
        'description': 'A beach bar menu built for ordering straight from the sunbed.',
        'categories': [
            {
                'name': 'Cocktails',
                'products': [
                    ('Mojito', 'White rum, lime, mint, soda.', '9.00', {'is_vegan': True}),
                    ('Aperol Spritz', 'Aperol, prosecco, soda, orange slice.', '9.50', {'is_vegan': True}),
                    ('Frozen Margarita', 'Tequila, triple sec, lime, blended with ice.', '10.00', {'is_vegan': True}),
                ],
            },
            {
                'name': 'Coffee & Frappe',
                'products': [
                    ('Freddo Espresso', 'Double espresso, shaken over ice.', '3.50', {'is_vegan': True}),
                    ('Freddo Cappuccino', 'Iced espresso topped with cold frothed milk.', '4.00', {'is_vegetarian': True}),
                ],
            },
            {
                'name': 'Snacks',
                'products': [
                    ('Club Sandwich', 'Chicken, bacon, lettuce, tomato, fries.', '9.50', {}),
                    ('Watermelon & Feta', 'Chilled watermelon slices with feta and mint.', '6.00', {'is_vegetarian': True, 'is_gluten_free': True}),
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = 'Idempotently creates/updates the demo restaurants shown on the /examples/ showcase page.'

    def handle(self, *args, **options):
        for entry in DEMO_RESTAURANTS:
            user, user_created = User.objects.get_or_create(
                username=entry['username'],
                defaults={'email': '', 'business_name': entry['name']},
            )
            if user_created:
                user.set_unusable_password()
                user.save()

            restaurant, _r_created = Restaurant.objects.update_or_create(
                user=user,
                defaults={
                    'name': entry['name'],
                    'description': entry['description'],
                    'is_active': True,
                    'allow_ordering': False,
                },
            )

            for cat_order, cat_data in enumerate(entry['categories']):
                category, _c_created = Category.objects.update_or_create(
                    restaurant=restaurant,
                    name=cat_data['name'],
                    defaults={'order': cat_order, 'is_active': True},
                )
                for prod_order, (name, description, price, flags) in enumerate(cat_data['products']):
                    Product.objects.update_or_create(
                        category=category,
                        name=name,
                        defaults={
                            'description': description,
                            'price': Decimal(price),
                            'is_available': True,
                            'order': prod_order,
                            **flags,
                        },
                    )

            self.stdout.write(self.style.SUCCESS(
                f'{entry["name"]} -> /menu/{restaurant.qr_code_token}/'
            ))
