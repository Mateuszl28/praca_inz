"""
Wczytuje rzeczywiste pozycje grobów odczytane ze skanu planu z oznaczeniami.

Plik JSON (domyślnie groby/data/pozycje_grobow.json) zawiera współrzędne
środków nagrobków w pikselach pełnej rozdzielczości skanu
„scan_ z_OZNACZENIAMI.JPG”:
    {"skan": [8292, 24250], "sektory": {"A": {"I": {"1": [x, y], ...}}}}

Współrzędne są przeliczane na rozmiar obrazu planu używanego na /mapa/
(settings.PLAN_IMAGE) i zapisywane w plan_x / plan_y.

Wywołanie:
    python manage.py pozycje_z_planu
    python manage.py pozycje_z_planu --dry-run
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from groby.models import Grob

DOMYSLNY_PLIK = Path(__file__).resolve().parents[2] / 'data' / 'pozycje_grobow.json'


class Command(BaseCommand):
    help = 'Ustawia plan_x/plan_y grobów na podstawie pozycji odczytanych ze skanu planu.'

    def add_arguments(self, parser):
        parser.add_argument('--plik', type=str, default=str(DOMYSLNY_PLIK), help='Plik JSON z pozycjami.')
        parser.add_argument('--dry-run', action='store_true', help='Nie zapisuj, pokaż tylko podsumowanie.')

    def handle(self, *args, **options):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None

        try:
            dane = json.loads(Path(options['plik']).read_text(encoding='utf-8'))
        except FileNotFoundError:
            raise CommandError(f'Nie znaleziono pliku: {options["plik"]}')

        skan_w, skan_h = dane['skan']
        try:
            with Image.open(settings.MEDIA_ROOT / settings.PLAN_IMAGE) as im:
                plan_w, plan_h = im.size
        except (FileNotFoundError, OSError):
            raise CommandError(f'Brak obrazu planu: {settings.PLAN_IMAGE}')
        sx, sy = plan_w / skan_w, plan_h / skan_h

        pozycje = {
            (sektor, rzad, numer): xy
            for sektor, rzedy in dane['sektory'].items()
            for rzad, numery in rzedy.items()
            for numer, xy in numery.items()
            if xy
        }

        zmienione, brak = 0, []
        with transaction.atomic():
            for g in Grob.objects.select_related('sektor'):
                xy = pozycje.get((g.sektor.nazwa, g.rzad, g.numer))
                if not xy:
                    brak.append(str(g))
                    continue
                g.plan_x = round(xy[0] * sx, 2)
                g.plan_y = round(xy[1] * sy, 2)
                if not options['dry_run']:
                    g.save(update_fields=['plan_x', 'plan_y', 'data_modyfikacji'])
                zmienione += 1

        self.stdout.write(self.style.SUCCESS(f'Ustawione pozycje: {zmienione}'))
        if brak:
            self.stdout.write(self.style.WARNING(f'Bez pozycji w pliku ({len(brak)}): {", ".join(brak)}'))
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('--- DRY RUN: nic nie zostało zapisane ---'))
