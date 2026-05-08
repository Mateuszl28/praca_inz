"""Import pliku GEDCOM (5.5+) — tworzy Osoby i Relacje.

Działa jako jedno-kierunkowe wzbogacenie istniejącej bazy: nowe osoby trafiają
do "TYMCZASOWY" sektora bez znanych dat zgonu (administrator później przypisze
do właściwych grobów). Relacje rodzic/małżeństwo są zachowane.

Uruchomienie:
    python manage.py import_gedcom plik.ged
    python manage.py import_gedcom plik.ged --sektor TYMCZASOWY --dry-run
"""
import re
from datetime import date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from groby.models import Sektor, Grob, Osoba, Relacja


MIESIACE = {
    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12,
}


def parsuj_date(s):
    if not s:
        return None
    s = s.strip().upper()
    m = re.match(r'(\d{1,2})\s+([A-Z]{3})\s+(\d{4})', s)
    if m:
        d, mc, r = int(m.group(1)), MIESIACE.get(m.group(2)), int(m.group(3))
        if mc:
            try:
                return date(r, mc, d)
            except ValueError:
                return None
    m = re.match(r'(\d{4})', s)
    if m:
        return date(int(m.group(1)), 1, 1)
    return None


def parsuj_gedcom(tresc):
    """Zwraca (osoby, rodziny). Każda osoba: dict z polami; każda rodzina: dict."""
    linie = [l.rstrip('\r\n') for l in tresc.splitlines() if l.strip()]
    osoby, rodziny = {}, {}
    biezacy = None  # (typ, id, dict)
    sciezka = []  # stos (poziom, klucz)

    for linia in linie:
        m = re.match(r'(\d+)\s+(@[^@]+@\s+)?(\w+)(?:\s+(.*))?', linia)
        if not m:
            continue
        poziom = int(m.group(1))
        odnos = (m.group(2) or '').strip().strip('@')
        tag = m.group(3)
        wartosc = (m.group(4) or '').strip()

        if poziom == 0:
            if tag == 'INDI':
                biezacy = ('I', odnos, {})
                osoby[odnos] = biezacy[2]
            elif tag == 'FAM':
                biezacy = ('F', odnos, {'rodzice': [], 'dzieci': []})
                rodziny[odnos] = biezacy[2]
            else:
                biezacy = None
            sciezka = []
            continue

        if not biezacy:
            continue

        # Skróć ścieżkę do bieżącego poziomu
        sciezka = [s for s in sciezka if s[0] < poziom]

        if biezacy[0] == 'I':
            d = biezacy[2]
            if poziom == 1 and tag == 'NAME':
                m2 = re.match(r'([^/]*)/([^/]*)/?', wartosc)
                if m2:
                    imie = m2.group(1).strip()
                    nazw = m2.group(2).strip()
                    d['imie'], d['nazwisko'] = imie, nazw
                else:
                    d['imie'] = wartosc
            elif poziom == 1 and tag in ('BIRT', 'DEAT'):
                sciezka.append((1, tag))
            elif poziom == 2 and tag == 'DATE':
                if sciezka and sciezka[-1][1] == 'BIRT':
                    d['data_urodzenia'] = parsuj_date(wartosc)
                elif sciezka and sciezka[-1][1] == 'DEAT':
                    d['data_smierci'] = parsuj_date(wartosc)
            elif poziom == 1 and tag == 'FAMC':
                d.setdefault('FAMC', []).append(wartosc.strip().strip('@'))
            elif poziom == 1 and tag == 'FAMS':
                d.setdefault('FAMS', []).append(wartosc.strip().strip('@'))
        elif biezacy[0] == 'F':
            d = biezacy[2]
            if poziom == 1 and tag in ('HUSB', 'WIFE'):
                d['rodzice'].append(wartosc.strip().strip('@'))
            elif poziom == 1 and tag == 'CHIL':
                d['dzieci'].append(wartosc.strip().strip('@'))
    return osoby, rodziny


class Command(BaseCommand):
    help = 'Import pliku GEDCOM. Nowe osoby trafiają do podanego sektora.'

    def add_arguments(self, parser):
        parser.add_argument('plik', type=str)
        parser.add_argument('--sektor', default='TYMCZASOWY', help='Nazwa sektora docelowego.')
        parser.add_argument('--dry-run', action='store_true', help='Nie zapisuj — tylko podsumuj.')

    def handle(self, *args, **opt):
        try:
            with open(opt['plik'], 'r', encoding='utf-8-sig') as f:
                tresc = f.read()
        except OSError as e:
            raise CommandError(f'Nie moge otworzyc pliku: {e}')

        osoby_g, rodziny_g = parsuj_gedcom(tresc)
        self.stdout.write(f'Sparsowano: {len(osoby_g)} osob, {len(rodziny_g)} rodzin')

        if opt['dry_run']:
            self.stdout.write(self.style.WARNING('DRY-RUN — nic nie zapisano.'))
            return

        with transaction.atomic():
            sektor, _ = Sektor.objects.get_or_create(nazwa=opt['sektor'])
            grob, _ = Grob.objects.get_or_create(
                sektor=sektor, numer='IMPORT', defaults={'typ': 'inny'}
            )

            mapa_osob = {}  # GEDCOM_ID -> Osoba
            for gid, dane in osoby_g.items():
                if not dane.get('imie') and not dane.get('nazwisko'):
                    continue
                o = Osoba.objects.create(
                    grob=grob,
                    imie=(dane.get('imie') or '?')[:100],
                    nazwisko=(dane.get('nazwisko') or '?')[:100],
                    data_urodzenia=dane.get('data_urodzenia'),
                    data_smierci=dane.get('data_smierci'),
                )
                mapa_osob[gid] = o

            # Relacje z rodzin
            zapisanych_relacji = 0
            for fid, fdane in rodziny_g.items():
                rodzice = [mapa_osob.get(r) for r in fdane['rodzice']]
                rodzice = [r for r in rodzice if r]
                dzieci = [mapa_osob.get(d) for d in fdane['dzieci']]
                dzieci = [d for d in dzieci if d]
                # małżeństwo
                if len(rodzice) >= 2:
                    a, b = rodzice[0], rodzice[1]
                    Relacja.objects.get_or_create(osoba_a=a, osoba_b=b, typ='malzenstwo')
                    zapisanych_relacji += 1
                # rodzic-dziecko
                for r in rodzice:
                    for d in dzieci:
                        Relacja.objects.get_or_create(osoba_a=r, osoba_b=d, typ='rodzic')
                        zapisanych_relacji += 1

            self.stdout.write(self.style.SUCCESS(
                f'Zaimportowano: {len(mapa_osob)} osob, {zapisanych_relacji} relacji.'
            ))
            self.stdout.write(self.style.NOTICE(
                'Wszystkie osoby przypisane do tymczasowego grobu '
                f'"{grob}". Przypisz wlasciwe groby w panelu admin.'
            ))
