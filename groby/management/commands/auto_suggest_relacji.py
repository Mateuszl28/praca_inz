from django.core.management.base import BaseCommand
from django.db.models import Q
from groby.models import Osoba, Relacja


class Command(BaseCommand):
    help = 'Sugeruje kandydatów relacji rodzinnych na podstawie współdzielonego grobu i nazwiska.'

    def add_arguments(self, parser):
        parser.add_argument('--zapisz', action='store_true', help='Zapisz znalezione relacje do bazy')
        parser.add_argument('--limit', type=int, default=200)

    def handle(self, *args, **opt):
        zapisz = opt['zapisz']
        limit = opt['limit']
        kandydaci = []

        for osoba in Osoba.objects.exclude(grob__isnull=True).select_related('grob')[:5000]:
            if not osoba.nazwisko:
                continue
            wspolgrob = Osoba.objects.filter(grob=osoba.grob).exclude(pk=osoba.pk)
            for inna in wspolgrob:
                if not inna.nazwisko:
                    continue
                if inna.nazwisko.lower() != osoba.nazwisko.lower():
                    if osoba.nazwisko_rodowe and inna.nazwisko and \
                       osoba.nazwisko_rodowe.lower() == inna.nazwisko.lower():
                        kandydaci.append((osoba, inna, 'corka_ojca'))
                    continue
                if osoba.data_urodzenia and inna.data_urodzenia:
                    diff = abs((osoba.data_urodzenia - inna.data_urodzenia).days) / 365.25
                    if 15 <= diff <= 45:
                        kandydaci.append((osoba, inna, 'rodzic_dziecko'))
                    elif diff <= 5:
                        kandydaci.append((osoba, inna, 'rodzenstwo'))

        kandydaci = kandydaci[:limit]
        self.stdout.write(self.style.SUCCESS(f'Znaleziono {len(kandydaci)} kandydatów relacji.'))

        for a, b, typ in kandydaci[:30]:
            self.stdout.write(f'  {a} ↔ {b}  ({typ})')

        if zapisz:
            zapisanych = 0
            for a, b, typ in kandydaci:
                if typ == 'rodzic_dziecko':
                    starszy, mlodszy = (a, b) if a.data_urodzenia < b.data_urodzenia else (b, a)
                    if not Relacja.objects.filter(
                        Q(osoba_a=starszy, osoba_b=mlodszy) | Q(osoba_a=mlodszy, osoba_b=starszy)
                    ).exists():
                        Relacja.objects.create(osoba_a=starszy, osoba_b=mlodszy, typ='rodzic')
                        zapisanych += 1
                elif typ == 'rodzenstwo':
                    if not Relacja.objects.filter(
                        Q(osoba_a=a, osoba_b=b) | Q(osoba_a=b, osoba_b=a)
                    ).exists():
                        Relacja.objects.create(osoba_a=a, osoba_b=b, typ='rodzenstwo')
                        zapisanych += 1
            self.stdout.write(self.style.SUCCESS(f'Zapisano {zapisanych} relacji.'))
