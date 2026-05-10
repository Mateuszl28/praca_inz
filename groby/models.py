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
    epitafium = models.CharField(max_length=400, blank=True, verbose_name='Epitafium / motto na nagrobku')

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
    onboarding_zakonczony = models.BooleanField(default=False)
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
    tagi_tresci = models.ManyToManyField('TagWpisu', blank=True, related_name='wpisy', verbose_name='Tagi tematyczne')
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
    audio = models.FileField(upload_to='panoramy/audio/', blank=True, null=True, verbose_name='Audio przewodnik (MP3)')

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


class List(models.Model):
    """List wirtualny do zmarłej osoby."""
    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='listy')
    autor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    autor_imie = models.CharField(max_length=100, blank=True)
    tresc = models.TextField()
    publiczny = models.BooleanField(default=False, verbose_name='Publiczny (widoczny na ścianie)')
    zaakceptowany = models.BooleanField(default=False)
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'List do zmarłego'
        verbose_name_plural = 'Listy do zmarłych'
        ordering = ['-data_dodania']

    @property
    def autor_str(self):
        if self.autor_user:
            return self.autor_user.username
        return self.autor_imie or 'Anonim'


class PytanieQuiz(models.Model):
    pytanie = models.CharField(max_length=500)
    odpowiedzi = models.JSONField(help_text='Lista 4 odpowiedzi (pierwsza jest poprawna).')
    wyjasnienie = models.TextField(blank=True)
    osoba = models.ForeignKey(Osoba, on_delete=models.SET_NULL, null=True, blank=True, help_text='Osoba związana z pytaniem.')
    aktywne = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Pytanie quiz'
        verbose_name_plural = 'Pytania quizu'

    def __str__(self):
        return self.pytanie[:80]


class WatekForum(models.Model):
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE, related_name='watki')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    tytul = models.CharField(max_length=200)
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    data_ostatniego_postu = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Wątek forum'
        verbose_name_plural = 'Wątki forum'
        ordering = ['-data_ostatniego_postu']

    def __str__(self):
        return self.tytul


class PostForum(models.Model):
    watek = models.ForeignKey(WatekForum, on_delete=models.CASCADE, related_name='posty')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    tresc = models.TextField()
    zaakceptowany = models.BooleanField(default=False)
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Post w forum'
        verbose_name_plural = 'Posty w forum'
        ordering = ['data_dodania']


class Webhook(models.Model):
    EVENT_CHOICES = [
        ('zgloszenie.nowe', 'Nowe zgłoszenie'),
        ('wspomnienie.zaakceptowane', 'Zaakceptowane wspomnienie'),
        ('osoba.dodano', 'Dodana osoba'),
        ('grob.zmieniono', 'Zmieniono grób'),
    ]
    TYP_CHOICES = [
        ('generic', 'Generyczny POST JSON'),
        ('discord', 'Discord'),
        ('slack', 'Slack'),
    ]
    nazwa = models.CharField(max_length=100)
    url = models.URLField(max_length=500)
    event = models.CharField(max_length=50, choices=EVENT_CHOICES)
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, default='generic')
    sekret = models.CharField(max_length=64, blank=True, help_text='Sekret do HMAC walidacji (tylko generic)')
    aktywny = models.BooleanField(default=True)
    licznik_wywolan = models.PositiveIntegerField(default=0)
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Webhook'
        verbose_name_plural = 'Webhooki'

    def __str__(self):
        return f'{self.nazwa} → {self.url}'


class WyszukiwanieLog(models.Model):
    fraza = models.CharField(max_length=200)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    liczba_wynikow = models.IntegerField(default=0)
    data = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Log wyszukiwania'
        verbose_name_plural = 'Logi wyszukiwań'
        ordering = ['-data']


