import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.test.client import Client
from django.urls import reverse
from groby.models import Osoba, Grob, Sektor, Wpis


class Command(BaseCommand):
    help = 'Eksportuje strony do statycznego HTML (do hostingu na GitHub Pages itd.).'

    def add_arguments(self, parser):
        parser.add_argument('--out', default='static_export', help='Katalog wyjściowy')
        parser.add_argument('--limit-osoby', type=int, default=1000)

    def handle(self, *args, **opt):
        out = Path(opt['out'])
        out.mkdir(exist_ok=True)
        c = Client()

        urls = [
            ('home', '/', 'index.html'),
            ('mapa', '/mapa/', 'mapa.html'),
            ('sektory', '/sektory/', 'sektory.html'),
            ('o-cmentarzu', '/o-cmentarzu/', 'o-cmentarzu.html'),
            ('indeks', '/indeks/', 'indeks.html'),
            ('statystyki', '/statystyki/', 'statystyki.html'),
            ('faq', '/faq/', 'faq.html'),
        ]
        for nazwa, url, plik in urls:
            r = c.get(url)
            if r.status_code == 200:
                (out / plik).write_bytes(r.content)
                self.stdout.write(f'  {plik}')

        (out / 'osoba').mkdir(exist_ok=True)
        for o in Osoba.objects.select_related('grob')[:opt['limit_osoby']]:
            r = c.get(f'/osoba/{o.pk}/')
            if r.status_code == 200:
                (out / 'osoba' / f'{o.pk}.html').write_bytes(r.content)
        self.stdout.write(self.style.SUCCESS(f'Wyeksportowano do {out.resolve()}'))
