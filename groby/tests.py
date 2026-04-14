"""
Testy jednostkowe aplikacji groby.
Uruchamianie: python manage.py test
"""
from datetime import date
from django.test import TestCase
from django.urls import reverse

from .models import Sektor, Grob, Osoba
from .templatetags.polish import polish_plural


# ---------- Testy modeli ----------


class SektorModelTest(TestCase):
    def test_str_zwraca_nazwe(self):
        s = Sektor.objects.create(nazwa='A', opis='Test')
        self.assertEqual(str(s), 'A')

    def test_domyslne_sortowanie_po_nazwie(self):
        Sektor.objects.create(nazwa='B')
        Sektor.objects.create(nazwa='A')
        Sektor.objects.create(nazwa='C')
        self.assertEqual(
            list(Sektor.objects.values_list('nazwa', flat=True)),
            ['A', 'B', 'C'],
        )

    def test_nazwa_jest_unikalna(self):
        Sektor.objects.create(nazwa='A')
        with self.assertRaises(Exception):
            Sektor.objects.create(nazwa='A')


class GrobModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sektor = Sektor.objects.create(nazwa='A')

    def test_str_format_sektor_numer(self):
        g = Grob.objects.create(sektor=self.sektor, numer='12')
        self.assertEqual(str(g), 'A/12')

    def test_domyslny_typ_to_ziemny(self):
        g = Grob.objects.create(sektor=self.sektor, numer='1')
        self.assertEqual(g.typ, 'ziemny')

    def test_unikalne_sektor_numer(self):
        Grob.objects.create(sektor=self.sektor, numer='1')
        with self.assertRaises(Exception):
            Grob.objects.create(sektor=self.sektor, numer='1')

    def test_ten_sam_numer_w_innym_sektorze(self):
        sektor_b = Sektor.objects.create(nazwa='B')
        Grob.objects.create(sektor=self.sektor, numer='1')
        Grob.objects.create(sektor=sektor_b, numer='1')
        self.assertEqual(Grob.objects.count(), 2)


class OsobaModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sektor = Sektor.objects.create(nazwa='A')
        cls.grob = Grob.objects.create(sektor=cls.sektor, numer='1')

    def test_str_z_nazwiskiem_rodowym(self):
        o = Osoba.objects.create(
            grob=self.grob, imie='Anna', nazwisko='Kowal', nazwisko_rodowe='Nowak',
        )
        self.assertEqual(str(o), 'Anna Kowal (z d. Nowak)')

    def test_str_bez_nazwiska_rodowego(self):
        o = Osoba.objects.create(grob=self.grob, imie='Jan', nazwisko='Nowak')
        self.assertEqual(str(o), 'Jan Nowak')

    def test_wiek_liczony_poprawnie(self):
        o = Osoba.objects.create(
            grob=self.grob, imie='Jan', nazwisko='Test',
            data_urodzenia=date(1950, 5, 10),
            data_smierci=date(2020, 5, 11),
        )
        self.assertEqual(o.wiek, 70)

    def test_wiek_gdy_zmarl_przed_urodzinami(self):
        o = Osoba.objects.create(
            grob=self.grob, imie='Jan', nazwisko='Test',
            data_urodzenia=date(1950, 5, 10),
            data_smierci=date(2020, 5, 9),
        )
        self.assertEqual(o.wiek, 69)

    def test_wiek_none_gdy_brak_dat(self):
        o = Osoba.objects.create(grob=self.grob, imie='X', nazwisko='Y')
        self.assertIsNone(o.wiek)


# ---------- Testy widoków ----------


class WidokiPubliczneTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sektor = Sektor.objects.create(nazwa='A', opis='Testowy sektor')
        cls.grob = Grob.objects.create(
            sektor=cls.sektor, numer='1', typ='ziemny',
            szerokosc_geo=50.5847, dlugosc_geo=20.8327,
        )
        cls.osoba = Osoba.objects.create(
            grob=cls.grob, imie='Jan', nazwisko='Kowalski',
            data_urodzenia=date(1950, 1, 1),
            data_smierci=date(2020, 6, 15),
        )

    def test_strona_glowna(self):
        r = self.client.get(reverse('groby:home'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Cmentarny')

    def test_o_cmentarzu(self):
        self.assertEqual(self.client.get(reverse('groby:o_cmentarzu')).status_code, 200)

    def test_lista_sektorow(self):
        r = self.client.get(reverse('groby:sektory_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'A')

    def test_szczegoly_sektora(self):
        r = self.client.get(reverse('groby:sektor_detail', args=[self.sektor.pk]))
        self.assertEqual(r.status_code, 200)

    def test_szczegoly_grobu(self):
        r = self.client.get(reverse('groby:grob_detail', args=[self.grob.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Kowalski')

    def test_szczegoly_osoby(self):
        r = self.client.get(reverse('groby:osoba_detail', args=[self.osoba.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Jan')
        self.assertContains(r, 'Kowalski')

    def test_mapa(self):
        self.assertEqual(self.client.get(reverse('groby:mapa')).status_code, 200)

    def test_statystyki(self):
        self.assertEqual(self.client.get(reverse('groby:statystyki')).status_code, 200)

    def test_404_dla_nieistniejacej_osoby(self):
        self.assertEqual(
            self.client.get(reverse('groby:osoba_detail', args=[99999])).status_code,
            404,
        )


class WyszukiwarkaTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sektor_a = Sektor.objects.create(nazwa='A')
        cls.sektor_b = Sektor.objects.create(nazwa='B')
        grob_a = Grob.objects.create(sektor=cls.sektor_a, numer='1')
        grob_b = Grob.objects.create(sektor=cls.sektor_b, numer='1', typ='murowany')
        Osoba.objects.create(grob=grob_a, imie='Jan', nazwisko='Kowalski', data_smierci=date(1990, 1, 1))
        Osoba.objects.create(grob=grob_a, imie='Anna', nazwisko='Kowalska', nazwisko_rodowe='Malinowska', data_smierci=date(1985, 1, 1))
        Osoba.objects.create(grob=grob_b, imie='Piotr', nazwisko='Zieliński', data_smierci=date(2020, 1, 1))

    def test_bez_parametrow_pokazuje_ekran_startowy(self):
        r = self.client.get(reverse('groby:szukaj'))
        self.assertContains(r, 'Rozpocznij wyszukiwanie')

    def test_szuka_po_nazwisku(self):
        r = self.client.get(reverse('groby:szukaj'), {'q': 'Kowalski'})
        self.assertContains(r, 'Kowalski')
        self.assertNotContains(r, 'Zieliński')

    def test_szuka_po_nazwisku_rodowym(self):
        r = self.client.get(reverse('groby:szukaj'), {'q': 'Malinowska'})
        self.assertContains(r, 'Kowalska')

    def test_filtr_sektora(self):
        r = self.client.get(reverse('groby:szukaj'), {'q': '', 'sektor': self.sektor_b.pk})
        self.assertContains(r, 'Zieliński')
        self.assertNotContains(r, 'Kowalski')

    def test_filtr_typu(self):
        r = self.client.get(reverse('groby:szukaj'), {'q': '', 'typ': 'murowany'})
        self.assertContains(r, 'Zieliński')

    def test_filtr_rok_od(self):
        r = self.client.get(reverse('groby:szukaj'), {'q': '', 'rok_od': '2000'})
        self.assertContains(r, 'Zieliński')
        self.assertNotContains(r, 'Kowalski')

    def test_brak_wynikow(self):
        r = self.client.get(reverse('groby:szukaj'), {'q': 'Xyzqwerty'})
        self.assertContains(r, 'Brak wyników')


# ---------- Testy API ----------


class SugestieAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        sektor = Sektor.objects.create(nazwa='A')
        grob = Grob.objects.create(sektor=sektor, numer='1')
        Osoba.objects.create(grob=grob, imie='Jan', nazwisko='Kowalski')
        Osoba.objects.create(grob=grob, imie='Anna', nazwisko='Nowak')

    def test_zbyt_krotkie_q_zwraca_pusto(self):
        r = self.client.get(reverse('groby:sugestie'), {'q': 'a'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['results'], [])

    def test_znajduje_po_prefiksie_nazwiska(self):
        r = self.client.get(reverse('groby:sugestie'), {'q': 'Kow'})
        results = r.json()['results']
        self.assertEqual(len(results), 1)
        self.assertIn('Kowalski', results[0]['nazwa'])

    def test_kazdy_wynik_ma_wymagane_pola(self):
        r = self.client.get(reverse('groby:sugestie'), {'q': 'Jan'})
        for wynik in r.json()['results']:
            self.assertIn('nazwa', wynik)
            self.assertIn('lata', wynik)
            self.assertIn('grob', wynik)
            self.assertIn('url', wynik)

    def test_zwraca_maksimum_8_wynikow(self):
        sektor = Sektor.objects.first()
        for i in range(15):
            grob = Grob.objects.create(sektor=sektor, numer=f'{i + 100}')
            Osoba.objects.create(grob=grob, imie='Test', nazwisko=f'Szukowski{i:02d}')
        r = self.client.get(reverse('groby:sugestie'), {'q': 'Szuk'})
        self.assertLessEqual(len(r.json()['results']), 8)


# ---------- Testy filtrów szablonu ----------


class PolishPluralTest(TestCase):
    FORMS = 'grób,groby,grobów'

    def test_forma_pojedyncza_dla_1(self):
        self.assertEqual(polish_plural(1, self.FORMS), 'grób')

    def test_forma_kilka_dla_2_3_4(self):
        for n in (2, 3, 4, 22, 23, 24, 102, 103):
            self.assertEqual(polish_plural(n, self.FORMS), 'groby', msg=f'n={n}')

    def test_forma_wiele_dla_pozostalych(self):
        for n in (0, 5, 10, 11, 12, 13, 14, 15, 19, 21, 25, 100):
            self.assertEqual(polish_plural(n, self.FORMS), 'grobów', msg=f'n={n}')

    def test_niepoprawny_input_zwraca_pusto(self):
        self.assertEqual(polish_plural('abc', self.FORMS), '')
        self.assertEqual(polish_plural(None, self.FORMS), '')
        self.assertEqual(polish_plural(5, 'tylko_jedna_forma'), '')


# ---------- Testy funkcji pomocniczych importu Excela ----------


class ImportExcelParsingTest(TestCase):
    def test_parsuj_date_rozne_formaty(self):
        from groby.management.commands.import_excel import parsuj_date
        self.assertEqual(parsuj_date('2020-05-15'), date(2020, 5, 15))
        self.assertEqual(parsuj_date('15.05.2020'), date(2020, 5, 15))
        self.assertEqual(parsuj_date('15/05/2020'), date(2020, 5, 15))
        self.assertEqual(parsuj_date('1985'), date(1985, 1, 1))

    def test_parsuj_date_pusta_wartosc(self):
        from groby.management.commands.import_excel import parsuj_date
        self.assertIsNone(parsuj_date(''))
        self.assertIsNone(parsuj_date(None))
        self.assertIsNone(parsuj_date('niepoprawna'))

    def test_parsuj_float_kropka_i_przecinek(self):
        from groby.management.commands.import_excel import parsuj_float
        self.assertEqual(parsuj_float('50.5'), 50.5)
        self.assertEqual(parsuj_float('50,5'), 50.5)

    def test_parsuj_float_niepoprawne(self):
        from groby.management.commands.import_excel import parsuj_float
        self.assertIsNone(parsuj_float(''))
        self.assertIsNone(parsuj_float(None))
        self.assertIsNone(parsuj_float('abc'))

    def test_parsuj_typ_mapuje_aliasy(self):
        from groby.management.commands.import_excel import parsuj_typ
        self.assertEqual(parsuj_typ('ziemny'), 'ziemny')
        self.assertEqual(parsuj_typ('Urnowy'), 'urnowy')
        self.assertEqual(parsuj_typ('kolumbarium'), 'urnowy')
        self.assertEqual(parsuj_typ('Masowy'), 'zbiorowy')

    def test_parsuj_typ_nieznany_jako_inny(self):
        from groby.management.commands.import_excel import parsuj_typ
        self.assertEqual(parsuj_typ('dziwny_typ'), 'inny')

    def test_parsuj_typ_pusty_jako_ziemny(self):
        from groby.management.commands.import_excel import parsuj_typ
        self.assertEqual(parsuj_typ(''), 'ziemny')
        self.assertEqual(parsuj_typ(None), 'ziemny')
