# Deploy

## Lokalne uruchomienie (Windows / Linux / macOS)

```bash
git clone https://github.com/Mateuszl28/praca_inz.git
cd praca_inz
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # Windows
# venv/bin/pip install -r requirements.txt     # Linux / macOS
venv/Scripts/python manage.py migrate
venv/Scripts/python manage.py loaddata data/dump.json
venv/Scripts/python manage.py createsuperuser
venv/Scripts/python manage.py runserver
```

Strona: <http://127.0.0.1:8000/>, admin: <http://127.0.0.1:8000/admin/>.

## Docker

```bash
docker compose up --build
```

Aplikacja na <http://localhost:8000/>. Dane (DB, media, staticfiles) montowane jako wolumeny — przeżyją restart kontenera.

## VPS (Ubuntu 22.04+) — automatyczny deploy

Skrypt `deploy.sh` jest idempotentny — możesz go uruchamiać wielokrotnie. Pierwszy raz instaluje pakiety, klonuje repo, stawia gunicorn (systemd) i nginx; kolejne wywołania robią `git pull` + migracje + restart.

```bash
ssh root@TWOJ-IP
wget -qO /tmp/d.sh https://raw.githubusercontent.com/Mateuszl28/praca_inz/main/deploy.sh
bash /tmp/d.sh
```

Po pierwszym uruchomieniu:

- Aplikacja: `http://TWOJ-IP/`
- Admin: `http://TWOJ-IP/admin/` (login `admin`, hasło `admin123` — **zmień natychmiast**)

### Aktualizacja po push do GitHuba

```bash
bash /opt/praca_inz/deploy.sh
```

### Logi i status

```bash
systemctl status groby
journalctl -u groby -f          # live
journalctl -u groby --since "1 hour ago"
nginx -t && systemctl reload nginx
```

### Zmienne środowiskowe (`/opt/praca_inz/.env`)

| Klucz                    | Opis                                                          |
|--------------------------|---------------------------------------------------------------|
| `DJANGO_SECRET_KEY`      | Generowany losowo przy pierwszym uruchomieniu deploy.sh.      |
| `DJANGO_DEBUG`           | `False` na produkcji.                                         |
| `DJANGO_ALLOWED_HOSTS`   | Lista hostów oddzielona przecinkami.                          |
| `PLAN_IMAGE`             | Ścieżka do skanu planu względem `MEDIA_ROOT`.                 |
| `DJANGO_EMAIL_BACKEND`   | Domyślnie `console`. Na produkcji wymień na SMTP.             |
| `DEFAULT_FROM_EMAIL`     | Adres nadawcy.                                                |
| `SENTRY_DSN`             | Opcjonalnie — DSN Sentry do raportowania błędów.              |

### HTTPS (po podpięciu domeny)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d twoja-domena.pl --redirect --agree-tos -m admin@example.com
```

Po podpięciu domeny: dopisz ją do `DJANGO_ALLOWED_HOSTS` w `.env` i `systemctl restart groby`.

## Backup

SQLite siedzi w `/opt/praca_inz/db.sqlite3`. Codzienny snapshot:

```bash
sqlite3 /opt/praca_inz/db.sqlite3 ".backup '/var/backups/groby-$(date +%F).sqlite3'"
```

Albo eksport JSON z czasów audytu:

```bash
cd /opt/praca_inz
sudo -u www-data venv/bin/python manage.py dumpdata groby \
    --indent=2 --output=/var/backups/groby-$(date +%F).json
```

Plik z `media/` (zdjęcia, plan): `tar czf /var/backups/groby-media-$(date +%F).tar.gz /opt/praca_inz/media/`.