class ZdjecieDronowe(models.Model):
    plik = models.ImageField(upload_to='drony/')
    tytul = models.CharField(max_length=200)
    opis = models.TextField(blank=True)
    data_wykonania = models.DateField(null=True, blank=True)
    sektor = models.ForeignKey(Sektor, on_delete=models.SET_NULL, null=True, blank=True)
    kolejnosc = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Zdjęcie z drona'
        verbose_name_plural = 'Zdjęcia z drona'
        ordering = ['kolejnosc']

    def __str__(self):
        return self.tytul


class KonkursFoto(models.Model):
    nazwa = models.CharField(max_length=200)
    opis = models.TextField(blank=True)
    data_start = models.DateField()
    data_koniec = models.DateField()
    aktywny = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Konkurs fotograficzny'
        verbose_name_plural = 'Konkursy fotograficzne'

    def __str__(self):
        return self.nazwa


class ZgloszenieKonkursowe(models.Model):
    konkurs = models.ForeignKey(KonkursFoto, on_delete=models.CASCADE, related_name='zgloszenia_foto')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    autor_imie = models.CharField(max_length=100, blank=True)
    plik = models.ImageField(upload_to='konkurs/')
    tytul = models.CharField(max_length=200, blank=True)
    grob = models.ForeignKey(Grob, on_delete=models.SET_NULL, null=True, blank=True)
    zaakceptowane = models.BooleanField(default=False)
    data_dodania = models.DateTimeField(auto_now_add=True)


class GlosKonkursowy(models.Model):
    zgloszenie = models.ForeignKey(ZgloszenieKonkursowe, on_delete=models.CASCADE, related_name='glosy')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    ip_hash = models.CharField(max_length=64)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['zgloszenie', 'ip_hash']]


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


class TagWpisu(models.Model):
    nazwa = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    opis = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'Tag wpisu'
        verbose_name_plural = 'Tagi wpisów'
        ordering = ['nazwa']

    def __str__(self):
        return self.nazwa


