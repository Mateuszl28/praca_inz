"""
Import danych z pliku Excel (.xlsx).

Przykładowe wywołanie:
    python manage.py import_excel "I:/Szydłów - cmentarz/baza.xlsx" --arkusz "księga grobów" --wyczysc
    python manage.py import_excel dane.xlsx --dry-run
    python manage.py import_excel dane.xlsx --sektor-domyslny A

Oczekiwany układ: jeden wiersz = jedna osoba. Osoby z tym samym
"sektor + rząd + numer grobu" są grupowane pod jednym rekordem grobu.

Domyślnie nagłówki czytane są z drugiego wiersza (pierwszy wiersz arkusza
„księga grobów” zawiera notatki UWAGI). Można nadpisać przez --wiersz-naglowkow.

Obsługiwane aliasy kolumn (wielkość liter i spacje bez znaczenia):
    sektor / kwatera                — nazwa sektora.
    numer / nr_grobu                — numer grobu w sektorze.
    rzad / rząd                     — rząd grobu (rzymski numer).
    typ / rodzaj_grobu              — typ/opis nagrobka.
    imie / imię_osoby_pochowanej    — imię (wymagane).
    nazwisko / nazwisko_osoby_...   — nazwisko (wymagane).
    data_urodzenia                  — data lub sam rok.
    data_smierci / data_śmierci     — data lub sam rok.
    numer_aktu                      — numer aktu w księdze zmarłych.
    oplata / opłata...              — tak / nie / brak danych.
    link / link_do_zdjęcia...       — URL do zdjęcia.
    biogram / opis / tekst_wspomnienia — biogram osoby.
    szerokosc / lat                 — szerokość geograficzna.
    dlugosc / lng / lon             — długość geograficzna.
    uwagi                           — uwagi o grobie.
"""
from datetime import date, datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from groby.models import Sektor, Grob, Osoba


