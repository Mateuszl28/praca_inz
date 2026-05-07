#!/usr/bin/env bash
# Skrypt deployu / aktualizacji aplikacji "groby" na świeżym Ubuntu 22.04 VPS.
#
# Idempotentny: można uruchamiać wiele razy.
#  - pierwszy raz: instaluje pakiety, klonuje repo, tworzy venv, robi migracje,
#    konfiguruje gunicorn (systemd) i nginx (port 80, brak domeny),
#  - kolejne razy: wystarczy git pull + pip install + migrate + restart.
#
# Uruchomienie z poziomu root:
#     wget -qO /tmp/deploy.sh https://raw.githubusercontent.com/Mateuszl28/praca_inz/main/deploy.sh
#     bash /tmp/deploy.sh
#
# Albo jednolinijkowo:
#     wget -qO- https://raw.githubusercontent.com/Mateuszl28/praca_inz/main/deploy.sh | bash

set -euo pipefail

REPO_URL="https://github.com/Mateuszl28/praca_inz.git"
APP_DIR="/opt/praca_inz"
APP_USER="www-data"
GUNICORN_BIND="127.0.0.1:8001"
SERVICE_NAME="groby"
PYTHON_BIN="python3"

echo
echo "=========================================="
echo " Deploy aplikacji 'groby' na VPS"
echo "=========================================="
echo

# --- Pakiety systemowe (idempotentne, instaluje brakujące) ---
if ! command -v git >/dev/null 2>&1 || ! command -v nginx >/dev/null 2>&1 \
   || ! dpkg -s python3-venv >/dev/null 2>&1 || ! dpkg -s python3-pip >/dev/null 2>&1 \
   || ! dpkg -s libpangocairo-1.0-0 >/dev/null 2>&1; then
    echo "[1/7] Instaluje pakiety systemowe..."
    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        git nginx python3 python3-venv python3-pip python3-dev \
        build-essential libjpeg-dev zlib1g-dev libfreetype6-dev \
        sqlite3
else
    echo "[1/7] Pakiety systemowe juz sa, pomijam."
fi

# --- Klon / pull repo ---
if [ ! -d "$APP_DIR/.git" ]; then
    echo "[2/7] Klonuje repo do $APP_DIR..."
    rm -rf "$APP_DIR"
    git clone --depth 1 "$REPO_URL" "$APP_DIR"
else
    echo "[2/7] Aktualizuje repo (git pull)..."
    cd "$APP_DIR"
    git fetch origin main
    git reset --hard origin/main
fi
cd "$APP_DIR"

# --- Wirtualne srodowisko + paczki ---
if [ ! -d "$APP_DIR/venv" ]; then
    echo "[3/7] Tworze venv..."
    "$PYTHON_BIN" -m venv venv
fi
echo "[3/7] Instaluje wymagania Pythona..."
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r requirements.txt

# --- .env (utworz tylko jesli nie istnieje) ---
if [ ! -f "$APP_DIR/.env" ]; then
    echo "[4/7] Generuje plik .env..."
    SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    IP=$(hostname -I | awk '{print $1}')
    cat > "$APP_DIR/.env" <<EOF
DJANGO_SECRET_KEY=$SECRET
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$IP,localhost,127.0.0.1
PLAN_IMAGE=plan_cmentarza/scan_oznaczenia.jpg
EOF
    chmod 640 "$APP_DIR/.env"
else
    echo "[4/7] Plik .env istnieje, pomijam."
fi

# --- Migracje, collectstatic ---
echo "[5/7] Migracje bazy + collectstatic..."
mkdir -p "$APP_DIR/static" "$APP_DIR/media" "$APP_DIR/staticfiles"
"$APP_DIR/venv/bin/python" manage.py migrate --noinput
"$APP_DIR/venv/bin/python" manage.py collectstatic --noinput >/dev/null

# Pierwszy uruchomienie: rozmiesc groby na planie jesli ich nie ma.
if "$APP_DIR/venv/bin/python" - <<'PY'
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from groby.models import Grob
import sys
sys.exit(0 if Grob.objects.filter(plan_x__isnull=True).exists() else 1)
PY
then
    echo "  - rozmieszczam groby na planie..."
    "$APP_DIR/venv/bin/python" manage.py rozmiesc_groby \
        --x-min 730 --x-max 1290 --y-min 100 --y-max 3950 || true
fi

# Wlasciciel plikow
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# --- Systemd unit dla gunicorna ---
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
if [ ! -f "$UNIT_FILE" ]; then
    echo "[6/7] Konfiguruje systemd unit dla gunicorna..."
    cat > "$UNIT_FILE" <<EOF
[Unit]
Description=Groby (Django) gunicorn
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn config.wsgi:application --workers 3 --bind $GUNICORN_BIND --access-logfile - --error-logfile -
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable --now "$SERVICE_NAME"
else
    echo "[6/7] Restart gunicorna..."
    systemctl restart "$SERVICE_NAME"
fi

# --- nginx jako reverse proxy port 80 ---
NGINX_CONF="/etc/nginx/sites-available/${SERVICE_NAME}.conf"
if [ ! -f "$NGINX_CONF" ]; then
    echo "[7/7] Konfiguruje nginx..."
    cat > "$NGINX_CONF" <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;
    client_max_body_size 25m;

    location /static/ {
        alias $APP_DIR/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias $APP_DIR/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://$GUNICORN_BIND;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    rm -f /etc/nginx/sites-enabled/default
    ln -sf "$NGINX_CONF" "/etc/nginx/sites-enabled/${SERVICE_NAME}.conf"
    nginx -t
    systemctl reload nginx
else
    echo "[7/7] Konfiguracja nginx juz jest, reload..."
    nginx -t
    systemctl reload nginx
fi

echo
echo "=========================================="
IP_FINAL=$(hostname -I | awk '{print $1}')
echo " GOTOWE!"
echo " Aplikacja: http://$IP_FINAL/"
echo " Status:    systemctl status $SERVICE_NAME"
echo " Logi:      journalctl -u $SERVICE_NAME -f"
echo "=========================================="
