# Informator Cmentarny — Szydłów

Aplikacja webowa do przeszukiwania i wizualizacji bazy grobów cmentarza parafialnego w Szydłowie. Praca inżynierska, Django 5.2 / SQLite + FTS5.

> **Demo:** http://212.132.124.0/
>
> **GitHub:** https://github.com/Mateuszl28/praca_inz

## Co potrafi

### Dla zwiedzających
- **Wyszukiwarka osób** z FTS5 (prefiksy, polskie znaki bez ogonków), sugestie literówek („czy chodziło o…?")
- **Mapa cmentarza** na bazie skanu, markery dla wszystkich grobów, **clustering**, filtry sektor/typ/rok
- **Geolokalizacja „jesteś tu"** — przybliżona pozycja użytkownika na planie z GPS
- **Skaner QR w aparacie** (`/skaner/`) — zeskanuj kod przy nagrobku, otwórz stronę grobu
- **Sektory**, **galeria całego cmentarza**, **indeks nazwisk**, **oś czasu** życiorysów
- **Kronika cmentarza** — co ostatnio się zmieniło, nowe zdjęcia i wspomnienia
- **Polecane trasy zwiedzania** — tematyczne ścieżki z mapą i kolejnością punktów
- **Kalendarz rocznic** śmierci + eksport iCal (.ics)
- **Spacer 360°** — panoramy z hotspotami do grobów (Pannellum)
- **Świeczki online** — zapal znicz, świeci 24h, intencja, animowany płomień
- **Wspomnienia + komentarze** zatwierdzane przez moderatora
- **Drzewo genealogiczne** w SVG: rodzice, małżonkowie, rodzeństwo, dzieci
- **Wspólni przodkowie** — porównaj 2 osoby, znajdź wspólnego przodka (BFS w grafie relacji)
- **Karta grobu PDF** — pełen dokument z fotami, osobami, QR i lokalizacją
- **QR kody** dla każdego grobu (PNG + naklejki A4)
- **Statystyki** z heatmapą zgonów (miesiące × dekady)
- **Postacie i wydarzenia** — blog parafialny + RSS
- **Newsletter** — miesięczne podsumowanie najbliższych rocznic i wpisów
- **Banner Wszystkich Świętych** — automatycznie 25.10–04.11
- **PWA** — instalowalne na telefonie, działa offline po pierwszym wejściu
- **i18n** — PL / EN / UA z przełącznikiem
- **Dostępność** — tryb wysokiego kontrastu, powiększanie czcionki (A+), skip-link, ARIA

### Dla zarejestrowanych
- Rejestracja + **logowanie hasłem lub magic linkiem** (link na e-mail, 30 min)
- **Obserwowanie** grobów i osób — powiadomienia e-mail przy zmianach
- **Web Push** — powiadomienia w przeglądarce (Service Worker + VAPID)
- **Zapisane wyszukiwania** w profilu
- **2FA TOTP** (Google Authenticator / Authy / 1Password) — QR + weryfikacja kodu
- **System odznak** — 5 osiągnięć (Strażnik pamięci, Kronikarz, Genealog, Przewodnik, Historyk)

### Dla administracji
- **Dashboard** z metrykami (oczekujące zgłoszenia, niezatwierdzone wspomnienia, niekompletne dane, świeczki 24h)
- **Audit log** — kto co kiedy zmienił (sygnały Django + thread-local middleware)
- **Detektor duplikatów** osób, **walidator danych** (`manage.py waliduj`)
- **Bulk import zdjęć ZIP** z konwencją nazw `SEKTOR_NUMER.jpg`
- **Bulk operacje** w admin (zmień typ wielu grobów, wyczyść pozycje)
- **Druk naklejek QR** dla całych sektorów (A4, 4 kolumny)
- **Eksport PDF / CSV / XLSX** wyników szukajki, **GEDCOM** całego drzewa
- **Backup do ZIP** — `manage.py backup` (dump.json + media)
- **Newsletter** — `manage.py wyslij_newsletter` z dry-run
- **Panoramy 360°** + hotspoty do grobów (admin z inline edytorem)

### Integracje
- **REST API** — `/api/v1/sektory/`, `/groby/`, `/osoby/` z filtrami, search, ordering, paginacją (DRF + django-filter)
- **GraphQL** — `/graphql/` z GraphiQL UI (graphene-django)
- **Embedded widget** — `/widget/?q=` do osadzenia w iframe parafii
- **iCal feed** — `/kalendarz.ics` rocznice do Google Calendar / Outlook
- **RSS** — `/postacie/feed/`
- **Sitemap.xml + robots.txt** — automatycznie generowane
- **Open Graph + Twitter Cards** — kafelki przy udostępnianiu
- **Schema.org JSON-LD** — `Person`, `Cemetery` na stronach osób
- **Health check** — `/health/` JSON ze stanem DB, dyskiem, licznikami
- **Sentry** — opcjonalnie przez `SENTRY_DSN`
- **API tokens + throttling** — DRF `TokenAuth` + rate limit (anon: 60/h, user: 1000/h)

## Szybki start (lokalnie)

```bash
git clone https://github.com/Mateuszl28/praca_inz.git
cd praca_inz
python -m venv venv

# Linux/macOS
source venv/bin/activate
pip install -r requirements.txt

# Windows (PowerShell)
venv\Scripts\Activate.ps1
venv\Scripts\pip install -r requirements.txt

python manage.py migrate
python manage.py loaddata data/dump.json
python manage.py seed_odznaki
python manage.py createsuperuser
python manage.py runserver
```

Otwórz http://127.0.0.1:8000/.

## Docker

```bash
docker compose up --build
```

Aplikacja: http://localhost:8000/.

## Deploy na VPS (Ubuntu 22.04+)

Jednolinijkowy provisioning na świeżym serwerze (gunicorn + nginx + systemd):

```bash
ssh root@TWOJ-IP
wget -qO /tmp/d.sh https://raw.githubusercontent.com/Mateuszl28/praca_inz/main/deploy.sh
bash /tmp/d.sh
```

Aktualizacja po push do GitHuba:

```bash
bash /opt/praca_inz/deploy.sh
```

Skrypt automatycznie:
- instaluje pakiety (`python3`, `git`, `nginx`, `python3-venv`)
- klonuje/aktualizuje repo
- tworzy venv i instaluje `requirements.txt`
- generuje `.env` (losowy `SECRET_KEY`)
- uruchamia migracje, ładuje fixturę przy pierwszym deploy
- konfiguruje gunicorn (systemd unit) + nginx
- tworzy/aktualizuje konto `admin` (hasło `admin123` — **zmień natychmiast**)

Szczegóły: [`docs/DEPLOY.md`](docs/DEPLOY.md).

## Stack technologiczny

| Warstwa            | Technologia                                                          |
|--------------------|----------------------------------------------------------------------|
| Backend            | Python 3.10+, Django 5.2, SQLite + FTS5                              |
| API                | Django REST Framework, django-filter, graphene-django                |
| Frontend           | Tailwind CSS (CDN), Inter + Cormorant Garamond, vanilla JS           |
| Mapa               | Leaflet 1.9 (CRS.Simple) + Leaflet.markercluster                     |
| Wykresy            | Chart.js 4 + canvas timeline                                         |
| 360°               | Pannellum 2.5                                                        |
| QR                 | qrcode (gen), jsQR (scan w przeglądarce)                             |
| PDF / XLSX         | reportlab, openpyxl                                                  |
| 2FA / Push         | django-otp (TOTP), pywebpush (VAPID)                                 |
| Produkcja          | gunicorn, nginx, systemd                                             |
| CI                 | GitHub Actions (matrix Python 3.10 + 3.12)                           |
| Monitoring         | Sentry (opcjonalnie)                                                 |

## Modele danych

```
Sektor 1───n Grob 1───n Osoba ───n Wspomnienie ───n Komentarz
              │            │ ───n Swieca / Tag (M2M) / Relacja
              │            │ ───n Wpisy (postacie)
              ├── n Zdjecie
              └── n Zgloszenie

Sektor ───n Panorama ───n HotspotPanoramy

Trasa ───n TrasaPunkt ───── Grob

User 1───1 Profil ───n Grob/Osoba (obserwowane)
       ├── n ZapisaneSzukanie
       ├── n SubskrypcjaPush, TokenLogowania (magic-link)
       └── n UzytkownikOdznaka ─── Odznaka

Newsletter (subskrybenci e-mail z tokenem anulowania)
HistoriaZmian — audit log (sygnały dla Grob/Osoba)
```

Pełny opis architektury: [`docs/ARCHITEKTURA.md`](docs/ARCHITEKTURA.md).

## API

- `/api/v1/` — DRF browsable HTML + JSON. Filtry, search, ordering, paginacja 50.
- `/graphql/` — GraphiQL UI z interaktywnym schemat.
- `/api/auth/login/` — login dla DRF browsable.

Dokumentacja: [`docs/API.md`](docs/API.md).

## Komendy zarządzania

```bash
# Import / eksport danych
python manage.py import_excel <plik.xlsx>
python manage.py import_gedcom <plik.ged>

# Pomocnicze
python manage.py rozmiesc_groby                # auto-układ markerów na planie
python manage.py waliduj                       # spójność danych (--json dla CI)
python manage.py seed_odznaki                  # utwórz 5 odznak gamifikacji
python manage.py wyslij_newsletter --dry-run   # podgląd, kogo by wysłać
python manage.py backup --output /var/backups  # ZIP z dump.json + media
```

## Testy

```bash
python manage.py test groby
```

**59 testów** pokrywa: modele, widoki, API, formularze, parsing dat, walidator, GEDCOM, FTS, anti-spam, świeczki, wspomnienia, PWA, walidator, dashboard staffu, eksport.

```bash
python manage.py test groby --verbosity=2
```

CI uruchamia testy na Python 3.10 i 3.12 przy każdym pushu.

## Struktura repozytorium

```
config/                 — settings, urls, wsgi
groby/
    api.py              — REST API (DRF serializers + viewsets)
    schema.py           — GraphQL schema (graphene-django)
    feeds.py            — RSS feed dla Wpis
    sitemaps.py         — sitemap.xml dla SEO
    admin.py            — panel administracyjny Django
    apps.py             — rejestracja sygnałów
    middleware.py       — bieżący użytkownik (audit log)
    context_processors.py — banner Wszystkich Świętych
    models.py           — wszystkie modele (~25)
    signals.py          — audit + powiadomienia + odznaki
    urls.py             — URL-e aplikacji
    views.py            — widoki HTML (REST/GraphQL osobno)
    management/commands/
        backup.py
        import_excel.py
        import_gedcom.py
        rozmiesc_groby.py
        seed_odznaki.py
        waliduj.py
        wyslij_newsletter.py
    migrations/         — migracje schematu
    templatetags/       — własne filtry/tagi (polish, antybot)
    tests.py            — 59 testów
templates/
    base.html           — layout z dropdownami, dark/kontrast/font-size
    404.html, 500.html, 403.html — strony błędów
    robots.txt
    groby/*.html        — wszystkie widoki
deploy.sh               — provisioning + update VPS
Dockerfile, docker-compose.yml
.github/workflows/      — CI
docs/                   — ARCHITEKTURA, DEPLOY, API
data/                   — fixtura JSON
```

## Bezpieczeństwo

- CSRF dla wszystkich formularzy (Django default).
- **Honeypot + min-time-to-submit** na formularzach publicznych (`_antybot()` w views).
- Świeczki: cooldown 10 minut po hashu IP (sha256, częściowo zanonimizowany).
- Wspomnienia, zgłoszenia, komentarze idą do moderacji.
- API: pisanie wymaga zalogowania (sesja, Basic Auth, Token), odczyt publiczny.
- **HSTS 1 rok**, X-Frame-Options, XSS filter, content-type nosniff (gdy `DEBUG=False`).
- 2FA TOTP dostępne dla wszystkich kont.
- `staticfiles/` i `media/` serwowane przez nginx.
- Migracja na PostgreSQL możliwa przez podmianę `DATABASES` (modele/URL nie wymagają zmian).

## Skalowanie i wydajność

- **Cache** stron publicznych (home/sektory/indeks) z `cache_page`.
- **Image thumbnails** generowane na żądanie (180/600/1200 px) i cache'owane na dysku.
- **DRF throttle** ogranicza spam (anon: 60/h, user: 1000/h).
- **FTS5** zamiast `LIKE` w wyszukiwarce.
- **PWA service worker** cache statycznych zasobów po pierwszym wejściu.

## Licencja

Praca inżynierska — Mateusz Łagocki, 2026.

Kod open-source na licencji MIT (komponenty third-party — wg ich własnych licencji).

## Podziękowania

Parafia pw. św. Władysława w Szydłowie — udostępnienie księgi grobów i pomoc w weryfikacji danych.
