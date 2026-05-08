from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Sektor, Osoba, Wpis


class StronyStaticzneSitemap(Sitemap):
    priority = 0.7
    changefreq = 'monthly'

    def items(self):
        return ['home', 'sektory_list', 'mapa', 'kalendarz', 'indeks',
                'wpisy_lista', 'galeria_cmentarza', 'statystyki', 'o_cmentarzu']

    def location(self, item):
        return reverse(f'groby:{item}')


class SektorSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'

    def items(self):
        return Sektor.objects.all()

    def location(self, obj):
        return reverse('groby:sektor_detail', args=[obj.pk])


class OsobaSitemap(Sitemap):
    priority = 0.5
    changefreq = 'yearly'
    limit = 5000

    def items(self):
        return Osoba.objects.select_related('grob').all()

    def location(self, obj):
        return reverse('groby:osoba_detail', args=[obj.pk])


class WpisSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return Wpis.objects.filter(opublikowany=True)

    def lastmod(self, obj):
        return obj.data_modyfikacji

    def location(self, obj):
        return reverse('groby:wpis_detail', args=[obj.slug])


sitemaps = {
    'static': StronyStaticzneSitemap,
    'sektory': SektorSitemap,
    'osoby': OsobaSitemap,
    'wpisy': WpisSitemap,
}
