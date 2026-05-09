"""Wysyła przypomnienia o urodzinach (jeśli znana data) do obserwujących."""
from datetime import date

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from groby.models import Osoba


class Command(BaseCommand):
    help = 'Wysyła przypomnienia o urodzinach obserwowanych osób.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opt):
        dzis = date.today()
        wyslano = 0
        for osoba in Osoba.objects.filter(data_urodzenia__month=dzis.month, data_urodzenia__day=dzis.day).select_related('grob__sektor'):
            emaile = list(osoba.obserwujacy.exclude(user__email='').values_list('user__email', flat=True))
            for grob_obs in osoba.grob.obserwujacy.exclude(user__email=''):
                if grob_obs.user.email not in emaile:
                    emaile.append(grob_obs.user.email)
            if not emaile:
                continue
            wiek = dzis.year - osoba.data_urodzenia.year if osoba.data_smierci is None else (osoba.data_smierci.year - osoba.data_urodzenia.year)
            tytul = f'Urodziny — {osoba.imie} {osoba.nazwisko}'
            tresc = f'Dziś urodziny obserwowanej osoby: {osoba.imie} {osoba.nazwisko}.\nUrodzony(a) w {osoba.data_urodzenia.year} r.\n'
            if not opt['dry_run']:
                send_mail(tytul, tresc, settings.DEFAULT_FROM_EMAIL, emaile, fail_silently=True)
                wyslano += 1
            else:
                self.stdout.write(f'[DRY] {tytul} → {emaile}')
        self.stdout.write(self.style.SUCCESS(f'Wysłano: {wyslano}'))
