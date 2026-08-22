#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/home/severinz/cleango.severinzran.ci"
VENV_ROOT="/home/severinz/virtualenv/cleango.severinzran.ci/3.12"

source "$VENV_ROOT/bin/activate"
cd "$APP_ROOT"

if [ ! -f ".env" ]; then
    echo "ERREUR : créez le fichier $APP_ROOT/.env avant le déploiement."
    exit 1
fi

if grep -qi "^mysqlclient" requirements.txt; then
    echo "ERREUR : requirements.txt contient encore mysqlclient."
    echo "Remplacez-le par PyMySQL==1.1.1 avant de relancer le déploiement."
    exit 1
fi

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py check
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput

mkdir -p tmp
touch tmp/restart.txt

echo "CleanGo a été déployé et Passenger a été redémarré."
