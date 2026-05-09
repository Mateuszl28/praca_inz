"""Import zdjęć z ZIP-a — wyciąga GPS z EXIF i przypisuje do najbliższego grobu."""
import io
import zipfile
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from groby.models import Grob, Zdjecie


def _convert_to_degrees(value):
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def _exif_gps(plik_bytes):
    try:
        from PIL import Image, ExifTags
    except ImportError:
        return None
    try:
        img = Image.open(io.BytesIO(plik_bytes))
        exif = img._getexif() or {}
        gps_idx = None
        for tag, val in ExifTags.TAGS.items():
            if val == 'GPSInfo':
                gps_idx = tag
                break
        if not gps_idx or gps_idx not in exif:
            return None
        gps = exif[gps_idx]
        lat = _convert_to_degrees(gps[2])
        if gps[1] != 'N':
            lat = -lat
        lon = _convert_to_degrees(gps[4])
        if gps[3] != 'E':
            lon = -lon
        return lat, lon
    except Exception:
        return None


class Command(BaseCommand):
    help = 'Import zdjęć z ZIP — przypisuje do najbliższego grobu na podstawie EXIF GPS.'

    def add_arguments(self, parser):
        parser.add_argument('zip_path')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--max-dist-m', type=float, default=20.0)

    def handle(self, *args, **opt):
        groby = list(Grob.objects.exclude(plan_x__isnull=True))
        if not groby:
            self.stdout.write(self.style.ERROR('Brak grobów z pozycjami — uruchom rozmiesc_groby.'))
            return

        zip_path = Path(opt['zip_path'])
        if not zip_path.exists():
            self.stdout.write(self.style.ERROR(f'Brak pliku: {zip_path}'))
            return

        with zipfile.ZipFile(zip_path) as z:
            for nazwa in z.namelist():
                if not nazwa.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                dane = z.read(nazwa)
                gps = _exif_gps(dane)
                if not gps:
                    self.stdout.write(f'  {nazwa}: brak GPS w EXIF')
                    continue

                najblizszy = min(groby, key=lambda g: (g.plan_x - gps[1])**2 + (g.plan_y - gps[0])**2)
                dist = ((najblizszy.plan_x - gps[1])**2 + (najblizszy.plan_y - gps[0])**2) ** 0.5
                self.stdout.write(f'  {nazwa}: GPS({gps[0]:.5f},{gps[1]:.5f}) -> {najblizszy} (dist={dist:.4f})')

                if not opt['dry_run']:
                    z_obj = Zdjecie(grob=najblizszy, podpis=Path(nazwa).stem[:200])
                    z_obj.plik.save(Path(nazwa).name, ContentFile(dane), save=True)
        self.stdout.write(self.style.SUCCESS('Gotowe.'))
