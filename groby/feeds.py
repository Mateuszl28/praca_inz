from django.contrib.syndication.views import Feed
from django.urls import reverse

from .models import Wpis


class WpisyFeed(Feed):
    title = 'Postacie i wydarzenia — Cmentarz Szydłów'
    link = '/postacie/'
    description = 'Sylwetki znanych Szydłowian i wydarzenia parafialne.'

    def items(self):
        return Wpis.objects.filter(opublikowany=True).order_by('-data_publikacji', '-data_dodania')[:20]

    def item_title(self, item):
        return item.tytul

    def item_description(self, item):
        return item.podpis or item.tresc[:280]

    def item_link(self, item):
        return reverse('groby:wpis_detail', args=[item.slug])

    def item_pubdate(self, item):
        from datetime import datetime, time
        if item.data_publikacji:
            return datetime.combine(item.data_publikacji, time.min)
        return item.data_dodania
