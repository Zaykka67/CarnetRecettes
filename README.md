# Carnet de recettes

Appli installable (PWA) pour garder tes recettes, classées par saison.
On partage une vidéo TikTok vers l'appli : le serveur lit la description et la miniature de la vidéo, puis Claude rédige la fiche (ingrédients, étapes, saisons, photo).

```
carnet-recettes/
├── app/
│   ├── main.py              serveur FastAPI (recettes, photos, import, connexion)
│   └── static/              l'appli : index.html, app.js, app.css, manifest, service worker, icônes
├── Dockerfile               image pour Coolify
├── docker-compose.yml       pour lancer en Docker sans Coolify
├── .env.example             variables à renseigner
└── lancer-local.bat         test en local sur Windows
```

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `APP_PASSWORD` | Mot de passe demandé à l'ouverture. **Obligatoire en ligne**, sinon n'importe qui peut lire ton carnet et consommer ta clé API. |
| `SECRET_KEY` | Longue chaîne aléatoire qui signe la session (tu restes connecté 1 an). Génère-la avec `openssl rand -hex 32`. |
| `ANTHROPIC_API_KEY` | Clé de l'API Claude, créée sur console.anthropic.com. Sans elle, l'appli marche mais sans import automatique. |
| `ANTHROPIC_MODEL` | Modèle utilisé, `claude-sonnet-5-5` par défaut. |
| `DATA_DIR` | Dossier des données, `/data` dans le conteneur. |

L'API Claude est facturée à part de l'abonnement Claude, à l'usage. Un import avec miniature coûte de l'ordre de quelques centimes.

## Tester en local (Windows)

1. Copie `.env.example` en `.env` et remplis-le.
2. Double-clique sur `lancer-local.bat` : il crée l'environnement Python la première fois, puis ouvre http://127.0.0.1:8000.

Les données sont dans le dossier `data\` à côté du script.

## Déployer sur le VPS avec Coolify

1. Pousse ce dossier dans un dépôt GitHub privé (par ex. `Zaykka67/CarnetRecettes`).
2. Dans Coolify : **+ New → Private Repository** (via ta GitHub App), choisis le dépôt, **Build Pack : Dockerfile**.
3. **Port exposé : 8000**.
4. **Domaine** : `https://recettes.duckdns.org` pour l'instant, puis `https://recettes.zaykka.fr` quand le domaine sera en place.
5. **Environment Variables** : `APP_PASSWORD`, `SECRET_KEY`, `ANTHROPIC_API_KEY` (et `ANTHROPIC_MODEL` si besoin).
6. **Storages → + Add → Volume Mount** : destination `/data`. Sans ce volume, recettes et photos disparaissent à chaque redéploiement.
7. **Deploy**. Le healthcheck interroge `/healthz`.

L'HTTPS est indispensable : sans lui, le téléphone refuse d'installer l'appli et de l'ajouter au menu Partager.

Sauvegarde : tout tient dans le volume `/data` (`recettes.db` et le dossier `photos/`).

## Installer l'appli sur le téléphone

**Android (Chrome)** : ouvre le site, connecte-toi, puis menu ⋮ → **Installer l'application** (ou le bouton « Installer » en haut). « Carnet » apparaît alors dans le menu **Partager** de TikTok : partage une vidéo, l'appli s'ouvre et lance la retranscription toute seule.

**iPhone (Safari)** : bouton Partager → **Sur l'écran d'accueil**. iOS ne permet pas aux applis web d'apparaître dans le menu Partager. Pour avoir le même geste, crée un raccourci :

1. App **Raccourcis** → **+** → nomme-le « Ajouter au Carnet ».
2. Touche ⓘ → active **Afficher dans la feuille de partage**, types acceptés : URL et Texte.
3. Ajoute l'action **Ouvrir les URL** avec : `https://recettes.zaykka.fr/share?url=` suivi de la variable **Entrée du raccourci**.

Dans TikTok : Partager → Plus → « Ajouter au Carnet ». La page s'ouvre dans Safari (connecte-toi une fois dans Safari aussi, la session de l'icône d'accueil est séparée).

## Comment marche l'import

- **TikTok / YouTube** : le serveur récupère la légende et la miniature via l'oEmbed officiel (sans compte ni clé).
- **Sites de cuisine** : il lit la description de la page et, s'il y en a, les données de recette structurées (schema.org).
- **Instagram** bloque souvent ce type de lecture : ajoute alors des captures d'écran ou colle la légende dans « Texte en plus ».
- Si la recette n'est dite qu'à l'oral dans la vidéo, la légende ne suffit pas : ajoute des captures des étapes, Claude lit ce qui est écrit à l'écran.

Claude ne regarde pas la vidéo elle-même et n'invente pas les quantités absentes : il les laisse vides et le signale. Tu relis toujours la fiche avant de l'enregistrer.

## API

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/api/config` | `{ai, auth, loggedIn}` |
| POST | `/api/login` / `/api/logout` | connexion par mot de passe (cookie) |
| GET / POST | `/api/recipes` | lister / créer |
| PUT / PATCH / DELETE | `/api/recipes/{id}` | remplacer / favori / supprimer (avec la photo) |
| POST | `/api/photos` | envoyer une photo (redimensionnée en JPEG 1600 px) |
| GET | `/photos/{id}` | lire une photo |
| POST | `/api/import` | `url`, `caption`, `images[]` → brouillon de fiche |
| GET | `/share` | cible du menu Partager |