class PlanZwiedzania(models.Model):
    """Lista grobów do odwiedzenia (zalogowany lub anonim po cookie)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='plan_zwiedzania')
    sesja_id = models.CharField(max_length=64, blank=True, help_text='Identyfikator sesji dla anonimowych')
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE, related_name='w_planach')
    odwiedzony = models.BooleanField(default=False)
    notatka = models.CharField(max_length=300, blank=True)
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Plan zwiedzania'
        verbose_name_plural = 'Plany zwiedzania'
        ordering = ['odwiedzony', '-data_dodania']
        constraints = [
            models.UniqueConstraint(fields=['user', 'grob'], name='plan_user_grob_uniq', condition=models.Q(user__isnull=False)),
            models.UniqueConstraint(fields=['sesja_id', 'grob'], name='plan_sesja_grob_uniq', condition=models.Q(user__isnull=True)),
        ]


class OdwiedzinyOsoba(models.Model):
    """Counter dziennych odwiedzin strony osoby (do trendu sparkline)."""
    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='odwiedziny')
    data = models.DateField(db_index=True)
    licznik = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Licznik odwiedzin osoby'
        verbose_name_plural = 'Liczniki odwiedzin osób'
        unique_together = [['osoba', 'data']]
        ordering = ['-data']


class FeaturedTygodnia(models.Model):
    """Wyróżniony grób/postać/wpis na home (auto-rotacja lub ręcznie)."""
    KAT_CHOICES = [
        ('osoba', 'Osoba'),
        ('grob', 'Grób'),
        ('wpis', 'Wpis (postać/wydarzenie)'),
    ]
    kategoria = models.CharField(max_length=20, choices=KAT_CHOICES)
    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, null=True, blank=True)
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE, null=True, blank=True)
    wpis = models.ForeignKey(Wpis, on_delete=models.CASCADE, null=True, blank=True)
    tytul = models.CharField(max_length=200)
    opis = models.CharField(max_length=400, blank=True)
    od = models.DateField()
    do = models.DateField()
    aktywne = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Wyróżnienie tygodnia'
        verbose_name_plural = 'Wyróżnienia tygodnia'
        ordering = ['-od']

    def __str__(self):
        return f'{self.kategoria}: {self.tytul} ({self.od} – {self.do})'


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


# ===== Batch 91 =====


class Powiadomienie(models.Model):
    """In-app notifications dla użytkowników (komentarz, odpowiedź na forum, akceptacja zgłoszenia)."""
    TYP_CHOICES = [
        ('komentarz', 'Nowy komentarz'),
        ('forum', 'Odpowiedź na forum'),
        ('zgloszenie', 'Status zgłoszenia'),
        ('opieka', 'Opieka nad grobem'),
        ('inne', 'Inne'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='powiadomienia')
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, default='inne')
    tresc = models.CharField(max_length=300)
    url = models.CharField(max_length=300, blank=True)
    przeczytane = models.BooleanField(default=False, db_index=True)
    data = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Powiadomienie'
        verbose_name_plural = 'Powiadomienia'
        ordering = ['-data']

    def __str__(self):
        return f'{self.user}: {self.tresc[:60]}'


class OpiekunGrobu(models.Model):
    """Użytkownicy mogą zadeklarować opiekę nad konkretnym grobem (zarządzanie zgłoszeniem przez staff)."""
    STATUS_CHOICES = [
        ('oczekuje', 'Oczekuje na akceptację'),
        ('aktywny', 'Aktywny opiekun'),
        ('odrzucony', 'Odrzucony'),
        ('zakonczony', 'Opieka zakończona'),
    ]
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE, related_name='opiekunowie')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='opieka_groby')
    relacja = models.CharField(max_length=100, blank=True, help_text='Np. wnuk, prawnuczka, sąsiad')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='oczekuje')
    motywacja = models.TextField(blank=True, help_text='Dlaczego chcesz opiekować się tym grobem')
    data_zgloszenia = models.DateTimeField(auto_now_add=True)
    data_zmiany = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Opiekun grobu'
        verbose_name_plural = 'Opiekunowie grobów'
        ordering = ['-data_zmiany']
        constraints = [
            models.UniqueConstraint(fields=['grob', 'user'], name='opiekun_grob_user_uniq'),
        ]

    def __str__(self):
        return f'{self.user} ↔ {self.grob} ({self.get_status_display()})'


class PrywatnaNotatka(models.Model):
    """Notatka przypięta do osoby — widoczna tylko dla autora."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prywatne_notatki')
    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='prywatne_notatki')
    tresc = models.TextField()
    data_dodania = models.DateTimeField(auto_now_add=True)
    data_modyfikacji = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Prywatna notatka'
        verbose_name_plural = 'Prywatne notatki'
        ordering = ['-data_modyfikacji']
        indexes = [models.Index(fields=['user', 'osoba'])]

    def __str__(self):
        return f'Notatka {self.user} → {self.osoba}'


class HasloSlownik(models.Model):
    """Hasło słownika historii Szydłowa (glossary postaci, wydarzeń, miejsc)."""
    KATEGORIA_CHOICES = [
        ('postac', 'Postać'),
        ('miejsce', 'Miejsce'),
        ('wydarzenie', 'Wydarzenie'),
        ('termin', 'Termin'),
        ('inne', 'Inne'),
    ]
    haslo = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True)
    kategoria = models.CharField(max_length=20, choices=KATEGORIA_CHOICES, default='termin')
    skrot = models.CharField(max_length=300, blank=True, help_text='Krótka definicja (na liście)')
    tresc = models.TextField()
    zrodla = models.TextField(blank=True, help_text='Źródła, jedno na linię')
    powiazana_osoba = models.ForeignKey(Osoba, on_delete=models.SET_NULL, null=True, blank=True, related_name='hasla_slownika')
    data_dodania = models.DateTimeField(auto_now_add=True)
    data_modyfikacji = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hasło słownika'
        verbose_name_plural = 'Słownik historii'
        ordering = ['haslo']

    def __str__(self):
        return self.haslo


# ===== Batch 92 =====


