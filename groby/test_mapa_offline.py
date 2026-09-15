"""
Testy: sieć alejek i wskazówki dojścia, krótkie linki QR, service worker offline,
zajętość kwater w statystykach.
"""
import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Alejka, Brama, Grob, Osoba, Sektor
from .nawigacja import zbuduj_graf

User = get_user_model()


class ZbudujGrafTest(TestCase):
    def test_pusta_siec(self):
        self.assertEqual(zbuduj_graf([]), {'wezly': [], 'krawedzie': []})

    def test_bliskie_punkty_scalane_w_skrzyzowanie(self):
        graf = zbuduj_graf([
            ('Główna', [[0, 0], [100, 0]]),
            ('Boczna', [[100, 5], [100, 100]]),   # koniec 5 px od końca Głównej
        ], tolerancja=10)
        self.assertEqual(len(graf['wezly']), 3)
        self.assertEqual(len(graf['krawedzie']), 2)

    def test_rozwidlenie_t_dzieli_odcinek(self):
        graf = zbuduj_graf([
            ('Główna', [[0, 0], [200, 0]]),
            ('Boczna', [[100, 3], [100, 150]]),   # dochodzi do środka Głównej
        ], tolerancja=10)
        nazwy = sorted(k[2] for k in graf['krawedzie'])
        self.assertEqual(nazwy, ['Boczna', 'Główna', 'Główna'])

    def test_bledne_punkty_pomijane(self):
        graf = zbuduj_graf([('X', [[0, 0], 'zle', [None], [50, 50]])])
        self.assertEqual(len(graf['krawedzie']), 1)


class EdytorAlejekTest(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('staff', password='x', is_staff=True)
        self.zwykly = User.objects.create_user('jan', password='x')

    def _post(self, nazwa_url, dane, **kw):
        return self.client.post(reverse(nazwa_url, **kw), json.dumps(dane), content_type='application/json')

    def test_gosc_i_zwykly_uzytkownik_nie_moga_zapisac(self):
        dane = {'nazwa': 'A', 'punkty': [[0, 0], [10, 10]]}
        self.assertEqual(self._post('groby:zapisz_alejke', dane).status_code, 403)
        self.client.force_login(self.zwykly)
        self.assertEqual(self._post('groby:zapisz_alejke', dane).status_code, 403)
        self.assertFalse(Alejka.objects.exists())

    def test_staff_zapisuje_i_usuwa_alejke(self):
        self.client.force_login(self.staff)
        r = self._post('groby:zapisz_alejke', {'nazwa': 'Główna', 'punkty': [[0, 0], [10, 10], [20, 5]]})
        self.assertTrue(r.json()['ok'])
        alejka = Alejka.objects.get()
        self.assertEqual(alejka.punkty, [[0.0, 0.0], [10.0, 10.0], [20.0, 5.0]])
        r = self._post('groby:usun_alejke', {}, args=[alejka.pk])
        self.assertTrue(r.json()['ok'])
        self.assertFalse(Alejka.objects.exists())

    def test_alejka_z_jednym_punktem_odrzucona(self):
        self.client.force_login(self.staff)
        r = self._post('groby:zapisz_alejke', {'punkty': [[0, 0]]})
        self.assertEqual(r.status_code, 400)
        r = self._post('groby:zapisz_alejke', ['nie', 'slownik'])
        self.assertEqual(r.status_code, 400)

    def test_staff_zapisuje_brame(self):
        self.client.force_login(self.staff)
        r = self._post('groby:zapisz_brame', {'nazwa': 'Brama główna', 'x': 5, 'y': 7})
        self.assertTrue(r.json()['ok'])
        self.assertEqual(Brama.objects.get().plan_y, 7)

    def test_mapa_przekazuje_graf_i_bramy(self):
        Alejka.objects.create(nazwa='Główna', punkty=[[0, 0], [100, 0]])
        Brama.objects.create(nazwa='Brama główna', plan_x=0, plan_y=0)
        r = self.client.get(reverse('groby:mapa'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(json.loads(r.context['graf_json'])['krawedzie']), 1)
        self.assertEqual(json.loads(r.context['bramy_json'])[0]['nazwa'], 'Brama główna')
        # Surowe alejki (do edycji) tylko dla staffu.
        self.assertEqual(json.loads(r.context['alejki_json']), [])


class QrKrotkiLinkTest(TestCase):
    def setUp(self):
        self.grob = Grob.objects.create(sektor=Sektor.objects.create(nazwa='A'), numer='1')

    def test_krotki_link_przekierowuje_na_karte(self):
        r = self.client.get(reverse('groby:grob_krotki', args=[self.grob.pk]))
        self.assertRedirects(r, reverse('groby:grob_detail', args=[self.grob.pk]))

    def test_qr_png(self):
        r = self.client.get(reverse('groby:grob_qr', args=[self.grob.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'image/png')

    def test_nieistniejacy_grob(self):
        self.assertEqual(self.client.get(reverse('groby:grob_krotki', args=[999])).status_code, 404)


class ServiceWorkerOfflineTest(TestCase):
    def test_sw_obsluguje_zapis_offline_i_dopuszcza_cdn(self):
        r = self.client.get(reverse('groby:sw'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('zapisz-offline', r.content.decode())
        self.assertIn('https://unpkg.com', r['Content-Security-Policy'])


class ZajetoscKwaterTest(TestCase):
    def test_zajetosc_wzgledem_ksiegi_i_pojemnosci(self):
        a = Sektor.objects.create(nazwa='A')
        b = Sektor.objects.create(nazwa='B', liczba_miejsc=10)
        g1 = Grob.objects.create(sektor=a, numer='1')
        Grob.objects.create(sektor=a, numer='2')
        g3 = Grob.objects.create(sektor=b, numer='1')
        Osoba.objects.create(imie='Jan', nazwisko='Nowak', grob=g1, data_smierci=date(1950, 3, 1))
        Osoba.objects.create(imie='Anna', nazwisko='Nowak', grob=g1, data_smierci=date(1972, 1, 1))
        Osoba.objects.create(imie='Piotr', nazwisko='Kos', grob=g3, data_smierci=date(1988, 5, 5))

        r = self.client.get(reverse('groby:statystyki'))
        self.assertEqual(r.status_code, 200)
        zaj = {z['sektor']: z for z in r.context['zajetosc']}
        self.assertEqual((zaj['A']['pojemnosc'], zaj['A']['zajete'], zaj['A']['wolne']), (2, 1, 1))
        self.assertTrue(zaj['A']['szacowana'])
        self.assertEqual(zaj['A']['pochowanych'], 2)
        self.assertEqual(zaj['A']['ostatni_rok'], 1972)
        self.assertEqual((zaj['B']['procent'], zaj['B']['szacowana']), (10.0, False))

        dekady = json.loads(r.context['dekady_json'])
        self.assertEqual(dekady[-1]['narastajaco'], 3)
