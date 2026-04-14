import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from groby.models import Sektor, Grob, Osoba


IMIONA_M = [
    'Jan', 'Stanisław', 'Józef', 'Kazimierz', 'Antoni', 'Franciszek', 'Władysław',
    'Stefan', 'Tadeusz', 'Henryk', 'Piotr', 'Andrzej', 'Mieczysław', 'Eugeniusz',
    'Marian', 'Zbigniew', 'Bogdan', 'Bolesław', 'Ryszard', 'Adam',
]
IMIONA_Z = [
    'Maria', 'Anna', 'Zofia', 'Helena', 'Janina', 'Krystyna', 'Stanisława',
    'Jadwiga', 'Barbara', 'Teresa', 'Irena', 'Wanda', 'Halina', 'Urszula',
    'Danuta', 'Elżbieta', 'Genowefa', 'Kazimiera', 'Józefa', 'Czesława',
]
NAZWISKA_BAZA = [
    'Kowal', 'Now', 'Wiśniewsk', 'Kowalczyk', 'Kamińsk', 'Lewandowsk', 'Zieliń',
    'Wójcik', 'Wozniak', 'Mazur', 'Krawczyk', 'Pawłowsk', 'Kaczmarek', 'Szymańsk',
    'Dąbrowsk', 'Pietrzak', 'Stępień', 'Michalak', 'Jankowsk', 'Baran',
]
MIEJSCOWOSCI = ['Szydłów', 'Kielce', 'Staszów', 'Busko-Zdrój', 'Chmielnik', 'Pińczów', 'Opatów', 'Kraków']
OPISY_SEKTOROW = {
    'A': 'Najstarszy sektor cmentarza, obejmujący groby z XIX i początku XX wieku.',
    'B': 'Sektor główny z grobami rodzinnymi i pomnikami.',
    'C': 'Sektor środkowy — groby z okresu międzywojennego i powojennego.',
    'D': 'Sektor nowy, obejmujący groby z drugiej połowy XX wieku.',
    'E': 'Najmłodsza część cmentarza z grobami współczesnymi oraz urnowymi.',
}

# Cmentarz w Szydłowie — przybliżone centrum
SZYDLOW_LAT = 50.5847
SZYDLOW_LNG = 20.8327


def nazwisko_meskie(baza):
    return baza + ('ski' if baza.endswith(('ń', 'sk', 'sk')) else '') + ('i' if baza.endswith('sk') else '') if False else baza + ('ski' if baza.endswith('sk') else '') or baza


def forma_meska(baza):
    if baza.endswith('sk'):
        return baza + 'i'
    if baza.endswith('ń'):
        return baza + 'ski'
    return baza


def forma_zenska(baza):
    if baza.endswith('sk'):
        return baza + 'a'
    if baza.endswith('ń'):
        return baza + 'ska'
    return baza + 'owa' if not baza.endswith(('a', 'o', 'y', 'i')) else baza


def losowa_data(rok_od, rok_do):
    start = date(rok_od, 1, 1)
    end = date(rok_do, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


class Command(BaseCommand):
    help = 'Dodaje przykładowe dane demonstracyjne (sektory, groby, osoby).'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Usuń istniejące dane przed dodaniem nowych.')
        parser.add_argument('--groby', type=int, default=50, help='Liczba grobów do wygenerowania (domyślnie 50).')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Usuwam istniejące dane…')
            Osoba.objects.all().delete()
            Grob.objects.all().delete()
            Sektor.objects.all().delete()

        sektory = []
        for nazwa, opis in OPISY_SEKTOROW.items():
            sektor, _ = Sektor.objects.get_or_create(nazwa=nazwa, defaults={'opis': opis})
            sektory.append(sektor)
        self.stdout.write(self.style.SUCCESS(f'[OK]Sektory: {len(sektory)}'))

        typy = [t[0] for t in Grob.TYP_CHOICES]
        liczba_grobow = options['groby']
        utworzone_groby = 0
        utworzone_osoby = 0

        for i in range(liczba_grobow):
            sektor = random.choice(sektory)
            numer = f'{i + 1:03d}'
            if Grob.objects.filter(sektor=sektor, numer=numer).exists():
                continue

            grob = Grob.objects.create(
                sektor=sektor,
                numer=numer,
                rzad=str(random.randint(1, 15)),
                typ=random.choices(typy, weights=[4, 3, 2, 1, 1, 1])[0],
                szerokosc_geo=SZYDLOW_LAT + random.uniform(-0.0008, 0.0008),
                dlugosc_geo=SZYDLOW_LNG + random.uniform(-0.0010, 0.0010),
                uwagi='',
            )
            utworzone_groby += 1

            liczba_osob = random.choices([1, 2, 3, 4], weights=[5, 4, 2, 1])[0]
            for _ in range(liczba_osob):
                plec = random.choice(['M', 'K'])
                baza = random.choice(NAZWISKA_BAZA)
                nazwisko = forma_meska(baza) if plec == 'M' else forma_zenska(baza)
                imie = random.choice(IMIONA_M if plec == 'M' else IMIONA_Z)

                rok_ur = random.randint(1880, 1970)
                wiek_max = min(2023 - rok_ur, 95)
                wiek_min = max(5, wiek_max - 60)
                rok_sm = rok_ur + random.randint(wiek_min, wiek_max)

                data_ur = losowa_data(rok_ur, rok_ur)
                data_sm = losowa_data(rok_sm, rok_sm)

                nazwisko_rodowe = ''
                if plec == 'K' and random.random() < 0.4:
                    baza_rod = random.choice(NAZWISKA_BAZA)
                    nazwisko_rodowe = forma_zenska(baza_rod)

                Osoba.objects.create(
                    grob=grob,
                    imie=imie,
                    nazwisko=nazwisko,
                    nazwisko_rodowe=nazwisko_rodowe,
                    data_urodzenia=data_ur,
                    data_smierci=data_sm,
                    miejsce_urodzenia=random.choice(MIEJSCOWOSCI) if random.random() < 0.6 else '',
                    biogram='',
                )
                utworzone_osoby += 1

        self.stdout.write(self.style.SUCCESS(f'[OK]Groby: {utworzone_groby}'))
        self.stdout.write(self.style.SUCCESS(f'[OK]Osoby: {utworzone_osoby}'))
        self.stdout.write(self.style.SUCCESS('Gotowe. Odśwież stronę główną, aby zobaczyć dane.'))
