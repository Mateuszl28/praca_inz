"""
Auto-rozmieszczenie grobów na planie cmentarza (CRS.Simple).

Kładzie marker dla każdego grobu na pozycji (plan_x, plan_y) wyliczonej
deterministycznie z (sektor, rząd, numer):
    - sektory ułożone poziomymi pasami (A na górze … F na dole),
    - w każdym sektorze rzędy ułożone jako kolumny od lewej do prawej,
    - w każdym rzędzie groby od góry do dołu według numeru.

Po uruchomieniu wszystkie groby mają sensowne pozycje wyjściowe; w
trybie edycji na /mapa/ można je dalej poprawiać klikiem.

Wywołanie:
    python manage.py rozmiesc_groby                      # 1367×4000 (default)
    python manage.py rozmiesc_groby --szer 1367 --wys 4000
    python manage.py rozmiesc_groby --tylko-puste        # nie nadpisuj już ustawionych
"""
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from groby.models import Grob, Sektor


def rzymski_na_int(s):
    if not s:
        return 0
    s = str(s).strip().upper()
    mapa = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    if any(c not in mapa for c in s):
        m = re.match(r'(\d+)', s)
        return int(m.group(1)) if m else 0
    wynik = 0
    poprz = 0
    for c in reversed(s):
        v = mapa[c]
        wynik += -v if v < poprz else v
        poprz = v
    return wynik


def numer_sortujacy(numer):
    s = str(numer).strip()
    m = re.match(r'(\d+)', s)
    return int(m.group(1)) if m else 0


class Command(BaseCommand):
    help = 'Auto-rozmieszczenie grobów na planie cmentarza (siatka).'

    def add_arguments(self, parser):
        parser.add_argument('--szer', type=int, default=1367, help='Szerokość obrazu planu (px).')
        parser.add_argument('--wys', type=int, default=4000, help='Wysokość obrazu planu (px).')
        parser.add_argument('--margines', type=int, default=40, help='Margines wewnętrzny w px.')
        parser.add_argument('--x-min', type=int, default=None, help='Lewa krawędź obszaru cmentarza (px). Domyślnie: margines.')
        parser.add_argument('--x-max', type=int, default=None, help='Prawa krawędź obszaru cmentarza (px). Domyślnie: szer-margines.')
        parser.add_argument('--y-min', type=int, default=None, help='Górna krawędź obszaru cmentarza (px). Domyślnie: margines.')
        parser.add_argument('--y-max', type=int, default=None, help='Dolna krawędź obszaru cmentarza (px). Domyślnie: wys-margines.')
        parser.add_argument('--kolejnosc', type=str, default=None, help='Kolejność sektorów od góry, oddzielone przecinkami (np. "F,A,B,C,D,E"). Domyślnie: alfabetycznie.')
        parser.add_argument('--tylko-puste', action='store_true', help='Nie ruszaj grobów, które już mają plan_x/plan_y.')

    def handle(self, *args, **options):
        szer = options['szer']
        wys = options['wys']
        m = options['margines']
        x_min = options['x_min'] if options['x_min'] is not None else m
        x_max = options['x_max'] if options['x_max'] is not None else szer - m
        y_min = options['y_min'] if options['y_min'] is not None else m
        y_max = options['y_max'] if options['y_max'] is not None else wys - m

        sektory_qs = list(Sektor.objects.all())
        if not sektory_qs:
            self.stdout.write(self.style.ERROR('Brak sektorów w bazie.'))
            return

        # Wyfiltruj sektory, które mają jakiekolwiek groby — sektor "test" może być pusty.
        sektory_qs = [s for s in sektory_qs if s.groby.exists()]

        if options['kolejnosc']:
            zamowiona = [n.strip() for n in options['kolejnosc'].split(',') if n.strip()]
            wg_nazwy = {s.nazwa: s for s in sektory_qs}
            sektory = [wg_nazwy[n] for n in zamowiona if n in wg_nazwy]
            # dopisz nieujęte sektory na końcu, żeby nigdy nie zgubić danych
            for s in sektory_qs:
                if s not in sektory:
                    sektory.append(s)
        else:
            sektory = sorted(sektory_qs, key=lambda s: s.nazwa)

        n_sektorow = len(sektory)
        wys_pasa = (y_max - y_min) / n_sektorow

        zmienione = pominiete = 0

        with transaction.atomic():
            for i_sekt, sektor in enumerate(sektory):
                pas_top = y_min + i_sekt * wys_pasa
                pas_bottom = pas_top + wys_pasa
                # przypadek: zostaw odrobinę odstępu od sąsiednich pasów
                pas_top += 8
                pas_bottom -= 8

                groby = list(sektor.groby.all())
                rzedy = sorted({g.rzad or '' for g in groby}, key=rzymski_na_int)
                rzad_index = {r: idx for idx, r in enumerate(rzedy)}
                n_rzedow = max(len(rzedy), 1)
                szer_kolumny = (x_max - x_min) / n_rzedow

                # ile grobów w najdłuższym rzędzie tego sektora — wpływa na rozsuw pionowy
                liczebnosc_rzedu = {}
                for g in groby:
                    liczebnosc_rzedu.setdefault(g.rzad or '', []).append(g)
                for r in liczebnosc_rzedu:
                    liczebnosc_rzedu[r].sort(key=lambda g: numer_sortujacy(g.numer))

                for rzad, lista in liczebnosc_rzedu.items():
                    kol = rzad_index[rzad]
                    x = x_min + kol * szer_kolumny + szer_kolumny / 2
                    n_grobow = len(lista)
                    krok = (pas_bottom - pas_top) / max(n_grobow, 1)
                    for j, g in enumerate(lista):
                        if options['tylko_puste'] and g.plan_x is not None and g.plan_y is not None:
                            pominiete += 1
                            continue
                        y = pas_top + j * krok + krok / 2
                        g.plan_x = round(x, 2)
                        g.plan_y = round(y, 2)
                        g.save(update_fields=['plan_x', 'plan_y', 'data_modyfikacji'])
                        zmienione += 1

                self.stdout.write(
                    f'  Sektor {sektor.nazwa}: {len(groby)} grobow, {len(rzedy)} rzedow, '
                    f'pas y w [{pas_top:.0f}, {pas_bottom:.0f}].'
                )

        self.stdout.write(self.style.SUCCESS(f'Zmienione: {zmienione}, pominięte: {pominiete}'))
