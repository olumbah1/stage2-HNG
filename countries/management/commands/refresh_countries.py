from django.core.management.base import BaseCommand
from countries.views import CountryViewSet

class Command(BaseCommand):
    help = 'Refresh countries data from external APIs'

    def handle(self, *args, **options):
        view = CountryViewSet()
        view.refresh(None)
        self.stdout.write(self.style.SUCCESS('Countries refreshed successfully'))