ALIASY_KOLUMN = {
    # sektor / kwatera
    'sektor': 'sektor',
    'sector': 'sektor',
    'nazwa_sektora': 'sektor',
    'kwatera': 'sektor',
    # numer grobu
    'numer': 'numer',
    'nr': 'numer',
    'nr_grobu': 'numer',
    'numer_grobu': 'numer',
    # rząd
    'rzad': 'rzad',
    'rząd': 'rzad',
    # typ / rodzaj
    'typ': 'rodzaj_opis',
    'typ_grobu': 'rodzaj_opis',
    'rodzaj': 'rodzaj_opis',
    'rodzaj_grobu': 'rodzaj_opis',
    'rodzaj_nagrobka': 'rodzaj_opis',
    # imię
    'imie': 'imie',
    'imię': 'imie',
    'imie_osoby_pochowanej': 'imie',
    'imię_osoby_pochowanej': 'imie',
    'drugie_imie': 'drugie_imie',
    # nazwisko
    'nazwisko': 'nazwisko',
    'nazwisko_osoby_pochowanej': 'nazwisko',
    'nazwisko_rodowe': 'nazwisko_rodowe',
    'nazwisko_panienskie': 'nazwisko_rodowe',
    'panienskie': 'nazwisko_rodowe',
    # daty
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
    # pozostałe pola osoby
    'miejsce_urodzenia': 'miejsce_urodzenia',
    'biogram': 'biogram',
    'opis': 'biogram',
    'tekst_wspomnienia': 'biogram',
    'wspomnienie': 'biogram',
    # pola grobu z arkusza księga grobów
    'numer_aktu': 'numer_aktu',
    'numer_aktu_w_księdze_zmarłych': 'numer_aktu',
    'numer_aktu_w_ksiedze_zmarlych': 'numer_aktu',
    'oplata': 'oplata',
    'opłata': 'oplata',
    'opłata_za_nagrobek': 'oplata',
    'oplata_za_nagrobek': 'oplata',
    'link': 'link_zdjecia',
    'link_do_zdjęcia': 'link_zdjecia',
    'link_do_zdjecia': 'link_zdjecia',
    'link_do_zdjęcia_nagrobka': 'link_zdjecia',
    'link_do_zdjecia_nagrobka': 'link_zdjecia',
    # mapa
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


def normalizuj(s):
    if s is None:
        return ''
    return str(s).strip().lower().replace(' ', '_').replace('-', '_').replace('\n', '_')


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
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def infer_typ(opis):
    """Mapuje wolny opis rodzaju nagrobka na jeden z TYP_CHOICES."""
    if not opis:
        return 'inny'
    s = str(opis).strip().lower()
    if not s:
        return 'inny'
    if 'rodzinn' in s or 'grobowiec' in s or 'plac rodzinny' in s:
        return 'rodzinny'
    if 'urna' in s or 'kolumbarium' in s:
        return 'urnowy'
    if 'pomnik' in s or 'grobowiec' in s or 'cementowa' in s or 'kamienn' in s or 'granitowy' in s:
        return 'murowany'
    if 'kopiec' in s or 'kopczyk' in s or 'ziemny' in s:
        return 'ziemny'
    if 'krzyż' in s or 'krzy' in s or 'obwódka' in s or 'obw' in s or 'płyta' in s or 'plyta' in s or 'tablica' in s or 'płotek' in s or 'plotek' in s:
        return 'ziemny'
    return 'inny'


def parsuj_oplata(v):
    if v is None:
        return ''
    s = str(v).strip().lower()
    if s in ('tak', 't', 'yes', 'y', '1'):
        return 'tak'
    if s in ('nie', 'n', 'no', '0'):
        return 'nie'
    if 'brak' in s:
        return 'brak_danych'
    return ''


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
        parser.add_argument('--wiersz-naglowkow', type=int, default=1, help='Numer wiersza nagłówków (od 0). Domyślnie 1 (drugi wiersz).')
        parser.add_argument('--sektor-domyslny', type=str, default=None, help='Nazwa sektora używana, gdy brak kolumny "sektor".')
        parser.add_argument('--wyczysc', action='store_true', help='Usuń istniejące groby i osoby przed importem (sektory zostają).')
        parser.add_argument('--dry-run', action='store_true', help='Nie zapisuj do bazy, pokaż tylko podsumowanie.')

    def handle(self, *args, **options):
        try:
            import pandas as pd
        except ImportError:
            raise CommandError('Brak biblioteki pandas. Zainstaluj: pip install pandas openpyxl')

        plik = options['plik']
        arkusz = options['arkusz']
        try:
            arkusz = int(arkusz)
        except (TypeError, ValueError):
            pass

        self.stdout.write(f'Wczytuję plik: {plik} (arkusz: {arkusz!r}, nagłówek w wierszu {options["wiersz_naglowkow"] + 1})')
        try:
            df = pd.read_excel(plik, sheet_name=arkusz, header=options['wiersz_naglowkow'])
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
            raise CommandError('Brak kolumny "sektor"/"kwatera". Użyj --sektor-domyslny aby przypisać jedną nazwę do wszystkich.')

        if 'numer' not in mapowanie:
            raise CommandError('Brak kolumny "numer" (numer grobu).')

        dry = options['dry_run']
        liczba_wierszy = len(df)
        pominiete = 0

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
                    pominiete += 1
                    continue

                # numer może być liczbą lub łańcuchem ("1a")
                surowy_numer = pole('numer')
                if isinstance(surowy_numer, float) and surowy_numer.is_integer():
                    numer = str(int(surowy_numer))
                else:
                    numer = parsuj_tekst(surowy_numer)
                if not numer:
                    pominiete += 1
                    continue

                imie = parsuj_tekst(pole('imie'))
                nazwisko = parsuj_tekst(pole('nazwisko'))
                if not imie or not nazwisko:
                    pominiete += 1
                    continue

                rzad = parsuj_tekst(pole('rzad'))

                sektor = cache_sektorow.get(nazwa_sektora)
                if not sektor:
                    if not dry:
                        sektor = Sektor.objects.create(nazwa=nazwa_sektora)
                    else:
                        sektor = Sektor(nazwa=nazwa_sektora)
                    cache_sektorow[nazwa_sektora] = sektor
                    nowych_sektorow += 1

                klucz_grobu = (nazwa_sektora, rzad, numer)
                grob = cache_grobow.get(klucz_grobu)
                if not grob:
                    grob_qs = Grob.objects.filter(sektor=sektor, rzad=rzad, numer=numer) if not dry else []
                    grob = grob_qs.first() if grob_qs else None
                    if not grob:
                        rodzaj_opis = parsuj_tekst(pole('rodzaj_opis'))
                        dane_grobu = {
                            'sektor': sektor,
                            'numer': numer,
                            'rzad': rzad,
                            'typ': infer_typ(rodzaj_opis),
                            'rodzaj_opis': rodzaj_opis,
                            'numer_aktu': parsuj_tekst(pole('numer_aktu')),
                            'oplata': parsuj_oplata(pole('oplata')),
                            'link_zdjecia': parsuj_tekst(pole('link_zdjecia')),
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

        self.stdout.write(self.style.SUCCESS(f'Przetworzono wierszy: {liczba_wierszy} (pominięto: {pominiete})'))
        self.stdout.write(self.style.SUCCESS(f'  Nowych sektorow: {nowych_sektorow}'))
        self.stdout.write(self.style.SUCCESS(f'  Nowych grobow:   {nowych_grobow}'))
        self.stdout.write(self.style.SUCCESS(f'  Nowych osob:     {nowych_osob}'))
