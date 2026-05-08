# Informator Cmentarny — Szydłów

Aplikacja webowa do przeszukiwania i wizualizacji bazy grobów cmentarza parafialnego w Szydłowie. Praca inżynierska, Django 5.2 / SQLite + FTS5.

> **Demo:** http://212.132.124.0/

## Co potrafi

### Dla zwiedzających
- **Wyszukiwarka osób** z FTS5 (prefiksy, polskie znaki bez ogonków), sugestie literówek („czy chodziło o…?")
- **Mapa cmentarza** na bazie skanu, markery dla wszystkich grobów, filtry sektor/typ/rok, wyszukiwarka „znajdź grób"
- **Sektory**, **galeria całego cmentarza**, **indeks nazwisk**, **oś czasu** życiorysów
- **Kalendarz rocznic** śmierci + eksport iCal (.ics)
- **Spacer 360°** — panoramy z hotspotami do grobów (Pannellum)
- **Świeczki online** — zapal znicz, świeci 24h, intencja, animowany płomień
- **Wspomnienia** zatwierdzane przez moderatora
- **Drzewo genealogiczne** w SVG: rodzice, małżonkowie, rodzeństwo, dzieci
- **QR kody** dla każdego grobu
- **Statystyki** z heatmapą zgonów (miesiące × dekady)
- **Postacie i wydarzenia** — blog parafialny
- **PWA** — można zainstalować na telefonie, działa offline po pierwszym wejściu
- **i18n** — PL / EN / UA z przełącznikiem w nagłówku

### Dla zarejestrowanych
- Rejestracja, **logowanie hasłem lub magic linkiem** (link na e-mail)
- **Obserwowanie** grobów i osób — powiadomienia e-mail przy zmianach
- **Web Push** — powiadomienia w przeglądarce (jeśli włączone)
- **Zapisane wyszukiwania** w profilu
- **2FA TOTP** (Google Authenticator / Authy / 1Password)

### Dla administracji
- **Dashboard** z metrykami (oczekujące zgłoszenia, wspomnienia, niekompletne dane, świeczki 24h)
- **Audit log** — kto co kiedy zmienił (sygnały Django)
- **Detektor duplikatów** osób
- **Walidator danych** (`manage.py waliduj`) — wykrywa daty z przyszłości, śmierć przed urodzeniem, nierealny wiek
- **Bulk import zdjęć ZIP** z konwencją nazw `SEKTOR_NUMER.jpg`
- **Druk naklejek QR** dla całych sektorów (A4, 4 kolumny)
- **Eksport PDF / CSV / XLSX** wyników szukajki, **GEDCOM** całego drzewa
- **Import GEDCOM** — `manage.py import_gedcom plik.ged`
- **Import bazy z Excela** — `manage.py import_excel`
- **Auto-rozmieszczenie grobów na planie** — `manage.py rozmiesc_groby`

### Integracje
- **REST API** — `/api/v1/sektory/`, `/groby/`, `/osoby/` z filtrami i search (DRF + django-filter)
- **GraphQL** — `/graphql/` z GraphiQL UI (graphene-django)
- **Embedded widget** — `/widget/` do osadzania w iframe parafii
- **Health check** — `/health/` JSON z metrykami systemu (DB, dysk)
- **Sentry** — opcjonalnie przez `SENTRY_DSN`

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

Szczegóły: [`docs/DEPLOY.md`](docs/DEPLOY.md).

## Stack

| Warstwa            | Technologia                                                          |
|--------------------|----------------------------------------------------------------------|
| Backend            | Python 3.10+, Django 5.2, SQLite + FTS5                              |
| API                | Django REST Framework, django-filter, graphene-django                |
| Frontend           | Tailwind CSS (CDN), Inter + Cormorant Garamond, vanilla JS           |
| Mapa               | Leaflet 1.9 (CRS.Simple)                                             |
| Wykresy            | Chart.js 4 + canvas timeline                                         |
| 360°               | Pannellum 2.5                                                        |
| PDF / XLSX / QR    | reportlab, openpyxl, qrcode                                          |
| 2FA / Push         | django-otp, pywebpush                                                |
| Produkcja          | gunicorn, nginx, systemd                                             |
| CI                 | GitHub Actions (matrix Python 3.10 + 3.12)                           |

## Modele danych

```
Sektor 1───n Grob 1───n Osoba ───n Wspomnienie / Swieca / Tag (M2M) / Relacja
              │            └ FK ──── Wpis (postacie)
              ├── n Zdjecie
              └── n Zgloszenie

Sektor ───n Panorama ───n HotspotPanoramy

User 1───1 Profil ───n Grob/Osoba (obserwowane)
       │       └── n ZapisaneSzukanie
       └── n SubskrypcjaPush, TokenLogowania (magic-link)

HistoriaZmian — audit log (sygnały)
```

Pełny opis architektury: [`docs/ARCHITEKTURA.md`](docs/ARCHITEKTURA.md).

## API

Przeglądalne pod `/api/v1/` (DRF browsable). Dokumentacja użytkownika i przykłady curl: [`docs/API.md`](docs/API.md).

GraphQL pod `/graphql/` z GraphiQL — możesz interaktywnie eksplorować schemat.

## Komendy zarządzania

```bash
python manage.py import_excel <plik.xlsx>      # import bazy
python manage.py import_gedcom <plik.ged>      # import drzewa genealogicznego
python manage.py rozmiesc_groby                # auto-układ markerów na planie
python manage.py waliduj                       # raport spójności danych
python manage.py waliduj --json                # do CI / monitoringu
```

## Testy

```bash
python manage.py test groby
```

59 testów: modele, widoki, API, formularze, parsing dat, walidator, GEDCOM, FTS, anti-spam, świeczki, wspomnienia, PWA.

## Licencja

Praca inżynierska — Mateusz Łagocki, 2026.

Kod open-source na licencji MIT (komponenty third-party — wg ich własnych licencji).

## Podziękowania

Parafia pw. św. Władysława w Szydłowie — udostępnienie księgi grobów i pomoc w weryfikacji danych.