class EtykietaOsoby(models.Model):
    """Kategorie zasług/zawodów osoby (Powstaniec, Żołnierz AK, Nauczyciel, Lekarz, Duchowny…)."""
    nazwa = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    opis = models.CharField(max_length=300, blank=True)
    ikona = models.CharField(max_length=8, blank=True, help_text='Krótki znak/emoji do listy')
    kolor = models.CharField(max_length=20, blank=True, help_text='Klasa Tailwind kolor (np. bg-amber-100 text-amber-800)')
    osoby = models.ManyToManyField(Osoba, blank=True, related_name='etykiety')

    class Meta:
        verbose_name = 'Etykieta osoby'
        verbose_name_plural = 'Etykiety osób'
        ordering = ['nazwa']

    def __str__(self):
        return self.nazwa


class WydarzenieParafialne(models.Model):
    """Wydarzenia w kościele/na cmentarzu (msze, procesje, modlitwy za zmarłych)."""
    TYP_CHOICES = [
        ('msza', 'Msza święta'),
        ('procesja', 'Procesja'),
        ('modlitwa', 'Modlitwa za zmarłych'),
        ('porzadkowanie', 'Porządkowanie cmentarza'),
        ('inne', 'Inne'),
    ]
    tytul = models.CharField(max_length=200)
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, default='msza')
    data_start = models.DateTimeField(db_index=True)
    data_koniec = models.DateTimeField(null=True, blank=True)
    miejsce = models.CharField(max_length=200, blank=True, help_text='Np. Kościół św. Władysława, brama cmentarza')
    opis = models.TextField(blank=True)
    intencja = models.CharField(max_length=300, blank=True, help_text='Intencja mszy / modlitwy (opcjonalnie)')
    opublikowane = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Wydarzenie parafialne'
        verbose_name_plural = 'Wydarzenia parafialne'
        ordering = ['data_start']

    def __str__(self):
        return f'{self.data_start:%Y-%m-%d %H:%M} — {self.tytul}'


# ===== Batch 93 =====


class Sonda(models.Model):
    """Tygodniowa sonda społecznościowa (np. Czy odnowić sektor A?)."""
    pytanie = models.CharField(max_length=300)
    opis = models.TextField(blank=True)
    aktywna = models.BooleanField(default=True, db_index=True)
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    data_zakonczenia = models.DateField(null=True, blank=True, help_text='Po tej dacie sonda zamyka się automatycznie')

    class Meta:
        verbose_name = 'Sonda'
        verbose_name_plural = 'Sondy'
        ordering = ['-data_utworzenia']

    def __str__(self):
        return self.pytanie


class OdpowiedzSondy(models.Model):
    sonda = models.ForeignKey(Sonda, on_delete=models.CASCADE, related_name='odpowiedzi')
    tresc = models.CharField(max_length=200)
    kolejnosc = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Odpowiedź sondy'
        verbose_name_plural = 'Odpowiedzi sondy'
        ordering = ['kolejnosc', 'pk']

    def __str__(self):
        return self.tresc


class GlosSondy(models.Model):
    odpowiedz = models.ForeignKey(OdpowiedzSondy, on_delete=models.CASCADE, related_name='glosy')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    ip_hash = models.CharField(max_length=64)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Głos w sondzie'
        verbose_name_plural = 'Głosy w sondach'
        constraints = [
            models.UniqueConstraint(fields=['odpowiedz', 'ip_hash'], name='glos_sondy_odp_ip_uniq'),
        ]


class Kondolencja(models.Model):
    """Wirtualne kondolencje pod profilem osoby (z moderacją)."""
    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='kondolencje')
    autor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    autor_imie = models.CharField(max_length=100, blank=True)
    tresc = models.TextField()
    zaakceptowana = models.BooleanField(default=False, db_index=True)
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kondolencja'
        verbose_name_plural = 'Kondolencje'
        ordering = ['-data_dodania']

    def __str__(self):
        return f'Kondolencja dla {self.osoba} ({self.data_dodania:%Y-%m-%d})'

    @property
    def autor_str(self):
        if self.autor_user:
            return self.autor_user.get_full_name() or self.autor_user.username
        return self.autor_imie or 'Anonim'


