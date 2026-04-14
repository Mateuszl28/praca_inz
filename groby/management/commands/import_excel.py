"""
Import danych z pliku Excel (.xlsx).

Przykładowe wywołanie:
    python manage.py import_excel dane.xlsx
    python manage.py import_excel dane.xlsx --arkusz "Zmarli" --dry-run
    python manage.py import_excel dane.xlsx --sektor-domyslny A --wyczysc

Oczekiwany układ: jeden wiersz = jedna osoba. Osoby z tym samym "sektor + numer grobu"
są grupowane pod jednym rekordem grobu.

Obsługiwane aliasy kolumn (wielkość liter i spacje bez znaczenia):
    sektor              — nazwa sektora (np. "A", "1"). Jeśli brak, wymagany --sektor-domyslny.
    numer | nr_grobu    — numer grobu w sektorze.
    rzad | rząd         — numer rzędu (opcjonalne).
    typ                 — typ grobu (ziemny, murowany, rodzinny, urnowy, zbiorowy).
    imie | imię         — imię osoby (wymagane).
    nazwisko            — nazwisko osoby (wymagane).
    nazwisko_rodowe     — nazwisko rodowe (opcjonalne).
    drugie_imie         — drugie imię (opcjonalne).
    data_urodzenia      — akceptuje datę lub sam rok.
    data_smierci        — akceptuje datę lub sam rok.
    miejsce_urodzenia   — opcjonalne.
    biogram | opis      — opcjonalne.
    szerokosc | lat     — szerokość geograficzna.
    dlugosc | lng | lon — długość geograficzna.
    uwagi               — uwagi o grobie.
"""
from datetime import date, datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from groby.models import Sektor, Grob, Osoba


ALIASY_KOLUMN = {
    'sektor': 'sektor',
    'sector': 'sektor',
    'nazwa_sektora': 'sektor',
    'numer': 'numer',
    'nr': 'numer',
    'nr_grobu': 'numer',
    'numer_grobu': 'numer',
    'rzad': 'rzad',
    'rząd': 'rzad',
    'typ': 'typ',
    'typ_grobu': 'typ',
    'imie': 'imie',
    'imię': 'imie',
    'drugie_imie': 'drugie_imie',
    'nazwisko': 'nazwisko',
    'nazwisko_rodowe': 'nazwisko_rodowe',
    'nazwisko_panienskie': 'nazwisko_rodowe',
    'panienskie': 'nazwisko_rodowe',
    'data_urodzenia': 'data_urodzenia',
    'rok_urodzenia': 'data_urodzenia',
    'urodzony': 'data_urodzenia',
    'urodzona': 'data_urodzenia',
    'data_smierci': 'data_smierci',
    'data_śmierci': 'data_smierci',
    'rok_smierci': 'data_smierci',
    'rok_śmierci': 'data_smierci',
    'zmarl': 'data_smierci',
    'zmarla': 'data_smierci',
    'zmarły': 'data_smierci',
    'miejsce_urodzenia': 'miejsce_urodzenia',
    'biogram': 'biogram',
    'opis': 'biogram',
    'uwagi': 'uwagi',
    'szerokosc': 'szerokosc_geo',
    'szerokość': 'szerokosc_geo',
    'szerokosc_geo': 'szerokosc_geo',
    'lat': 'szerokosc_geo',
    'latitude': 'szerokosc_geo',
    'dlugosc': 'dlugosc_geo',
    'długość': 'dlugosc_geo',
    'dlugosc_geo': 'dlugosc_geo',
    'lng': 'dlugosc_geo',
    'lon': 'dlugosc_geo',
    'longitude': 'dlugosc_geo',
}

MAPA_TYPOW = {
    'ziemny': 'ziemny',
    'grob ziemny': 'ziemny',
    'ziemne': 'ziemny',
    'murowany': 'murowany',
    'grob murowany': 'murowany',
    'rodzinny': 'rodzinny',
    'grob rodzinny': 'rodzinny',
    'urnowy': 'urnowy',
    'urna': 'urnowy',
    'kolumbarium': 'urnowy',
    'zbiorowy': 'zbiorowy',
    'masowy': 'zbiorowy',
}


def normalizuj(s):
    if s is None:
        return ''
    return str(s).strip().lower().replace(' ', '_').replace('-', '_')


def parsuj_date(v):
    if v is None or v == '':
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    if not s:
        return None
    if s.isdigit() and len(s) == 4:
        return date(int(s), 1, 1)
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parsuj_typ(v):
    if not v:
        return 'ziemny'
    norm = str(v).strip().lower()
    return MAPA_TYPOW.get(norm, 'inny')


def parsuj_float(v):
    if v is None or v == '':
        return None
    try:
        return float(str(v).replace(',', '.'))
    except (ValueError, TypeError):
        return None


def parsuj_tekst(v):
    if v is None:
        return ''
    s = str(v).strip()
    return '' if s.lower() in ('nan', 'none') else s


