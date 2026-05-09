from django.conf import settings
from django.db import models


class Sektor(models.Model):
    nazwa = models.CharField(max_length=50, unique=True, verbose_name='Nazwa sektora')
    opis = models.TextField(blank=True, verbose_name='Opis')

    class Meta:
        verbose_name = 'Sektor'
        verbose_name_plural = 'Sektory'
        ordering = ['nazwa']

    def __str__(self):
        return self.nazwa


class Grob(models.Model):
    TYP_CHOICES = [
        ('ziemny', 'Grób ziemny'),
        ('murowany', 'Grób murowany'),
        ('rodzinny', 'Grób rodzinny'),
        ('urnowy', 'Grób urnowy'),
        ('zbiorowy', 'Grób zbiorowy'),
        ('inny', 'Inny'),
    ]

    OPLATA_CHOICES = [
        ('tak', 'Tak'),
        ('nie', 'Nie'),
        ('brak_danych', 'Brak danych'),
    ]

    sektor = models.ForeignKey(Sektor, on_delete=models.PROTECT, related_name='groby', verbose_name='Sektor (kwatera)')
    numer = models.CharField(max_length=20, verbose_name='Numer grobu')
    rzad = models.CharField(max_length=20, blank=True, verbose_name='Rząd')
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, default='ziemny', verbose_name='Typ grobu')
    rodzaj_opis = models.CharField(max_length=255, blank=True, verbose_name='Rodzaj nagrobka (opis)')
    numer_aktu = models.CharField(max_length=50, blank=True, verbose_name='Numer aktu w księdze zmarłych')
    oplata = models.CharField(max_length=20, choices=OPLATA_CHOICES, blank=True, verbose_name='Opłata za nagrobek')
    link_zdjecia = models.URLField(max_length=500, blank=True, verbose_name='Link do zdjęcia nagrobka')
    szerokosc_geo = models.FloatField(null=True, blank=True, verbose_name='Szerokość geograficzna')
    dlugosc_geo = models.FloatField(null=True, blank=True, verbose_name='Długość geograficzna')
    plan_x = models.FloatField(null=True, blank=True, verbose_name='Pozycja X na planie (px)')
    plan_y = models.FloatField(null=True, blank=True, verbose_name='Pozycja Y na planie (px)')
    zdjecie = models.ImageField(upload_to='groby/', blank=True, null=True, verbose_name='Zdjęcie')
    uwagi = models.TextField(blank=True, verbose_name='Uwagi')
    data_dodania = models.DateTimeField(auto_now_add=True)
    data_modyfikacji = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Grób'
        verbose_name_plural = 'Groby'
        unique_together = [['sektor', 'rzad', 'numer']]
        ordering = ['sektor__nazwa', 'rzad', 'numer']

    def __str__(self):
        if self.rzad:
            return f'{self.sektor.nazwa}/{self.rzad}/{self.numer}'
        return f'{self.sektor.nazwa}/{self.numer}'


class Osoba(models.Model):
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE, related_name='osoby', verbose_name='Grób')
    imie = models.CharField(max_length=100, verbose_name='Imię')
    drugie_imie = models.CharField(max_length=100, blank=True, verbose_name='Drugie imię')
    nazwisko = models.CharField(max_length=100, verbose_name='Nazwisko')
    nazwisko_rodowe = models.CharField(max_length=100, blank=True, verbose_name='Nazwisko rodowe')
    data_urodzenia = models.DateField(null=True, blank=True, verbose_name='Data urodzenia')
    data_smierci = models.DateField(null=True, blank=True, verbose_name='Data śmierci')
    miejsce_urodzenia = models.CharField(max_length=200, blank=True, verbose_name='Miejsce urodzenia')
    biogram = models.TextField(blank=True, verbose_name='Biogram / uwagi')

    class Meta:
        verbose_name = 'Osoba'
        verbose_name_plural = 'Osoby'
        ordering = ['nazwisko', 'imie']

    def __str__(self):
        if self.nazwisko_rodowe:
            return f'{self.imie} {self.nazwisko} (z d. {self.nazwisko_rodowe})'
        return f'{self.imie} {self.nazwisko}'

    @property
    def wiek(self):
        if self.data_urodzenia and self.data_smierci:
            lata = self.data_smierci.year - self.data_urodzenia.year
            if (self.data_smierci.month, self.data_smierci.day) < (self.data_urodzenia.month, self.data_urodzenia.day):
                lata -= 1
            return lata
        return None


