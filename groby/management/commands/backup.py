"""Backup całej aplikacji do ZIP — fixture + media + plan.

Uruchomienie:
    python manage.py backup                     # do /tmp/groby-backup-RRRR-MM-DD.zip
    python manage.py backup --output /backups/  # do podanego katalogu
"""
import os
import zipfile
from datetime import date
from io import BytesIO

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Backup bazy + media do ZIP.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='/tmp', help='Katalog docelowy.')
        parser.add_argument('--media', action='store_true', default=True, help='Dołącz pliki media.')
        parser.add_argument('--keep', type=int, default=4, help='Ile ostatnich backupów zostawić (retention).')

    def handle(self, *args, **opt):
        nazwa = f'groby-backup-{date.today().isoformat()}.zip'
        sciezka = os.path.join(opt['output'], nazwa)

        # Dump JSON do pamięci
        buf = BytesIO()
        call_command(
            'dumpdata', 'groby', 'auth.User', 'auth.Group',
            indent=2, stdout=buf, format='json',
        )
        # dumpdata writes bytes to buf in some Django versions; ensure str → bytes
        try:
            dane = buf.getvalue()
            if isinstance(dane, str):
                dane = dane.encode('utf-8')
        except Exception:
            buf.seek(0)
            dane = buf.read().encode('utf-8') if isinstance(buf.read(), str) else buf.getvalue()

        with zipfile.ZipFile(sciezka, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('dump.json', dane)
            if opt['media'] and os.path.isdir(settings.MEDIA_ROOT):
                for root, _, files in os.walk(settings.MEDIA_ROOT):
                    for f in files:
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, settings.MEDIA_ROOT)
                        zf.write(full, f'media/{rel}')

        rozmiar_mb = os.path.getsize(sciezka) / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(
            f'Backup zapisany: {sciezka} ({rozmiar_mb:.1f} MB)'
        ))

        # Retention — zachowaj N ostatnich
        keep = opt['keep']
        if keep > 0:
            backupy = sorted(
                [f for f in os.listdir(opt['output']) if f.startswith('groby-backup-') and f.endswith('.zip')],
                reverse=True,
            )
            for stary in backupy[keep:]:
                stary_full = os.path.join(opt['output'], stary)
                try:
                    os.remove(stary_full)
                    self.stdout.write(f'  Usunięto stary backup: {stary}')
                except OSError:
                    pass