class Command(BaseCommand):
    help = 'Importuje dane z pliku Excel (.xlsx) do bazy.'

    def add_arguments(self, parser):
        parser.add_argument('plik', type=str, help='Ścieżka do pliku .xlsx')
        parser.add_argument('--arkusz', type=str, default=0, help='Nazwa lub indeks arkusza (domyślnie pierwszy).')
        parser.add_argument('--sektor-domyslny', type=str, default=None, help='Nazwa sektora używana, gdy brak kolumny "sektor".')
        parser.add_argument('--wyczysc', action='store_true', help='Usuń istniejące groby i osoby przed importem (sektory zostają).')
        parser.add_argument('--dry-run', action='store_true', help='Nie zapisuj do bazy, pokaż tylko podsumowanie.')

    def handle(self, *args, **options):
        try:
            import pandas as pd
        except ImportError:
            raise CommandError('Brak biblioteki pandas. Zainstaluj: pip install pandas openpyxl')

        plik = options['plik']
        self.stdout.write(f'Wczytuję plik: {plik}')
        try:
            df = pd.read_excel(plik, sheet_name=options['arkusz'])
        except FileNotFoundError:
            raise CommandError(f'Nie znaleziono pliku: {plik}')
        except Exception as e:
            raise CommandError(f'Błąd odczytu pliku: {e}')

        # Mapowanie kolumn Excela na pola modelu
        mapowanie = {}
        for kol in df.columns:
            klucz = normalizuj(kol)
            if klucz in ALIASY_KOLUMN:
                mapowanie[ALIASY_KOLUMN[klucz]] = kol

        self.stdout.write(f'Rozpoznane kolumny: {list(mapowanie.keys())}')

        if 'imie' not in mapowanie or 'nazwisko' not in mapowanie:
            raise CommandError('Brak wymaganych kolumn: "imie" i "nazwisko". Sprawdź nagłówki.')

        if 'sektor' not in mapowanie and not options['sektor_domyslny']:
            raise CommandError('Brak kolumny "sektor". Użyj --sektor-domyslny aby przypisać jedną nazwę do wszystkich.')

        if 'numer' not in mapowanie:
            raise CommandError('Brak kolumny "numer" (numer grobu).')

        dry = options['dry_run']
        liczba_wierszy = len(df)

        with transaction.atomic():
            if options['wyczysc'] and not dry:
                self.stdout.write('Usuwam istniejące osoby i groby…')
                Osoba.objects.all().delete()
                Grob.objects.all().delete()

            cache_sektorow = {s.nazwa: s for s in Sektor.objects.all()}
            cache_grobow = {}
            nowych_sektorow = nowych_grobow = nowych_osob = 0

            for idx, row in df.iterrows():
                def pole(klucz, default=None):
                    return row[mapowanie[klucz]] if klucz in mapowanie else default

                nazwa_sektora = parsuj_tekst(pole('sektor')) or options['sektor_domyslny']
                if not nazwa_sektora:
                    self.stdout.write(self.style.WARNING(f'  Wiersz {idx + 2}: brak sektora, pomijam.'))
                    continue

                numer = parsuj_tekst(pole('numer'))
                if not numer:
                    self.stdout.write(self.style.WARNING(f'  Wiersz {idx + 2}: brak numeru grobu, pomijam.'))
                    continue

                imie = parsuj_tekst(pole('imie'))
                nazwisko = parsuj_tekst(pole('nazwisko'))
                if not imie or not nazwisko:
                    self.stdout.write(self.style.WARNING(f'  Wiersz {idx + 2}: brak imienia lub nazwiska, pomijam.'))
                    continue

                sektor = cache_sektorow.get(nazwa_sektora)
                if not sektor:
                    if not dry:
                        sektor = Sektor.objects.create(nazwa=nazwa_sektora)
                    else:
                        sektor = Sektor(nazwa=nazwa_sektora)
                    cache_sektorow[nazwa_sektora] = sektor
                    nowych_sektorow += 1

                klucz_grobu = (nazwa_sektora, numer)
                grob = cache_grobow.get(klucz_grobu)
                if not grob:
                    grob_qs = Grob.objects.filter(sektor=sektor, numer=numer) if not dry else []
                    grob = grob_qs.first() if grob_qs else None
                    if not grob:
                        dane_grobu = {
                            'sektor': sektor,
                            'numer': numer,
                            'rzad': parsuj_tekst(pole('rzad')),
                            'typ': parsuj_typ(pole('typ')),
                            'szerokosc_geo': parsuj_float(pole('szerokosc_geo')),
                            'dlugosc_geo': parsuj_float(pole('dlugosc_geo')),
                            'uwagi': parsuj_tekst(pole('uwagi')),
                        }
                        grob = Grob.objects.create(**dane_grobu) if not dry else Grob(**dane_grobu)
                        nowych_grobow += 1
                    cache_grobow[klucz_grobu] = grob

                dane_osoby = {
                    'grob': grob,
                    'imie': imie,
                    'drugie_imie': parsuj_tekst(pole('drugie_imie')),
                    'nazwisko': nazwisko,
                    'nazwisko_rodowe': parsuj_tekst(pole('nazwisko_rodowe')),
                    'data_urodzenia': parsuj_date(pole('data_urodzenia')),
                    'data_smierci': parsuj_date(pole('data_smierci')),
                    'miejsce_urodzenia': parsuj_tekst(pole('miejsce_urodzenia')),
                    'biogram': parsuj_tekst(pole('biogram')),
                }
                if not dry:
                    Osoba.objects.create(**dane_osoby)
                nowych_osob += 1

            if dry:
                self.stdout.write(self.style.WARNING('--- DRY RUN: nic nie zostało zapisane ---'))
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(f'Przetworzono wierszy: {liczba_wierszy}'))
        self.stdout.write(self.style.SUCCESS(f'  Nowych sektorow: {nowych_sektorow}'))
        self.stdout.write(self.style.SUCCESS(f'  Nowych grobow:   {nowych_grobow}'))
        self.stdout.write(self.style.SUCCESS(f'  Nowych osob:     {nowych_osob}'))
