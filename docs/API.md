# REST API — `/api/v1/`

Wszystkie endpointy zwracają JSON. Domyślna paginacja: 50 elementów na stronę (`?page=2`).

Autoryzacja:
- **GET** — publiczne (brak logowania).
- **POST/PUT/PATCH/DELETE** — wymaga zalogowania (Session lub Basic Auth).

## Endpointy

### `/api/v1/sektory/`

```http
GET /api/v1/sektory/
GET /api/v1/sektory/{id}/
GET /api/v1/sektory/{id}/groby/
```

Pole `liczba_grobow` zwracane automatycznie. Nie można edytować przez API (read-only).

### `/api/v1/groby/`

```http
GET    /api/v1/groby/?sektor=1&typ=ziemny
GET    /api/v1/groby/{id}/
POST   /api/v1/groby/                 # zalogowany
PATCH  /api/v1/groby/{id}/            # zalogowany
DELETE /api/v1/groby/{id}/            # zalogowany
```

Filtry: `sektor`, `typ`, `rzad`. Search: `?search=Kowalski`. Sort: `?ordering=-data_modyfikacji`.

Każdy grób zawiera tablicę `osoby` (skrócone reprezentacje).

### `/api/v1/osoby/`

```http
GET /api/v1/osoby/?grob__sektor=1
GET /api/v1/osoby/?search=Kowal
GET /api/v1/osoby/?ordering=nazwisko
```

Filtry: `grob__sektor`, `grob__typ`. Search: `nazwisko`, `imie`, `nazwisko_rodowe`.

## Przykłady (`curl`)

Pobierz wszystkie sektory:

```bash
curl https://twoja-domena.pl/api/v1/sektory/
```

Wyszukaj osoby po nazwisku:

```bash
curl 'https://twoja-domena.pl/api/v1/osoby/?search=Kowalski'
```

Dodaj nową osobę (Basic Auth):

```bash
curl -u admin:HASLO -X POST https://twoja-domena.pl/api/v1/osoby/ \
     -H 'Content-Type: application/json' \
     -d '{"imie":"Jan","nazwisko":"Nowy","grob_id":42}'
```

Aktualizuj typ grobu:

```bash
curl -u admin:HASLO -X PATCH https://twoja-domena.pl/api/v1/groby/42/ \
     -H 'Content-Type: application/json' \
     -d '{"typ":"murowany"}'
```

## DRF browsable API

Otwórz w przeglądarce: `https://twoja-domena.pl/api/v1/` — interaktywny widok z możliwością wykonania zapytań i przeglądania wyników w HTML. Logowanie przez `/api/auth/login/`.