class Zdjecie(models.Model):
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE, related_name='zdjecia', verbose_name='Grób')
    plik = models.ImageField(upload_to='groby/galeria/', verbose_name='Zdjęcie')
    podpis = models.CharField(max_length=200, blank=True, verbose_name='Podpis')
    data_dodania = models.DateTimeField(auto_now_add=True)
    kolejnosc = models.PositiveSmallIntegerField(default=0, verbose_name='Kolejność')

    class Meta:
        verbose_name = 'Zdjęcie'
        verbose_name_plural = 'Zdjęcia'
        ordering = ['kolejnosc', 'data_dodania']

    def __str__(self):
        return f'Zdjęcie {self.pk} — grób {self.grob}'

    def miniatura_url(self, szer=600):
        """Generuje miniaturę przy pierwszym dostępie i cache'uje na dysku."""
        import os
        from PIL import Image
        from django.conf import settings
        if not self.plik:
            return ''
        try:
            sciezka_orig = self.plik.path
        except (NotImplementedError, ValueError):
            return self.plik.url
        nazwa_orig = os.path.basename(sciezka_orig)
        baza, ext = os.path.splitext(nazwa_orig)
        nazwa_min = f'{baza}_w{szer}{ext}'
        sciezka_min = os.path.join(settings.MEDIA_ROOT, 'thumbs', nazwa_min)
        if not os.path.exists(sciezka_min):
            os.makedirs(os.path.dirname(sciezka_min), exist_ok=True)
            try:
                with Image.open(sciezka_orig) as im:
                    im.thumbnail((szer, szer * 4))
                    im.save(sciezka_min, optimize=True, quality=85)
            except (OSError, IOError):
                return self.plik.url
        return settings.MEDIA_URL + 'thumbs/' + nazwa_min


class Relacja(models.Model):
    TYP_CHOICES = [
        ('rodzic', 'Rodzic — Dziecko'),
        ('malzenstwo', 'Małżeństwo'),
        ('rodzenstwo', 'Rodzeństwo'),
        ('inny', 'Inna relacja'),
    ]
    osoba_a = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='relacje_a', verbose_name='Osoba A (np. rodzic)')
    osoba_b = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='relacje_b', verbose_name='Osoba B (np. dziecko)')
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, verbose_name='Typ relacji')
    uwagi = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Relacja rodzinna'
        verbose_name_plural = 'Relacje rodzinne'
        unique_together = [['osoba_a', 'osoba_b', 'typ']]

    def __str__(self):
        return f'{self.osoba_a} — {self.get_typ_display()} — {self.osoba_b}'


class Zgloszenie(models.Model):
    STATUS_CHOICES = [
        ('nowe', 'Nowe'),
        ('w_trakcie', 'W trakcie'),
        ('zaakceptowane', 'Zaakceptowane'),
        ('odrzucone', 'Odrzucone'),
    ]
    grob = models.ForeignKey(Grob, on_delete=models.SET_NULL, null=True, blank=True, related_name='zgloszenia', verbose_name='Grób')
    osoba = models.ForeignKey(Osoba, on_delete=models.SET_NULL, null=True, blank=True, related_name='zgloszenia', verbose_name='Osoba')
    typ = models.CharField(max_length=50, default='poprawka', verbose_name='Typ zgłoszenia')
    tresc = models.TextField(verbose_name='Treść zgłoszenia')
    autor_imie = models.CharField(max_length=100, blank=True, verbose_name='Imię i nazwisko zgłaszającego')
    autor_email = models.EmailField(blank=True, verbose_name='E-mail (opcjonalnie)')
    autor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='zgloszenia', verbose_name='Konto')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='nowe')
    odpowiedz = models.TextField(blank=True, verbose_name='Odpowiedź administratora')
    data_dodania = models.DateTimeField(auto_now_add=True)
    data_modyfikacji = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Zgłoszenie'
        verbose_name_plural = 'Zgłoszenia'
        ordering = ['-data_dodania']

    def __str__(self):
        cel = self.osoba or self.grob or '—'
        return f'Zgłoszenie {self.pk}: {cel} ({self.get_status_display()})'


