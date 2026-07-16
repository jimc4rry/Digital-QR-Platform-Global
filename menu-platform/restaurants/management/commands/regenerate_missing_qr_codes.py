"""One-off repair command: restaurants/tables created before persistent media
storage was set up (see MEDIA_ROOT/Volume config) have a qr_code field that
still references a file, but the file itself no longer exists on disk. This
finds those and regenerates the QR code image. Safe to re-run - it only acts
on records whose file is actually missing from storage."""
from django.core.management.base import BaseCommand

from restaurants.models import Restaurant, RestaurantTable


class Command(BaseCommand):
    help = 'Regenerates QR code images for restaurants/tables whose qr_code file is missing from storage.'

    def handle(self, *args, **options):
        fixed = 0

        for restaurant in Restaurant.objects.all():
            if restaurant.qr_code and not restaurant.qr_code.storage.exists(restaurant.qr_code.name):
                restaurant.generate_qr_code()
                restaurant.save(update_fields=['qr_code'])
                fixed += 1
                self.stdout.write(f'Regenerated QR code for restaurant "{restaurant.name}" (id={restaurant.id})')

        for table in RestaurantTable.objects.all():
            if table.qr_code and not table.qr_code.storage.exists(table.qr_code.name):
                table.generate_qr_code()
                table.save(update_fields=['qr_code'])
                fixed += 1
                self.stdout.write(f'Regenerated QR code for table "{table}" (id={table.id})')

        if fixed:
            self.stdout.write(self.style.SUCCESS(f'Done - regenerated {fixed} QR code(s).'))
        else:
            self.stdout.write('Nothing to fix - all QR code files exist.')
