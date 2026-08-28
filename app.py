"""Point d’entrée Django pour le sélecteur Python de cPanel."""

import os
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

# Passenger peut démarrer depuis un autre répertoire. Django et
# python-decouple doivent toujours résoudre .env depuis la racine du projet.
os.chdir(APP_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application
