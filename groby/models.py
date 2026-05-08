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