class ZbiorkaRenowacja(models.Model):
    """Zbiórka na renowację konkretnego grobu (publiczna, z postępem)."""
    STATUS_CHOICES = [
        ('oczekuje', 'Oczekuje na akceptację'),
        ('aktywna', 'Aktywna'),
        ('zakonczona', 'Zakończona'),
        ('odrzucona', 'Odrzucona'),
    ]
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE, related_name='zbiorki')
    inicjator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    tytul = models.CharField(max_length=200)
    opis = models.TextField()
    cel_pln = models.PositiveIntegerField(help_text='Kwota docelowa w PLN')
    zebrano_pln = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='oczekuje', db_index=True)
    konto_bankowe = models.CharField(max_length=80, blank=True, help_text='Numer konta na wpłaty')
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    data_zmiany = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Zbiórka renowacyjna'
        verbose_name_plural = 'Zbiórki renowacyjne'
        ordering = ['-data_utworzenia']

    def __str__(self):
        return f'{self.tytul} ({self.zebrano_pln}/{self.cel_pln} zł)'

    @property
    def procent(self):
        if not self.cel_pln:
            return 0
        return min(100, int(self.zebrano_pln * 100 / self.cel_pln))


class NotkaCmentarna(models.Model):
    """Mini-blog 'Z życia cmentarza' — krótkie posty staffu (max 500 zn.) na home."""
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    tresc = models.CharField(max_length=500)
    przypiety = models.BooleanField(default=False, help_text='Wyświetlaj na górze')
    opublikowana = models.BooleanField(default=True, db_index=True)
    data_dodania = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Notka cmentarna'
        verbose_name_plural = 'Notki cmentarne'
        ordering = ['-przypiety', '-data_dodania']

    def __str__(self):
        return f'{self.data_dodania:%Y-%m-%d}: {self.tresc[:60]}'


# ===== Batch 94 =====


class WpisLapidarium(models.Model):
    """Kuratorska wystawa najpiękniejszych nagrobków cmentarza."""
    KAT_CHOICES = [
        ('zabytek', 'Nagrobek zabytkowy'),
        ('artyzm', 'Walory artystyczne'),
        ('historia', 'Znaczenie historyczne'),
        ('symbolika', 'Symbolika'),
        ('inne', 'Inne'),
    ]
    grob = models.ForeignKey(Grob, on_delete=models.CASCADE, related_name='wpisy_lapidarium')
    tytul = models.CharField(max_length=200)
    kategoria = models.CharField(max_length=20, choices=KAT_CHOICES, default='zabytek')
    opis_kuratorski = models.TextField(help_text='Co warto zauważyć w tym nagrobku')
    foto = models.ImageField(upload_to='lapidarium/', blank=True, null=True)
    rok_powstania = models.PositiveSmallIntegerField(null=True, blank=True)
    autor_nagrobka = models.CharField(max_length=200, blank=True, help_text='Kamieniarz / artysta, jeśli znany')
    kolejnosc = models.PositiveSmallIntegerField(default=0, help_text='Kolejność na liście (mniejsza = wyżej)')
    opublikowany = models.BooleanField(default=True, db_index=True)
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Wpis lapidarium'
        verbose_name_plural = 'Lapidarium'
        ordering = ['kolejnosc', '-data_dodania']

    def __str__(self):
        return self.tytul


class ModlitwaDziennie(models.Model):
    """Counter dziennych modlitw za osobę (1 modlitwa per IP per osoba per dzień)."""
    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name='modlitwy')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ip_hash = models.CharField(max_length=64)
    data = models.DateField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Modlitwa za zmarłego'
        verbose_name_plural = 'Modlitwy za zmarłych'
        constraints = [
            models.UniqueConstraint(fields=['osoba', 'ip_hash', 'data'], name='modlitwa_uniq'),
        ]
        indexes = [models.Index(fields=['osoba', 'data'])]