class Profil(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profil')
    obserwowane_groby = models.ManyToManyField(Grob, blank=True, related_name='obserwujacy', verbose_name='Obserwowane groby')
    obserwowane_osoby = models.ManyToManyField(Osoba, blank=True, related_name='obserwujacy', verbose_name='Obserwowane osoby')
    pokrewienstwo = models.CharField(max_length=200, blank=True, verbose_name='Pokrewieństwo / opis')
    data_utworzenia = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Profil użytkownika'
        verbose_name_plural = 'Profile użytkowników'

    def __str__(self):
        return f'Profil: {self.user}'


class Wspomnienie(models.Model):
    STATUS_CHOICES = [
        ('oczekuje', 'Oczekuje'),
        ('zaakceptowane', 'Zaakceptowane'),
        ('odrzucone', 'Odrzucone'),
    ]
    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='wspomnienia', verbose_name='Osoba')
    autor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='wspomnienia')
    autor_imie = models.CharField(max_length=100, blank=True, verbose_name='Imię i nazwisko zgłaszającego')
    tresc = models.TextField(verbose_name='Treść wspomnienia')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='oczekuje')
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Wspomnienie'
        verbose_name_plural = 'Wspomnienia'
        ordering = ['-data_dodania']

    def __str__(self):
        return f'Wspomnienie {self.pk} — {self.osoba}'

    @property
    def autor_str(self):
        if self.autor_user:
            return self.autor_user.get_full_name() or self.autor_user.username
        return self.autor_imie or 'Anonim'


class Swieca(models.Model):
    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='swiece', verbose_name='Osoba')
    autor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='swiece')
    intencja = models.CharField(max_length=200, blank=True, verbose_name='Intencja / dedykacja')
    ip_hash = models.CharField(max_length=64, blank=True)
    data_zapalenia = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Świeczka'
        verbose_name_plural = 'Świeczki'
        ordering = ['-data_zapalenia']

    def __str__(self):
        return f'Świeczka {self.pk} dla {self.osoba}'


class ZapisaneSzukanie(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='zapisane_szukania')
    nazwa = models.CharField(max_length=100, verbose_name='Nazwa wyszukiwania')
    querystring = models.CharField(max_length=500, verbose_name='Parametry filtru')
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    ostatnie_uzycie = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Zapisane wyszukiwanie'
        verbose_name_plural = 'Zapisane wyszukiwania'
        ordering = ['-ostatnie_uzycie', '-data_utworzenia']

    def __str__(self):
        return f'{self.nazwa} ({self.user})'


class Wpis(models.Model):
    TYP_CHOICES = [
        ('postac', 'Znana postać'),
        ('wydarzenie', 'Wydarzenie'),
        ('historia', 'Tekst historyczny'),
    ]
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, default='postac')
    tytul = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    podpis = models.CharField(max_length=300, blank=True, verbose_name='Krótki opis (lead)')
    tresc = models.TextField()
    osoba = models.ForeignKey(Osoba, on_delete=models.SET_NULL, null=True, blank=True, related_name='wpisy', verbose_name='Powiązana osoba (opcjonalnie)')
    zdjecie = models.ImageField(upload_to='wpisy/', blank=True, null=True)
    data_publikacji = models.DateField(null=True, blank=True, verbose_name='Data publikacji')
    opublikowany = models.BooleanField(default=False)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    data_dodania = models.DateTimeField(auto_now_add=True)
    data_modyfikacji = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Wpis (blog/postać)'
        verbose_name_plural = 'Wpisy (blog/postacie)'
        ordering = ['-data_publikacji', '-data_dodania']

    def __str__(self):
        return f'{self.get_typ_display()}: {self.tytul}'


class Tag(models.Model):
    nazwa = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    opis = models.CharField(max_length=255, blank=True)
    osoby = models.ManyToManyField(Osoba, related_name='tagi', blank=True)

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tagi'
        ordering = ['nazwa']

    def __str__(self):
        return self.nazwa


class Panorama(models.Model):
    nazwa = models.CharField(max_length=200)
    plik = models.ImageField(upload_to='panoramy/')
    opis = models.TextField(blank=True)
    sektor = models.ForeignKey(Sektor, on_delete=models.SET_NULL, null=True, blank=True, related_name='panoramy')
    pitch = models.FloatField(default=0, help_text='Domyślny pitch widoku w stopniach')
    yaw = models.FloatField(default=0, help_text='Domyślny yaw widoku w stopniach')
    hfov = models.FloatField(default=110, help_text='Domyślny horizontal FOV')
    kolejnosc = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Panorama 360°'
        verbose_name_plural = 'Panoramy 360°'
        ordering = ['kolejnosc', 'nazwa']

    def __str__(self):
        return self.nazwa


