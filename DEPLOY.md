# Déploiement — Voyage Assistant (gratuit)

Architecture : **un seul service** sur **Hugging Face Spaces** (FastAPI + RAG torch
+ front statique, même URL) et **base Postgres sur Neon**.

```
  Navigateur ─────► Hugging Face Space (Docker)
                      ├─ FastAPI  (/auth, /chat, /trajets, ...)
                      ├─ RAG (gte-small + reranker, torch CPU)
                      └─ front statique (index.html, *.jsx)
                              │
                              └────► Neon (Postgres) : users, routes, billets...
```

Pourquoi pas Render/Railway free : 512 Mo de RAM, torch + 2 modèles RAG = OOM.
HF Spaces free = 16 Go RAM, conçu pour les modèles ML.

---

## 1. Base de données — Neon

1. Créer un compte sur https://neon.tech (gratuit, login GitHub possible).
2. **New Project** → région **Europe (Frankfurt)** → créer.
3. Copier la **connection string** (bouton *Connect*). Elle ressemble à :
   ```
   postgresql://USER:PASSWORD@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
4. **Important** : remplacer `postgresql://` par `postgresql+psycopg://` (on utilise
   psycopg 3). On obtient le `DATABASE_URL` à utiliser partout :
   ```
   postgresql+psycopg://USER:PASSWORD@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```

### Migrer les données existantes vers Neon

La table `routes` (~182 000 lignes) n'existe que dans `voyage.db` : on copie les
données plutôt que de relancer le seed.

```bash
cd backend
export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@ep-xxxx.../neondb?sslmode=require"
.venv/bin/python migrate_to_postgres.py          # source = ./voyage.db par défaut
```

Le script crée le schéma, vide les tables cibles (relançable) puis copie tout
(routes, users, billets, sessions de chat...). Compter 1 à 3 min pour les routes.

> Neon free = 0,5 Go de stockage : les ~65 Mo de données passent largement.

---

## 2. Application — Hugging Face Space

1. Créer un compte sur https://huggingface.co.
2. **New Space** : https://huggingface.co/new-space
   - Owner : ton compte
   - Space name : `voyage-assistant`
   - **SDK : Docker** (template *Blank*)
   - Visibilité : Public (suffisant pour la SAE)
3. Récupérer un **token d'accès** : Settings → Access Tokens → *New token* (rôle
   **Write**). Il sert à pousser le code.

### Pousser le code

Le dépôt du Space doit contenir : `Dockerfile`, `backend/`, `frontend/`, et un
`README.md` avec l'en-tête YAML (déjà prêt dans `SPACE_README.md`).

```bash
cd /home/optimalako/Projet/SAE2

# Cloner le dépôt vide du Space (remplace <user>)
git clone https://huggingface.co/spaces/<user>/voyage-assistant /tmp/space
cp SPACE_README.md /tmp/space/README.md
cp Dockerfile .dockerignore /tmp/space/
cp -r backend frontend /tmp/space/

cd /tmp/space
# ne pas envoyer la BDD locale ni le venv (déjà couverts par .dockerignore,
# mais on nettoie par sécurité)
rm -rf backend/.venv backend/voyage.db backend/app/rag/store

git add -A
git commit -m "Déploiement Voyage Assistant (FastAPI + RAG + front)"
git push    # login : <user> / mot de passe : le token Write
```

Le Space lance le build automatiquement (onglet **Logs**). Premier build ~10-15 min
(torch + modèles téléchargés dans l'image).

### Secrets du Space

Space → **Settings → Variables and secrets** → *New secret* pour chacun :

| Nom | Valeur | Obligatoire |
|---|---|---|
| `DATABASE_URL` | la chaîne Neon `postgresql+psycopg://...` | **oui** |
| `GEMINI_API_KEY` | ta clé Gemini | **oui** |
| `AUTH_SECRET` | une longue chaîne aléatoire (ex `openssl rand -hex 32`) | **oui** |
| `BREVO_API_KEY` | clé Brevo (emails) | si emails |
| `PIXABAY_API_KEY` | clé Pixabay (photos villes) | optionnel |
| `ADMIN_DEFAULT_PASSWORD` | mot de passe admin | optionnel |

Après ajout des secrets : **Settings → Factory reboot** pour les prendre en compte.

---

## 3. Google Sign-In

Le `GOOGLE_CLIENT_ID` est dans `frontend/index.html`. Pour que le bouton Google
marche sur le nouveau domaine :

1. https://console.cloud.google.com → **APIs & Services → Credentials**
2. Ouvrir le client OAuth utilisé.
3. **Authorized JavaScript origins** → ajouter :
   ```
   https://<user>-voyage-assistant.hf.space
   ```
4. Enregistrer (propagation quelques minutes).

---

## 4. Vérifier

URL publique : `https://<user>-voyage-assistant.hf.space`

```bash
curl https://<user>-voyage-assistant.hf.space/health
# {"status":"ok",...}
```

- Ouvrir l'URL dans le navigateur → le front s'affiche (servi par FastAPI).
- Se connecter avec le compte de test : `camille@test.fr` / `test1234`.
- Tester le chatbot : « Combien de temps va durer mon vol ? », « Quel temps fait-il
  à Barcelone ? », « 200 euros en yens ».

> Le Space **s'endort** après ~48 h d'inactivité (offre gratuite) : le premier
> appel après une mise en veille prend ~30 s à se réveiller, puis c'est rapide.

---

## Notes

- **torch CPU-only** : le Dockerfile installe `torch==2.12.0+cpu` (le venv local
  est en CUDA, trop lourd). Si ce numéro n'existe pas sur l'index CPU au moment du
  build, mettre la version CPU disponible la plus proche.
- **Front même origine** : `window.VA_CONFIG.API_BASE = window.location.origin`
  pointe automatiquement sur l'API du Space, aucun réglage à faire.
- **Re-déployer** : refaire un `git push` dans le dépôt du Space.
