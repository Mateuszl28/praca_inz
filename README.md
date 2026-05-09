# Informator Cmentarny — Szydłów

Aplikacja webowa do przeszukiwania i wizualizacji bazy grobów cmentarza parafialnego w Szydłowie. Praca inżynierska, Django 5.2 / SQLite + FTS5.

> **Demo:** http://212.132.124.0/
>
> **GitHub:** https://github.com/Mateuszl28/praca_inz

## Co potrafi

### Wyszukiwanie i nawigacja
- **Wyszukiwarka osób** z FTS5 (prefiksy, polskie znaki bez ogonków), sugestie literówek („czy chodziło o…?")
- **Voice search** — 🎤 wyszukiwanie głosowe przez Web Speech API (PL)
- **Mapa cmentarza** na bazie skanu — markery, **clustering**, **heatmap pochówków**, filtry sektor/typ/rok
- **Geolokalizacja „jesteś tu"** — przybliżona pozycja użytkownika na planie z GPS
- **Skaner QR w aparacie** (`/skaner/`) — zeskanuj kod przy nagrobku, otwórz stronę grobu
- **Sektory**, **galeria całego cmentarza**, **indeks nazwisk**, **chmura nazwisk**
- **Oś czasu** życiorysów (`/timeline/`), **„Kto żył w roku X"** z sliderem 1700–2026
- **Family tree całego cmentarza** — interaktywny D3 z drag/zoom
- **Mapa pochodzenia** — geo-mapa miejsc urodzenia z geocoderem Nominatim
- **Kronika** — co ostatnio się zmieniło, **Memory wall** — wszystkie wspomnienia
- **Polecane trasy zwiedzania** z mapą, kolejnością i audio przewodnikiem
- **Kalendarz rocznic** + eksport iCal (.ics)
- **Top 10 rankingi** — najmłodsi/najstarsi/najczęstsze nazwiska
- **Plebiscyt nagrobków** — głosowanie na najpiękniejsze, ranking miesiąca
- **Quiz historyczny** „Czy znasz cmentarz?" — 10 losowych pytań, gamifikacja

### Pamięć i zaangażowanie
- **Świeczki online** — zapal znicz, świeci 24h, intencja, animowany płomień
- **Wirtualne kwiaty** — róża/lilia/chryzantema/tulipan, 7 dni, opcjonalna wiadomość
- **Wspomnienia + komentarze** zatwierdzane przez moderatora
- **Listy do zmarłych** — wirtualne listy + publiczna ściana
- **Forum dyskusyjne** per grób — wątki z odpowiedziami dla zalogowanych
- **Speech-to-text** w formularzu wspomnień (dyktowanie głosem)
- **Nagrania audio/video** pożegnań, dodawane do grobu (po moderacji)
- **Drzewo genealogiczne** w SVG: rodzice, małżonkowie, rodzeństwo, dzieci
- **Wspólni przodkowie** — porównaj 2 osoby, znajdź wspólnego przodka
- **Karta grobu PDF** — pełen dokument do druku z fotami, osobami, QR
- **Kolaż wspomnień PDF** — wszystkie wspomnienia o jednej osobie w jednym dokumencie
- **QR kody** dla każdego grobu (PNG + naklejki A4)
- **Postacie i wydarzenia** — blog parafialny + RSS

### Dla zarejestrowanych użytkowników
- Rejestracja + **logowanie hasłem lub magic linkiem** (link na e-mail, 30 min)
- **Obserwowanie** grobów i osób — powiadomienia e-mail przy zmianach
- **Auto-przypomnienia** — 7 dni przed rocznicą śmierci obserwowanej osoby
- **Web Push** — powiadomienia w przeglądarce (Service Worker + VAPID)
- **2FA TOTP** (Google Authenticator / Authy / 1Password) — QR + weryfikacja
- **Zapisane wyszukiwania** w profilu
- **Newsletter** — miesięczne podsumowanie najbliższych rocznic i wpisów
- **Auto-przypomnienia urodzinowe** — e-mail w urodziny obserwowanej osoby
- **Onboarding wizard** — interaktywny tour po pierwszym logowaniu
- **Apple Wallet pass** — `/grob/<pk>/wallet.json` z QR i lokalizacją grobu
- **System odznak** — Strażnik pamięci, Kronikarz, Genealog, Przewodnik, Historyk
- **Statystyki użytkownika** — Twoja aktywność: świeczki, kwiaty, wspomnienia, głosy, odznaki
- **„Moja rodzina"** — wszyscy obserwowani + ich relacje rodzinne
- **Intencje mszalne** — zamów mszę za zmarłą osobę online
- **Zaproszenia do współedycji** — admin może zaprosić rodzinę do uzupełnienia danych

### Dostępność i UX
- **i18n** — PL / EN / UA z przełącznikiem
- **Tryb wysokiego kontrastu** — czarny/żółty dla osób słabowidzących
- **Powiększanie czcionki** — przycisk A+ (100%/110%/125%) z persistencją
- **Skip-link** + `aria-label` na ważnych elementach
- **PWA** — instalowalne na telefonie (banner instalacji), działa offline
- **Strony błędów** 404/500/403 stylowane
- **Empty states + spinner + skeleton** loadery
- **Print stylesheet** — uniwersalny dla wszystkich stron (URL-e drukowane jako `(...)` po linkach)
- **Sezonowe banery** — Wszystkich Świętych, Boże Narodzenie, Wielkanoc (auto-detekcja daty + algorytm Gaussa dla Wielkanocy)

### GDPR / compliance
- **Polityka prywatności** i **regulamin**
- **Cookies consent banner** (localStorage)
- **Eksport własnych danych** w ZIP (RODO art. 15)
- **Usunięcie konta** z kaskadowym usunięciem danych (RODO art. 17)
- **Honeypot + min-time-to-submit** na formularzach publicznych
- **Świeczki/kwiaty/głosy:** cooldown po hashu IP (zanonimizowany sha256)

### Dla administracji
- **Dashboard** z metrykami (oczekujące zgłoszenia, niezatwierdzone wspomnienia, świeczki 24h, kwiaty)
- **Audit log** — kto co kiedy zmienił (sygnały Django + thread-local middleware)
- **Detektor duplikatów** osób, **walidator danych** (`manage.py waliduj`)
- **Bulk import zdjęć ZIP** z konwencją nazw `SEKTOR_NUMER.jpg`
- **Bulk operacje** w admin (zmień typ, wyczyść pozycje, zaakceptuj wiele)
- **Inline edit** kluczowych pól w widoku publicznym (dla staffu)
- **Audit rollback** — staff może cofnąć zmiany pól z historii (`/staff/cofnij/<pk>/`)
- **Druk naklejek QR** dla całych sektorów (A4, 4 kolumny)
- **Eksport** wyników szukajki: PDF, CSV, XLSX
- **Eksport całego drzewa** w GEDCOM 5.5
- **Eksport galerii sektora** do ZIP
- **Backup do ZIP** (`manage.py backup --keep 4`) — dump.json + media z retention
- **Moderacja:** wspomnienia, komentarze, zgłoszenia, nagrania, intencje
- **Newsletter** — wysyłka komendą (`manage.py wyslij_newsletter`)
- **Panoramy 360°** + hotspoty do grobów (admin z inline edytorem)
- **Trasy zwiedzania** — komponowanie ścieżek tematycznych

### Integracje i API
- **REST API** — `/api/v1/sektory/`, `/groby/`, `/osoby/` z filtrami, search, ordering, paginacją (DRF + django-filter)
- **OpenAPI 3 + Swagger UI** — `/api/docs/` (interaktywny), `/api/redoc/` (czytelny), `/api/schema/` (YAML/JSON) — drf-spectacular
- **GraphQL** — `/graphql/` z GraphiQL UI (graphene-django)
- **Webhooki** — model `Webhook` z eventami (`zgloszenie.nowe`, `wspomnienie.zaakceptowane`, …) — POST do dowolnego URL przy zmianach
- **API Tokens + throttling** — DRF `TokenAuth` + rate limit (anon: 60/h, user: 1000/h)
- **Embedded widget** — `/widget/?q=` do osadzenia w iframe parafii
- **iCal feed** — `/kalendarz.ics` rocznice do Google Calendar / Outlook
- **RSS** — `/postacie/feed/`
- **Sitemap.xml + robots.txt** — automatycznie generowane
- **Open Graph + Twitter Cards** — kafelki przy udostępnianiu w mediach społecznościowych
- **Schema.org JSON-LD** — `Person`, `Cemetery` na stronach osób
- **Health check** — `/health/` JSON ze stanem DB, dyskiem, licznikami
- **Sentry** — opcjonalnie przez `SENTRY_DSN`

### Treść statyczna
- **Strona główna**, **O cmentarzu**, **Statystyki** z heatmapą zgonów (miesiące × dekady)
- **FAQ** — 7 najczęstszych pytań
- **Pomoc** — instrukcja krok po kroku
- **Dla mediów** (`/dla-mediow/`) — press kit dla dziennikarzy
- **Wesprzyj cmentarz** (`/wesprzyj/`) — strona donate z numerem konta i szkieletem płatności online

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
- konfiguruje gunicorn (systemd unit) + nginx (port 80)
- tworzy/aktualizuje konto `admin` (hasło `admin123` — **zmień natychmiast**)

Szczegóły: [`docs/DEPLOY.md`](docs/DEPLOY.md).

## Stack technologiczny

| Warstwa            | Technologia                                                          |
|--------------------|----------------------------------------------------------------------|
| Backend            | Python 3.10+, Django 5.2, SQLite + FTS5                              |
| API                | Django REST Framework, django-filter, drf-spectacular (OpenAPI 3), graphene-django |
| Frontend           | Tailwind CSS (CDN), Inter + Cormorant Garamond, vanilla JS           |
| Mapa               | Leaflet 1.9 (CRS.Simple) + markercluster + heat                      |
| Wizualizacje       | Chart.js 4 + canvas timeline + D3.js (drzewo)                        |
| 360°               | Pannellum 2.5                                                        |
| QR                 | qrcode (gen), jsQR (scan w przeglądarce)                             |
| PDF / XLSX         | reportlab, openpyxl                                                  |
| 2FA / Push         | django-otp (TOTP), pywebpush (VAPID)                                 |
| Speech / Voice     | Web Speech API (przeglądarka)                                        |
| Geokodowanie       | Nominatim (OpenStreetMap)                                            |
| Produkcja          | gunicorn, nginx, systemd                                             |
| CI                 | GitHub Actions (matrix Python 3.10 + 3.12)                           |
| Monitoring         | Sentry (opcjonalnie)                                                 |

## Modele danych (~30)

```
Sektor 1───n Grob 1───n Osoba ───n Wspomnienie ───n Komentarz
              │            │ ───n Swieca / Kwiat / Tag (M2M) / Relacja
              │            │ ───n Nagranie (audio/video)
              │            │ ───n IntencjaMszalna
              │            │ ───n Zaproszenie (do współedycji)
              │            │ ───n Wpisy (postacie/historia)
              ├── n Zdjecie / Nagranie
              ├── n GlosNagrobek (plebiscyt)
              └── n Zgloszenie

Sektor ───n Panorama ───n HotspotPanoramy

Trasa ───n TrasaPunkt ───── Grob (audio przewodnik na trasie)

User 1───1 Profil ───n Grob/Osoba (obserwowane)
       ├── n ZapisaneSzukanie
       ├── n SubskrypcjaPush, TokenLogowania (magic-link)
       └── n UzytkownikOdznaka ─── Odznaka

Wpis ───n ZdjecieWpisu (galeria treści blog)

Newsletter (subskrybenci e-mail z tokenem anulowania)
GeoCache (cache Nominatim: miejsce → lat/lng)
HistoriaZmian — audit log (sygnały dla Grob/Osoba)
```

Pełny opis architektury: [`docs/ARCHITEKTURA.md`](docs/ARCHITEKTURA.md).

## API

- `/api/v1/` — DRF browsable HTML + JSON. Filtry, search, ordering, paginacja 50.
- `/graphql/` — GraphiQL UI z interaktywnym schematem.
- `/api/auth/login/` — login dla DRF browsable.

Dokumentacja: [`docs/API.md`](docs/API.md).

## Komendy zarządzania

### Import / eksport danych

```bash
python manage.py import_excel <plik.xlsx>
python manage.py import_gedcom <plik.ged>
python manage.py backup --output /var/backups        # ZIP z dump.json + media
```

### Pomocnicze

```bash
python manage.py rozmiesc_groby                      # auto-układ markerów na planie
python manage.py waliduj                             # spójność danych (--json dla CI)
python manage.py seed_odznaki                        # utwórz 5 odznak gamifikacji
python manage.py geokoduj --limit 100                # geokodowanie miejsc urodzenia (Nominatim)
python manage.py optymalizuj_zdjecia --max 2000      # bulk resize zdjęć (oszczędność dysku)
```

### Wysyłka mailowa

```bash
python manage.py wyslij_newsletter --dry-run         # podgląd, kogo by wysłać
python manage.py wyslij_przypomnienia --dni 7        # 7 dni przed rocznicą obserwowanym
python manage.py wyslij_urodziny                     # przypomnienia urodzinowe
```

## Testy

```bash
python manage.py test groby
```

**59 testów** pokrywa: modele, widoki, API, formularze, parsing dat, walidator, GEDCOM, FTS, anti-spam, świeczki, wspomnienia, PWA, dashboard staffu, eksport.

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
    models.py           — wszystkie modele (~30)
    signals.py          — audit + powiadomienia + odznaki
    urls.py             — URL-e aplikacji
    views.py            — widoki HTML (REST/GraphQL osobno)
    management/commands/
        backup.py
        geokoduj.py
        import_excel.py
        import_gedcom.py
        optymalizuj_zdjecia.py
        rozmiesc_groby.py
        seed_odznaki.py
        waliduj.py
        wyslij_newsletter.py
        wyslij_przypomnienia.py
    migrations/         — migracje (~13)
    templatetags/       — własne filtry/tagi (polish, antybot)
    tests.py            — 59 testów
templates/
    base.html           — layout z dropdownami, dark/kontrast/font-size, banner WS
    404.html, 500.html, 403.html — strony błędów
    robots.txt
    groby/*.html        — wszystkie widoki (~35 szablonów)
deploy.sh               — provisioning + update VPS
Dockerfile, docker-compose.yml
.github/workflows/      — CI
docs/                   — ARCHITEKTURA, DEPLOY, API
data/                   — fixtura JSON
```

## Bezpieczeństwo

- CSRF dla wszystkich formularzy (Django default).
- **Honeypot + min-time-to-submit** na formularzach publicznych.
- **Cooldown** po hashu IP dla świeczek/kwiatów/głosów.
- Wspomnienia, zgłoszenia, komentarze, nagrania → moderacja.
- API: pisanie wymaga zalogowania (sesja, Basic Auth, Token), odczyt publiczny.
- **HSTS 1 rok**, X-Frame-Options, XSS filter, content-type nosniff (gdy `DEBUG=False`).
- 2FA TOTP dostępne dla wszystkich kont.
- `staticfiles/` i `media/` serwowane przez nginx.
- Migracja na PostgreSQL możliwa przez podmianę `DATABASES`.

## Skalowanie i wydajność

- **Indeksy DB** na `Osoba(nazwisko, imie)`, `Osoba(data_smierci)`, `Grob(plan_x, plan_y)`.
- **Cache** stron publicznych (home/sektory/indeks) z `cache_page`.
- **Image thumbnails** generowane na żądanie i cache'owane na dysku.
- **DRF throttle** ogranicza spam (anon: 60/h, user: 1000/h).
- **FTS5** zamiast `LIKE` w wyszukiwarce.
- **PWA service worker** cache statycznych zasobów po pierwszym wejściu.
- **Auto-optymalizacja zdjęć** (`optymalizuj_zdjecia`) — bulk resize do max 2000px.
- **PostgreSQL** — opcjonalnie przez `DATABASE_URL` env (np. `postgres://user:pass@host/db`).
- **Redis cache** — opcjonalnie przez `DJANGO_REDIS_URL` env zamiast LocMemCache.

## Licencja

Praca inżynierska — Mateusz Łagocki, 2026.

Kod open-source na licencji MIT (komponenty third-party — wg ich własnych licencji).

## Podziękowania

Parafia pw. św. Władysława w Szydłowie — udostępnienie księgi grobów i pomoc w weryfikacji danych.