class HotspotPanoramy(models.Model):
    """Punkt na panoramie 360° → grób lub inna panorama."""
    panorama = models.ForeignKey(Panorama, on_delete=models.CASCADE, related_name='hotspoty')
    pitch = models.FloatField()
    yaw = models.FloatField()
    etykieta = models.CharField(max_length=120, blank=True)
    grob = models.ForeignKey(Grob, on_delete=models.SET_NULL, null=True, blank=True)
    docelowa_panorama = models.ForeignKey(Panorama, on_delete=models.SET_NULL, null=True, blank=True, related_name='przejscia_z')

    class Meta:
        verbose_name = 'Hotspot panoramy'
        verbose_name_plural = 'Hotspoty panoram'

    def __str__(self):
        return f'{self.panorama} @ {self.pitch:.1f},{self.yaw:.1f}'


class SubskrypcjaPush(models.Model):
    """Subskrypcja Web Push z serviceWorker.subscribe()."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subskrypcje_push', null=True, blank=True)
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=80)
    data_dodania = models.DateTimeField(auto_now_add=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Subskrypcja Push'
        verbose_name_plural = 'Subskrypcje Push'

    def __str__(self):
        return f'Push {self.pk} ({self.user or "anon"})'


class TokenLogowania(models.Model):
    """Magic-link token. Wygasa po 30 minutach lub po jednym użyciu."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    data_wygasniecia = models.DateTimeField()
    wykorzystany = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Token logowania (magic link)'
        verbose_name_plural = 'Tokeny logowania'

    def __str__(self):
        return f'Token {self.user} ({"wykorzystany" if self.wykorzystany else "aktywny"})'


class Komentarz(models.Model):
    """Komentarz pod wspomnieniem (1-poziomowe wątki)."""
    wspomnienie = models.ForeignKey(Wspomnienie, on_delete=models.CASCADE, related_name='komentarze')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='odpowiedzi')
    autor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    autor_imie = models.CharField(max_length=100, blank=True)
    tresc = models.TextField()
    zaakceptowany = models.BooleanField(default=False)
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Komentarz'
        verbose_name_plural = 'Komentarze'
        ordering = ['data_dodania']

    def __str__(self):
        return f'Komentarz {self.pk} pod {self.wspomnienie}'


class Trasa(models.Model):
    nazwa = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    opis = models.TextField(blank=True)
    audio = models.FileField(upload_to='trasy/audio/', blank=True, null=True, verbose_name='Przewodnik audio (mp3)')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    opublikowana = models.BooleanField(default=False)
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Trasa zwiedzania'
        verbose_name_plural = 'Trasy zwiedzania'
        ordering = ['nazwa']

    def __str__(self):
        return self.nazwa


class TrasaPunkt(models.Model):
    trasa = models.ForeignKey(Trasa, on_delete=models.CASCADE, related_name='punkty')
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE)
    kolejnosc = models.PositiveSmallIntegerField(default=0)
    podpis = models.TextField(blank=True, verbose_name='Komentarz przewodnika')

    class Meta:
        verbose_name = 'Punkt trasy'
        verbose_name_plural = 'Punkty tras'
        ordering = ['kolejnosc']
        unique_together = [['trasa', 'grob']]


class Odznaka(models.Model):
    KOD_CHOICES = [
        ('strazn', 'Strażnik pamięci (10 świec)'),
        ('kron', 'Kronikarz (5 wspomnień)'),
        ('genea', 'Genealog (3 relacje)'),
        ('prze', 'Przewodnik (1 trasa)'),
        ('hist', 'Historyk (1 wpis)'),
    ]
    kod = models.CharField(max_length=20, choices=KOD_CHOICES, unique=True)
    nazwa = models.CharField(max_length=100)
    opis = models.TextField(blank=True)
    ikona = models.CharField(max_length=10, default='🏆', help_text='Emoji/glyph')

    class Meta:
        verbose_name = 'Odznaka'
        verbose_name_plural = 'Odznaki'

    def __str__(self):
        return self.nazwa


class UzytkownikOdznaka(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='odznaki')
    odznaka = models.ForeignKey(Odznaka, on_delete=models.CASCADE)
    data_zdobycia = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'odznaka']]
        ordering = ['-data_zdobycia']


class Newsletter(models.Model):
    email = models.EmailField(unique=True)
    aktywny = models.BooleanField(default=True)
    token_anulowania = models.CharField(max_length=64, unique=True)
    data_dodania = models.DateTimeField(auto_now_add=True)
    ostatnia_wysylka = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Subskrybent newslettera'
        verbose_name_plural = 'Subskrybenci newslettera'

    def __str__(self):
        return f'{self.email} ({"✓" if self.aktywny else "✗"})'


