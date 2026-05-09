"""Wysyła przypomnienia o rocznicach śmierci do obserwujących, na 7 dni przed.

Cron sugerowany: codziennie rano.
"""
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.urls import reverse

from groby.models import Osoba


class Command(BaseCommand):
    help = 'Wysyła przypomnienia o rocznicach śmierci na 7 dni przed.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--dni', type=int, default=7, help='Ile dni przed rocznicą.')

    def handle(self, *args, **opt):
        cel_data = date.today() + timedelta(days=opt['dni'])
        wyslano = 0
        for osoba in Osoba.objects.filter(data_smierci__month=cel_data.month, data_smierci__day=cel_data.day).select_related('grob__sektor'):
            obserwujacy_emaile = list(
                osoba.obserwujacy.exclude(user__email='').values_list('user__email', flat=True)
            )
            for grob_obs in osoba.grob.obserwujacy.exclude(user__email=''):
                if grob_obs.user.email not in obserwujacy_emaile:
                    obserwujacy_emaile.append(grob_obs.user.email)
            if not obserwujacy_emaile:
                continue
            lat = cel_data.year - osoba.data_smierci.year
            tytul = f'{lat}. rocznica śmierci — {osoba.imie} {osoba.nazwisko}'
            tresc = (
                f'Za {opt["dni"]} dni ({cel_data.strftime("%d.%m.%Y")}) {lat}. rocznica śmierci '
                f'osoby, którą obserwujesz: {osoba.imie} {osoba.nazwisko}.\n'
                f'Sektor {osoba.grob.sektor.nazwa}, grób {osoba.grob.numer}.\n'
            )
            if not opt['dry_run']:
                try:
                    send_mail(tytul, tresc, settings.DEFAULT_FROM_EMAIL, obserwujacy_emaile, fail_silently=True)
                    wyslano += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Błąd: {e}'))
            else:
                self.stdout.write(f'[DRY] {tytul} → {obserwujacy_emaile}')
        self.stdout.write(self.style.SUCCESS(f'Wysłano: {wyslano} przypomnień'))
