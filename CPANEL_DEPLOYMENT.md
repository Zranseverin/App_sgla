# Déploiement cPanel

## Prérequis

- cPanel doit proposer **Setup Python App** ou **Application Manager** avec Passenger.
- Python 3.10 ou une version plus récente.
- Un domaine ou sous-domaine avec certificat SSL actif.
- Une base MySQL et un utilisateur MySQL créés depuis l’assistant cPanel.

## Création de l’application

Dans **Setup Python App**, créer une application avec :

- version Python : 3.10 ou plus récente ;
- racine de l’application : `/home/severinz/cleango.severinzran.ci` ;
- fichier de démarrage : `app.py` ;
- point d’entrée : `application`.

Téléverser ensuite le projet dans cette racine, sans inclure `.venv`, `.git` ni le fichier `.env` local.

## Variables d’environnement

Configurer les variables suivantes dans l’application Python cPanel :

```text
DJANGO_SECRET_KEY=une-cle-secrete-longue-et-aleatoire
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=cleango.severinzran.ci
DJANGO_CSRF_TRUSTED_ORIGINS=https://cleango.severinzran.ci
DB_NAME=utilisateurcpanel_nomdelabase
DB_USER=utilisateurcpanel_nomutilisateur
DB_PASSWORD=mot-de-passe-mysql
DB_HOST=localhost
DB_PORT=3306
GOOGLE_OAUTH_REDIRECT_URI=https://cleango.severinzran.ci/auth/google/callback/
```

Ajouter aussi les variables SMTP et Google OAuth si ces fonctions sont utilisées.

## Installation

Depuis le terminal cPanel, activer l’environnement virtuel indiqué par **Setup Python App**, puis exécuter depuis la racine :

```bash
source /home/severinz/virtualenv/cleango.severinzran.ci/3.12/bin/activate
cd /home/severinz/cleango.severinzran.ci
bash deploy_cpanel.sh
```

Importer les anciennes données avec phpMyAdmin avant `migrate` si la base locale doit être conservée.

## Fichiers médias

Le dossier `media` contient les logos et photos téléversés. Le faire servir par le domaine à l’adresse `/media/`, soit avec la configuration Passenger proposée par l’hébergeur, soit depuis un dossier public lié au `MEDIA_ROOT`.

## Redémarrage

Après une modification, utiliser le bouton **Restart** de l’application Python. Avec Passenger en terminal :

```bash
mkdir -p tmp
touch tmp/restart.txt
```
# Tâche quotidienne des rappels d’abonnement

Dans **cPanel → Cron Jobs**, programmez une exécution quotidienne (par exemple à 08h00) :

```bash
0 8 * * * cd /CHEMIN/DU/PROJET && .venv/bin/python manage.py send_subscription_reminders --base-url https://VOTRE-DOMAINE/
```

La commande envoie un seul rappel par échéance aux entreprises dont l’essai ou l’abonnement expire dans les trois prochains jours. Les doublons sont bloqués par le journal `SubscriptionEmailLog`.
