# Deploiement automatique GitHub vers FTP

Le workflow `.github/workflows/deploy-ftp.yml` publie automatiquement le projet
sur le serveur apres chaque `push` sur la branche `main`. Il peut aussi etre
lance manuellement depuis l'onglet **Actions** de GitHub.

## Configuration des secrets GitHub

Dans le depot GitHub, ouvrir **Settings > Secrets and variables > Actions**, puis
creer les secrets suivants :

| Secret | Valeur attendue |
|---|---|
| `FTP_SERVER` | Serveur FTP, par exemple `ftp.example.com` |
| `FTP_USERNAME` | Utilisateur FTP cPanel |
| `FTP_PASSWORD` | Mot de passe FTP |
| `FTP_PROTOCOL` | `ftps` recommande, ou `ftp` si FTPS n'est pas disponible |
| `FTP_PORT` | `21` dans la plupart des configurations FTP/FTPS |
| `FTP_SERVER_DIR` | Dossier distant termine par `/`, par exemple `/cleango.severinzran.ci/` |

Le workflow genere les fichiers statiques avec `collectstatic --noinput`, puis
transfere `staticfiles` et son manifeste avec le code correspondant.
Il ne transfere pas `.env`, la base SQLite, `media`, les
logs ou l'environnement virtuel. Ces fichiers restent intacts sur le serveur.
Il actualise `tmp/restart.txt` pour redemarrer Passenger apres le deploiement.

## Limite du FTP

FTP ne peut pas executer de commande distante. Apres une modification de
`requirements.txt` ou l'ajout d'une migration Django, executer manuellement
`bash deploy_cpanel.sh` dans le terminal cPanel. Un deploiement SSH sera
necessaire pour automatiser egalement ces commandes.

## Reparer une erreur 500 apres un changement de design

Si le journal indique `Missing staticfiles manifest entry`, executer dans le
terminal cPanel :

```bash
source /home/severinz/virtualenv/cleango.severinzran.ci/3.12/bin/activate
cd /home/severinz/cleango.severinzran.ci
python manage.py collectstatic --noinput
mkdir -p tmp
touch tmp/restart.txt
```

Le workflow FTP reconstruit desormais ce manifeste a chaque deploiement.
