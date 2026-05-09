"""Auto-resize wszystkich zdjęć w galerii do max 2000px (oszczędność dysku)."""
import os
from PIL import Image
from django.conf import settings
from django.core.management.base import BaseCommand

from groby.models import Zdjecie


class Command(BaseCommand):
    help = 'Resize wszystkich zdjęć do max-szer 2000px.'

    def add_arguments(self, parser):
        parser.add_argument('--max', type=int, default=2000)
        parser.add_argument('--quality', type=int, default=85)

    def handle(self, *args, **opt):
        max_w = opt['max']
        zoptymalizowanych = 0
        zaoszczedzono = 0
        for z in Zdjecie.objects.all():
            try:
                sciezka = z.plik.path
            except (NotImplementedError, ValueError):
                continue
            if not os.path.isfile(sciezka):
                continue
            try:
                rozmiar_przed = os.path.getsize(sciezka)
                with Image.open(sciezka) as im:
                    if im.width <= max_w and im.height <= max_w:
                        continue
                    im.thumbnail((max_w, max_w))
                    if im.mode in ('RGBA', 'P'):
                        im = im.convert('RGB')
                    im.save(sciezka, optimize=True, quality=opt['quality'])
                rozmiar_po = os.path.getsize(sciezka)
                zaoszczedzono += rozmiar_przed - rozmiar_po
                zoptymalizowanych += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ✗ {sciezka}: {e}'))
        self.stdout.write(self.style.SUCCESS(
            f'Zoptymalizowano: {zoptymalizowanych}, zaoszczędzono: {zaoszczedzono / (1024*1024):.1f} MB'
        ))
