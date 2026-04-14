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

    sektor = models.ForeignKey(Sektor, on_delete=models.PROTECT, related_name='groby', verbose_name='Sektor')
    numer = models.CharField(max_length=20, verbose_name='Numer grobu')
    rzad = models.CharField(max_length=20, blank=True, verbose_name='Rząd')
    typ = models.CharField(max_length=20, choices=TYP_CHOICES, default='ziemny', verbose_name='Typ grobu')
    szerokosc_geo = models.FloatField(null=True, blank=True, verbose_name='Szerokość geograficzna')
    dlugosc_geo = models.FloatField(null=True, blank=True, verbose_name='Długość geograficzna')
    zdjecie = models.ImageField(upload_to='groby/', blank=True, null=True, verbose_name='Zdjęcie')
    uwagi = models.TextField(blank=True, verbose_name='Uwagi')
    data_dodania = models.DateTimeField(auto_now_add=True)
    data_modyfikacji = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Grób'
        verbose_name_plural = 'Groby'
        unique_together = [['sektor', 'numer']]
        ordering = ['sektor__nazwa', 'numer']

    def __str__(self):
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
