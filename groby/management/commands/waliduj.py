"""Walidator danych — szuka błędów logicznych w bazie i raportuje.

Uruchomienie:
    python manage.py waliduj          # raport tekstowy
    python manage.py waliduj --json   # JSON, do CI / monitoringu
"""
import json
from datetime import date
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count

from groby.models import Grob, Osoba


class Command(BaseCommand):
    help = 'Walidator danych — wykrywa nielogiczne wpisy w bazie.'

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', help='Output w formacie JSON.')

    def handle(self, *args, **options):
        problemy = defaultdict(list)
        teraz = date.today()

        # Osoby — daty
        for o in Osoba.objects.all():
            if o.data_urodzenia and o.data_smierci and o.data_smierci < o.data_urodzenia:
                problemy['smierc_przed_urodzeniem'].append({
                    'id': o.pk, 'osoba': str(o),
                    'urodzony': str(o.data_urodzenia), 'zmarl': str(o.data_smierci),
                })
            if o.data_urodzenia and o.data_urodzenia.year < 1700:
                problemy['data_urodzenia_zbyt_dawno'].append({
                    'id': o.pk, 'osoba': str(o), 'urodzony': str(o.data_urodzenia),
                })
            if o.data_smierci and o.data_smierci > teraz:
                problemy['data_smierci_w_przyszlosci'].append({
                    'id': o.pk, 'osoba': str(o), 'zmarl': str(o.data_smierci),
                })
            if o.data_urodzenia and o.data_smierci:
                wiek = o.data_smierci.year - o.data_urodzenia.year
                if wiek > 120:
                    problemy['nierealny_wiek'].append({
                        'id': o.pk, 'osoba': str(o), 'wiek': wiek,
                    })

        # Groby
        groby_bez_osob = Grob.objects.annotate(_n=Count('osoby')).filter(_n=0)
        for g in groby_bez_osob:
            problemy['grob_bez_osob'].append({
                'id': g.pk, 'grob': str(g),
            })

        groby_bez_pozycji = Grob.objects.filter(plan_x__isnull=True)
        if groby_bez_pozycji.exists():
            problemy['groby_bez_pozycji_na_planie'].append({
                'liczba': groby_bez_pozycji.count(),
                'wskazowka': "Uruchom: python manage.py rozmiesc_groby",
            })

        # Duplikaty osób (te same imie+nazwisko + zbliżone daty)
        klucze = defaultdict(list)
        for o in Osoba.objects.all():
            klucz = (o.imie.lower().strip(), o.nazwisko.lower().strip(),
                     o.data_smierci.year if o.data_smierci else None)
            klucze[klucz].append(o.pk)
        for klucz, ids in klucze.items():
            if len(ids) > 1:
                problemy['duplikaty_potencjalne'].append({
                    'klucz': f'{klucz[1]} {klucz[0]} (zm. {klucz[2]})',
                    'ids': ids,
                })

        if options['json']:
            self.stdout.write(json.dumps(dict(problemy), ensure_ascii=False, indent=2))
            return

        # Raport tekstowy
        if not problemy:
            self.stdout.write(self.style.SUCCESS('Walidacja OK — nie wykryto problemów.'))
            return

        for kategoria, lista in sorted(problemy.items()):
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(f'== {kategoria} ({len(lista)}) =='))
            for poz in lista[:20]:
                self.stdout.write('  - ' + ', '.join(f'{k}={v}' for k, v in poz.items()))
            if len(lista) > 20:
                self.stdout.write(f'  ... oraz {len(lista) - 20} kolejnych')
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE(f'Razem kategorii: {len(problemy)}, przypadków: {sum(len(v) for v in problemy.values())}'))
