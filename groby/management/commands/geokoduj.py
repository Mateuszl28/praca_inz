"""Geokodowanie miejsc urodzenia przez Nominatim (OSM).

Uruchomienie:
    python manage.py geokoduj
    python manage.py geokoduj --limit 50
"""
import time
import urllib.parse
import urllib.request
import json

from django.core.management.base import BaseCommand
from django.db.models import Count

from groby.models import Osoba, GeoCache


class Command(BaseCommand):
    help = 'Geokoduje miejsce_urodzenia osób przez Nominatim (OSM).'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **opt):
        miejsca = (Osoba.objects
                   .exclude(miejsce_urodzenia='')
                   .values('miejsce_urodzenia')
                   .annotate(c=Count('id'))
                   .order_by('-c')[:opt['limit']])

        zgeokodowanych, blednych = 0, 0
        for m in miejsca:
            nazwa = m['miejsce_urodzenia'][:200]
            if GeoCache.objects.filter(nazwa=nazwa).exists():
                continue
            try:
                q = urllib.parse.quote_plus(nazwa + ', Polska')
                url = f'https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1'
                req = urllib.request.Request(url, headers={'User-Agent': 'Cmentarz-Szydlow/1.0'})
                with urllib.request.urlopen(req, timeout=10) as r:
                    dane = json.loads(r.read().decode('utf-8'))
                if dane:
                    GeoCache.objects.create(
                        nazwa=nazwa,
                        lat=float(dane[0]['lat']),
                        lng=float(dane[0]['lon']),
                        znaleziono=True,
                    )
                    zgeokodowanych += 1
                    self.stdout.write(f'  ✓ {nazwa} → ({dane[0]["lat"]}, {dane[0]["lon"]})')
                else:
                    GeoCache.objects.create(nazwa=nazwa, znaleziono=False)
                    blednych += 1
                time.sleep(1.1)  # Limit Nominatim 1 req/s
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ✗ {nazwa}: {e}'))
                blednych += 1
        self.stdout.write(self.style.SUCCESS(f'Zgeokodowano: {zgeokodowanych}, błędów: {blednych}'))
