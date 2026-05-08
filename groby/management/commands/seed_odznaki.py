"""Tworzy podstawowe odznaki w bazie."""
from django.core.management.base import BaseCommand
from groby.models import Odznaka

ODZNAKI = [
    ('strazn', 'Strażnik pamięci', 'Zapaliłeś co najmniej 10 świeczek.', '🕯'),
    ('kron', 'Kronikarz', 'Dodałeś co najmniej 5 zaakceptowanych wspomnień.', '📜'),
    ('genea', 'Genealog', 'Pomogłeś uzupełnić co najmniej 3 relacje rodzinne.', '🌳'),
    ('prze', 'Przewodnik', 'Stworzyłeś trasę zwiedzania.', '🗺'),
    ('hist', 'Historyk', 'Napisałeś biogram lub wpis historyczny.', '📚'),
]


class Command(BaseCommand):
    help = 'Tworzy podstawowe odznaki.'

    def handle(self, *args, **opt):
        utworzonych = 0
        for kod, nazwa, opis, ikona in ODZNAKI:
            o, created = Odznaka.objects.get_or_create(
                kod=kod, defaults={'nazwa': nazwa, 'opis': opis, 'ikona': ikona},
            )
            if created:
                utworzonych += 1
        self.stdout.write(self.style.SUCCESS(f'Utworzono {utworzonych} odznak (już było: {len(ODZNAKI) - utworzonych}).'))
