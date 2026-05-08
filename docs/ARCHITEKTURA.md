# Architektura aplikacji „groby"

## Stack technologiczny

- **Python 3.10+ / Django 5.2** — framework webowy.
- **SQLite** — baza danych z rozszerzeniem **FTS5** (wyszukiwanie pełnotekstowe).
- **Tailwind CSS (CDN)** + **Inter / Cormorant Garamond** — design system, dark mode.
- **Leaflet 1.9** — mapa cmentarza w trybie `CRS.Simple` na bazie skanu.
- **Chart.js 4** — wykresy na statystykach.
- **Pillow + reportlab + qrcode + openpyxl** — przetwarzanie obrazów, generowanie PDF, QR, XLSX.
- **Django REST Framework + django-filter** — API JSON `/api/v1/`.
- **PWA** — `manifest.webmanifest` + service worker (`sw.js`).
- **Gunicorn + nginx** — produkcja.

## Diagram zależności modeli

```
Sektor 1 ─── n Grob 1 ─── n Osoba ─── n Wspomnienie
              │                │ ─── n Swieca
              │                │ ─── n Relacja (osoba_a/osoba_b)
              │                └ FK Wpis (postacie/wydarzenia)
              ├── n Zdjecie
              └── n Zgloszenie

User 1 ─── 1 Profil ─── n Grob (obserwowane)
            │           n Osoba (obserwowane)
            └── n ZapisaneSzukanie

HistoriaZmian — audit log Grob/Osoba (sygnały Django)
```

## Najważniejsze przepływy

### Wyszukiwanie
1. `views.szukaj()` parsuje GET-y (`q`, `sektor`, `typ`, `rok_od`, `rok_do`).
2. Jeśli jest `q`, wywołuje `_szukaj_fts()` — używa SQLite FTS5 z prefiksami (`Kowal*`).
3. Fallback do `icontains` gdy FTS niedostępny.
4. Przy zerowych trafieniach → `_zaproponuj_nazwisko()` (difflib) podsuwa najbliższy wynik.
5. Wyniki paginowane po 20 (`Paginator`).

### Mapa
1. `views.mapa()` filtruje groby z `plan_x/plan_y`, opcjonalnie po sektor/typ/data.
2. JSON markerów + URL planu są przekazywane do template.
3. Leaflet w `CRS.Simple` rozkłada markery; staff może klikać aby przepisywać pozycje przez `zapisz_pozycje`.

### Audit log
1. `groby.middleware.BiezacyUzytkownikMiddleware` zapisuje `request.user` w thread-local.
2. Sygnały `pre_save`/`post_save`/`post_delete` w `groby/signals.py` porównują pola przed i po, tworzą `HistoriaZmian` z autorem.

### Powiadomienia
1. `signals._powiadom_*` reagują na zapis `Zdjecie`, `Wspomnienie`, `Zgloszenie`.
2. Wysyłają e-mail przez `send_mail()` (`EMAIL_BACKEND` w `.env`, dev: console).

## Layout repozytorium

```
config/                 — settings, urls, wsgi
groby/
    api.py              — REST API (DRF serializers + viewsets)
    admin.py            — panel administracyjny Django
    apps.py             — rejestracja sygnałów
    middleware.py       — bieżący użytkownik dla audit logu
    models.py           — wszystkie modele
    signals.py          — audit + powiadomienia
    urls.py             — wszystkie URL-e aplikacji
    views.py            — widoki HTML (REST jest osobno w api.py)
    management/commands/
        import_excel.py     — import bazy z arkusza
        rozmiesc_groby.py   — auto-układ markerów na planie
        import_gedcom.py    — import drzewa genealogicznego
        waliduj.py          — kontrola spójności danych
    migrations/         — migracje schematu (0007 plików)
    templatetags/       — własne filtry/tagi
    tests.py            — testy (59)
templates/
    base.html           — layout, ciemny motyw, PWA, hamburger
    groby/*.html        — widoki
deploy.sh               — provisioning + update VPS (Ubuntu 22.04)
Dockerfile, docker-compose.yml — środowisko kontenerowe
.github/workflows/      — CI
docs/                   — dokumentacja
```

## Bezpieczeństwo

- CSRF dla wszystkich formularzy (Django default).
- Honeypot + rate-limit na formularzach publicznych (`_antybot()` w views).
- Świeczki: cooldown 10 minut po hashu IP (sha256, częściowo zanonimizowany).
- Wspomnienia i zgłoszenia idą do moderacji (`status='oczekuje'`/`'nowe'`).
- API: pisanie wymaga zalogowania (sesja lub Basic Auth), odczyt publiczny.
- `DEBUG=False` na produkcji (`.env`), `ALLOWED_HOSTS` ograniczone do IP.
- `staticfiles/` i `media/` serwowane przez nginx (nie przez gunicorn).

## Skalowanie

Aplikacja celowo używa SQLite + plik FTS5 — wystarcza na rozmiar parafii (~700 grobów, ~1300 osób).
W razie potrzeby przejścia na PostgreSQL: zmiana `DATABASES` w `settings.py`, zastąpienie FTS5 odpowiednikiem `SearchVector`/`pg_trgm`. Modele i URL-e nie wymagają zmian.