class Kwiat(models.Model):
    """Wirtualny kwiat położony na grobie. TTL 7 dni."""
    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='kwiaty')
    autor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    autor_imie = models.CharField(max_length=100, blank=True)
    wiadomosc = models.CharField(max_length=300, blank=True)
    rodzaj = models.CharField(max_length=20, default='roza', choices=[
        ('roza', 'Róża'),
        ('lilia', 'Lilia'),
        ('chryzantema', 'Chryzantema'),
        ('tulipan', 'Tulipan'),
    ])
    ip_hash = models.CharField(max_length=64, blank=True)
    data_zlozenia = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Kwiat'
        verbose_name_plural = 'Kwiaty'
        ordering = ['-data_zlozenia']


class Nagranie(models.Model):
    """Audio/video pożegnanie do grobu."""
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE, related_name='nagrania')
    osoba = models.ForeignKey(Osoba, on_delete=models.SET_NULL, null=True, blank=True, related_name='nagrania')
    typ = models.CharField(max_length=10, choices=[('audio', 'Audio'), ('video', 'Wideo')], default='audio')
    plik = models.FileField(upload_to='nagrania/')
    tytul = models.CharField(max_length=200)
    opis = models.TextField(blank=True)
    autor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    zaakceptowane = models.BooleanField(default=False)
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Nagranie'
        verbose_name_plural = 'Nagrania'
        ordering = ['-data_dodania']

    def __str__(self):
        return f'{self.get_typ_display()}: {self.tytul}'


class GlosNagrobek(models.Model):
    """Plebiscyt nagrobków — głos na grób."""
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE, related_name='glosy')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    ip_hash = models.CharField(max_length=64)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Głos w plebiscycie'
        verbose_name_plural = 'Głosy w plebiscycie'
        unique_together = [['grob', 'ip_hash']]


class IntencjaMszalna(models.Model):
    STATUS_CHOICES = [
        ('nowa', 'Nowa'),
        ('przyjeta', 'Przyjęta'),
        ('odprawiona', 'Odprawiona'),
        ('odrzucona', 'Odrzucona'),
    ]
    osoba = models.ForeignKey(Osoba, on_delete=models.SET_NULL, null=True, blank=True, related_name='intencje')
    zamawiajacy_imie = models.CharField(max_length=200)
    zamawiajacy_email = models.EmailField()
    zamawiajacy_tel = models.CharField(max_length=30, blank=True)
    intencja = models.TextField()
    proponowana_data = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='nowa')
    notatka_kapelana = models.TextField(blank=True)
    data_zlozenia = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Intencja mszalna'
        verbose_name_plural = 'Intencje mszalne'
        ordering = ['-data_zlozenia']


class Zaproszenie(models.Model):
    """Zaproszenie do współedycji konkretnej osoby (rodzina krewna)."""
    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='zaproszenia')
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    wykorzystane_przez = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='przyjete_zaproszenia')
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    data_wykorzystania = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Zaproszenie do edycji'
        verbose_name_plural = 'Zaproszenia do edycji'


class ZdjecieWpisu(models.Model):
    wpis = models.ForeignKey(Wpis, on_delete=models.CASCADE, related_name='zdjecia_dodatkowe')
    plik = models.ImageField(upload_to='wpisy/galeria/')
    podpis = models.CharField(max_length=200, blank=True)
    kolejnosc = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Zdjęcie wpisu'
        verbose_name_plural = 'Zdjęcia wpisów'
        ordering = ['kolejnosc']


class GeoCache(models.Model):
    """Cache geokodowania (miejsce -> lat/lng)."""
    nazwa = models.CharField(max_length=200, unique=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    znaleziono = models.BooleanField(default=False)
    data_zapytania = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cache geokodowania'
        verbose_name_plural = 'Cache geokodowania'

    def __str__(self):
        return f'{self.nazwa} → ({self.lat}, {self.lng})'


class HistoriaZmian(models.Model):
    AKCJA_CHOICES = [
        ('dodano', 'Dodano'),
        ('zmieniono', 'Zmieniono'),
        ('usunieto', 'Usunięto'),
    ]
    model = models.CharField(max_length=50)
    obiekt_id = models.PositiveIntegerField()
    obiekt_repr = models.CharField(max_length=255)
    akcja = models.CharField(max_length=20, choices=AKCJA_CHOICES)
    pola = models.JSONField(default=dict, blank=True, verbose_name='Zmienione pola')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historia zmiany'
        verbose_name_plural = 'Historia zmian'
        ordering = ['-data']
        indexes = [models.Index(fields=['model', 'obiekt_id'])]

    def __str__(self):
        return f'{self.data:%Y-%m-%d %H:%M} {self.get_akcja_display()} {self.model}#{self.obiekt_id}'
