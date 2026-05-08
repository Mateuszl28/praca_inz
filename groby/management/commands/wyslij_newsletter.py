"""Wysyła miesięczny newsletter z najbliższymi rocznicami i nowymi wpisami.

Uruchomienie:
    python manage.py wyslij_newsletter
    python manage.py wyslij_newsletter --dry-run
"""
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from groby.models import Newsletter, Wpis, Osoba


class Command(BaseCommand):
    help = 'Wysyła newsletter do aktywnych subskrybentów.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Pokaż tylko ile wysłalibyśmy.')

    def handle(self, *args, **opt):
        dzis = date.today()
        za_30 = dzis + timedelta(days=30)

        rocznice = []
        for o in Osoba.objects.exclude(data_smierci__isnull=True).select_related('grob__sektor'):
            try:
                r = o.data_smierci.replace(year=dzis.year)
            except ValueError:
                r = o.data_smierci.replace(year=dzis.year, day=28)
            if dzis <= r <= za_30:
                rocznice.append((r, o))
        rocznice.sort(key=lambda x: x[0])

        nowe_wpisy = list(Wpis.objects.filter(opublikowany=True).order_by('-data_publikacji', '-data_dodania')[:5])

        subskrybenci = Newsletter.objects.filter(aktywny=True)
        liczba = subskrybenci.count()

        if opt['dry_run']:
            self.stdout.write(f'Wysłałbym do {liczba} subskrybentów:')
            self.stdout.write(f'  - {len(rocznice)} rocznic w ciągu 30 dni')
            self.stdout.write(f'  - {len(nowe_wpisy)} nowych wpisów')
            return

        wyslano = 0
        for n in subskrybenci:
            tresc = (
                f'Cześć,\n\nNajbliższe rocznice śmierci ({len(rocznice)}):\n'
                + '\n'.join(f'  - {r:%d.%m}: {o.imie} {o.nazwisko} (sekt. {o.grob.sektor.nazwa})' for r, o in rocznice[:10])
                + '\n\nNowe wpisy:\n'
                + '\n'.join(f'  - {w.tytul}' for w in nowe_wpisy)
                + f'\n\nAby anulować: /newsletter/anuluj/{n.token_anulowania}/\n'
            )
            try:
                EmailMultiAlternatives(
                    subject='Newsletter — Cmentarz Szydłów',
                    body=tresc,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[n.email],
                ).send(fail_silently=True)
                n.ostatnia_wysylka = timezone.now()
                n.save(update_fields=['ostatnia_wysylka'])
                wyslano += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Błąd dla {n.email}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Wysłano {wyslano}/{liczba} maili.'))
