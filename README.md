# Voyage Assistant — SAE2 BUT3

> Plateforme web de réservation de transport multi-mode (avion, train, bateau, bus
> longue distance) dotée d'un **assistant IA conversationnel** capable de répondre
> aux questions des voyageurs, de **modifier réellement** une réservation, de
> signaler un retard et de déposer une réclamation — le tout déployé en ligne.

**Application en ligne : https://optimalako-voyage-assistant.hf.space**

Projet réalisé dans le cadre de la **SAE2 BUT3**, domaine **transport**.
Encadrement : **Bilal Faye** (LIPN, CNRS UMR 7030).

### Équipe

| Membre | Rôle |
|---|---|
| **Ako Christian** | Développement ML / Android |
| **Carl Similien** | Développement Android / Intégration |
| **Noé Cervera** | Entraînement des modèles / Évaluation |
| **Dhanoush Kessavane** | Front-end / Design / Documentation |

---

## Sommaire

1. [Présentation](#1-présentation)
2. [Glossaire — les concepts, simplement](#2-glossaire--les-concepts-simplement)
3. [Stack technique](#3-stack-technique)
4. [Architecture du projet](#4-architecture-du-projet)
5. [Le cerveau du chatbot : 3 sources de connaissance](#5-le-cerveau-du-chatbot--3-sources-de-connaissance)
6. [Sécurité du chatbot](#6-sécurité-du-chatbot)
7. [Mise en ligne (déploiement) — comment on a procédé](#7-mise-en-ligne-déploiement--comment-on-a-procédé)
8. [Difficultés rencontrées & solutions](#8-difficultés-rencontrées--solutions)
9. [Installation & lancement en local](#9-installation--lancement-en-local)
10. [Endpoints de l'API](#10-endpoints-de-lapi)
11. [Tests de robustesse](#11-tests-de-robustesse)
12. [Réponse au cahier des charges](#12-réponse-au-cahier-des-charges)

---

## 1. Présentation

Voyage Assistant est une application **full-stack** (frontend + backend + base de
données + IA) sur le domaine du **transport de voyageurs**. Un utilisateur peut :

- **Rechercher** un trajet (aller simple, aller-retour, retour seul) avec
  autocomplétion des villes et filtres (mode, horaire, escales) sur un catalogue
  de **182 000+ liaisons réelles**.
- **Réserver** un billet en choisissant la classe (Éco / Premium / Affaires /
  Première) et des bagages, puis recevoir un **email de confirmation** avec le
  **billet en PDF** en pièce jointe.
- **Gérer son compte** (connexion Google ou email/mot de passe) et retrouver
  l'historique de ses billets.
- **Discuter avec un assistant IA** qui :
  - vérifie son identité (numéro de billet + nom + prénom + date de naissance) ;
  - **modifie réellement** la réservation en base (avec ré-émission du PDF + email) ;
  - dépose une réclamation / demande d'indemnité avec numéro de suivi ;
  - répond aux questions de voyage (durée du vol, météo et heure à destination,
    taux de change, horaires, formalités…) ;
  - reste **robuste** face aux insultes, aux injections de prompt et aux sujets
    hors-périmètre.

La grande idée pédagogique du projet est de montrer qu'un chatbot utile **ne se
contente pas d'un LLM** : il combine un modèle de langage avec des **sources de
vérité** (base de données, documents, web temps réel) pour répondre du **factuel**
plutôt que d'**inventer**.

---

## 2. Glossaire — les concepts, simplement

Cette section explique, sans jargon, les notions qui structurent le projet. Elle
sert aussi à répondre clairement aux questions sur ce qu'on a mis en place.

### LLM (Large Language Model)
Un **modèle de langage** (ici **Google Gemini 2.5 Flash**) : on lui donne du texte,
il produit du texte. Il est très bon pour formuler une réponse naturelle, mais il a
deux limites : il **invente** parfois (« hallucinations ») et ses connaissances sont
**figées** à sa date d'entraînement (il ne connaît ni la météo d'aujourd'hui, ni le
contenu de *notre* base de données). On corrige ces deux limites avec le RAG.

### RAG (Retrieval-Augmented Generation) — *« génération augmentée par la récupération »*
C'est le cœur du projet. Au lieu de demander une réponse au LLM « à l'aveugle », on
**récupère d'abord l'information pertinente** (dans des documents, la base, ou le web),
puis on l'**injecte dans le prompt** avant de générer la réponse. Le LLM répond donc
**en s'appuyant sur des faits fournis**, pas sur sa mémoire approximative.

> Analogie : un examen « à livre ouvert ». Plutôt que de réciter de mémoire (et de se
> tromper), l'IA a le bon paragraphe sous les yeux au moment de répondre.

### Vectorisation / Embeddings — *« transformer du sens en nombres »*
Pour retrouver le bon paragraphe, l'ordinateur ne peut pas « lire » comme nous. On
convertit donc chaque morceau de texte en un **vecteur** : une liste de nombres
(ici **384 dimensions**) qui **encode le sens** de la phrase. Deux textes au sens
proche ont des vecteurs proches dans l'espace, **même s'ils n'utilisent pas les mêmes
mots**. C'est exactement ce que le prof désignait : grâce à cette conversion, l'IA
fait le lien entre « je veux annuler » et un article de CGV intitulé « conditions de
résiliation », sans correspondance de mots-clés.

On utilise le modèle d'embeddings **`thenlper/gte-small`** (multilingue, exécuté
**en local**, pas via une API cloud).

### Chunking — *« découper en morceaux »*
Un document est trop long pour être vectorisé d'un bloc. On le **découpe en chunks**
(morceaux de ~512 caractères, avec un léger chevauchement pour ne pas couper une idée
en deux). Chaque chunk devient un vecteur. Outil utilisé :
**`RecursiveCharacterTextSplitter`** de LangChain.

### FAISS — *« la base de données de vecteurs »*
**FAISS** (Facebook AI Similarity Search) stocke tous les vecteurs et trouve
**très vite** les plus proches d'une requête. C'est notre **index vectoriel**.

### Bi-encoder vs Cross-encoder (le *reranking* en 2 étapes)
- Le **bi-encoder** (gte-small) est **rapide** : il compare la requête à des milliers
  de chunks et en remonte 10 candidats. Mais sa précision est moyenne.
- Le **cross-encoder** (**`cross-encoder/ms-marco-MiniLM-L-6-v2`**) est **lent mais
  précis** : il regarde la question **et** un chunk **ensemble** pour juger leur
  pertinence réelle. On l'utilise pour **re-trier** les 10 candidats et n'en garder
  que les **3 meilleurs**.

> Pourquoi deux étapes ? On obtient la précision du cross-encoder sans payer son coût
> sur tout le corpus : il ne re-juge que 10 candidats, pas 200.

### NER (Named Entity Recognition) — *« reconnaissance d'entités »*
Un modèle (**`Jean-Baptiste/camembert-ner`**, français) qui repère dans une phrase
libre les **noms propres** (prénom, nom). Exemple : *« je m'appelle Pierre Girard »*
→ `{prenom: "Pierre", nom: "Girard"}`. Cela permet à l'utilisateur de tout dire d'un
coup au lieu de répondre à 3 questions séparées.

### LangChain
Une **boîte à outils** Python qui relie tous ces composants (découpage, embeddings,
FAISS, requêtes) avec une API unifiée.

### API REST / FastAPI
Le **backend** expose des **routes HTTP** (`/chat/message`, `/billets`, …) que le
frontend appelle. **FastAPI** génère aussi automatiquement la doc interactive
(`/docs`).

### OAuth / JWT
- **OAuth Google** : se connecter avec son compte Google sans créer de mot de passe.
- **Token (type JWT)** : après connexion, le serveur renvoie un **jeton signé** que
  le navigateur renvoie à chaque requête pour prouver qui il est.

---

## 3. Stack technique

### Backend (`backend/`)

| Composant | Technologie | Rôle |
|---|---|---|
| Framework web | **FastAPI** | Routes HTTP + validation + doc OpenAPI |
| ORM | **SQLAlchemy 2.0** | Mapping objets ↔ base de données |
| Validation | **Pydantic 2** | Schémas d'entrée/sortie typés |
| Base de données | **PostgreSQL (Neon)** en prod · **SQLite** en local | Users, 182k routes, billets, sessions de chat |
| LLM | **Google Gemini 2.5 Flash** | Réponses conversationnelles |
| RAG | **LangChain + FAISS + `thenlper/gte-small`** | Récupération vectorielle (CGV + billets) |
| Reranker | **CrossEncoder `ms-marco-MiniLM-L-6-v2`** | Re-tri des chunks par attention croisée |
| NER | **CamemBERT `Jean-Baptiste/camembert-ner`** | Extraction prénom/nom d'un message libre |
| APIs temps réel | **Open-Meteo** (météo/heure) · **Frankfurter** (change) | Données du jour que ni le LLM ni le RAG ne connaissent |
| Recherche web | **DuckDuckGo** via `ddgs` | Compléments temps réel (formalités, à voir…) |
| Email | **Brevo** | Mail transactionnel + pièce jointe PDF |
| PDF | **ReportLab** | Génération du billet A4 |
| Auth | HMAC custom + **Google Identity** | Tokens email/mdp + Google OAuth |

### Frontend (`frontend/`)

| Composant | Technologie | Rôle |
|---|---|---|
| UI | **React 18** (Babel inline, sans build) | Composants déclaratifs |
| Style | CSS custom (dark / light / system) | Identité visuelle |
| Auth Google | **Google Identity Services** | Sign-In Web |
| HTTP | `fetch` natif | Appels à l'API FastAPI |
| Voix | **Web Speech API** | Dictée (STT) + lecture des réponses (TTS) |

### Infrastructure (production)

| Élément | Service | Pourquoi |
|---|---|---|
| Hébergement appli | **Hugging Face Spaces** (Docker, gratuit) | 16 Go de RAM gratuits — indispensable pour faire tourner torch + 2 modèles RAG |
| Base de données | **Neon** (PostgreSQL serverless, gratuit) | Postgres persistant, co-localisé avec le Space (us-east-1) |
| Conteneur | **Docker** (torch **CPU-only**) | Image légère, modèles RAG pré-téléchargés |

---

## 4. Architecture du projet

```
/Projet/SAE2/
├── Dockerfile                 # Image de production (HF Spaces, port 7860, torch CPU)
├── .dockerignore
├── DEPLOY.md                  # Guide de déploiement pas à pas
├── backend/
│   ├── app/
│   │   ├── main.py            # Bootstrap FastAPI + CORS + montage du front statique
│   │   ├── config.py          # Settings via .env (pydantic-settings)
│   │   ├── database.py        # Engine SQLAlchemy + get_db()
│   │   ├── models.py          # Tables : User, Route, Trajet, Billet, Reclamation,
│   │   │                      #          ChatSession, ChatMessage, Admin
│   │   ├── schemas.py         # Schémas Pydantic in/out
│   │   ├── data/cgv/          # Documents CGV (Markdown) indexés par le RAG
│   │   ├── routers/           # auth, trajets, billets, reclamations, chat, admin, lieux, images, stats
│   │   └── services/
│   │       ├── chatbot.py     # ❤ State machine + détection d'intention + sécurité
│   │       ├── gemini.py      # SDK Google Generative AI
│   │       ├── rag.py         # LangChain + FAISS + embeddings gte-small
│   │       ├── reranker.py    # CrossEncoder ms-marco (re-tri des chunks)
│   │       ├── ner.py         # NER CamemBERT (extraction d'entités)
│   │       ├── travel_apis.py # Open-Meteo (météo/heure) + Frankfurter (change)
│   │       ├── web_search.py  # Wrapper DuckDuckGo (ddgs)
│   │       ├── billet_pdf.py  # Billet PDF (ReportLab)
│   │       ├── email.py       # Email HTML + PDF (Brevo)
│   │       ├── identity.py    # Vérification d'identité (tolérante à l'inversion)
│   │       └── numeros.py     # Génération des numéros TRV-2026-XXXXXX
│   ├── seed.py                # Peuplement de démo (trajets, users, billets)
│   └── migrate_to_postgres.py # Migration des données SQLite → Neon
└── frontend/
    ├── index.html             # Charge React + Babel + Google Identity + tous les .jsx
    ├── api.js                 # Wrappers fetch (window.VA_API)
    ├── voyage-pages.jsx       # Pages : Home / Results / Booking / Confirm / MesBillets
    ├── voyage-chatbot-interactive.jsx  # L'assistant IA (UI complète)
    ├── voyage-auth.jsx        # Connexion Google / email
    └── ...                    # composants partagés, recherche, icônes, styles
```

### Flux d'une question au chatbot

```
Navigateur (React)
   │  POST /chat/message
   ▼
FastAPI ── chatbot.py
   ├── 1. Sanitization + détection d'intention
   ├── 2. Action sensible ?  ──► State machine (vérif identité → modif/réclamation réelle → email+PDF)
   └── 2'. Question libre ?   ──► On récupère le contexte depuis 3 sources :
            ├── RAG vectoriel (FAISS + reranker) sur les CGV / billets
            ├── Base de données (billet vérifié, durée du trajet…)
            └── APIs temps réel + Web (météo, heure, change, DuckDuckGo)
                       │
                       ▼  contexte injecté dans le prompt
                    Gemini 2.5 Flash ──► réponse factuelle
```

---

## 5. Le cerveau du chatbot : 3 sources de connaissance

Le chatbot ne « devine » pas : selon la question, il va chercher l'information à la
**bonne source**, puis laisse Gemini rédiger la réponse à partir de ces faits. Le
champ `tools_used` renvoyé par l'API indique quelles sources ont servi
(`rag`, `api`, `web`, ou combinaisons).

### Source 1 — RAG documentaire vectoriel (`rag.py` + `reranker.py`)
Pour les **questions sur les règles** (annulation, bagages, remboursement).
- Les **CGV** (`backend/app/data/cgv/`) sont découpées, vectorisées et stockées dans
  **FAISS** au démarrage.
- À chaque question : **bi-encoder** → 10 candidats → **cross-encoder** → 3 meilleurs
  chunks → injectés dans le prompt.

*Exemple* : « je peux annuler 3 jours avant ? » → le bon article de CGV est retrouvé
par le sens (pas par mots-clés) → réponse fiable avec les frais exacts.

### Source 2 — Base de données (`chatbot.py`)
Pour les **questions personnelles** sur un billet vérifié.
Une fois l'identité confirmée, les infos du billet (trajet, **durée calculée**,
horaires, prix, retard) sont injectées telles quelles.

*Exemple* : « **combien de temps va durer mon vol ?** » → le bot lit le billet de
l'utilisateur en base (Malaga → Nice, EasyJet), **calcule la durée** à partir des
horaires (4 h 38) et répond **personnellement**. Choix assumé : la durée vient de
**notre base** (fiable), pas d'une estimation en ligne.

### Source 3 — APIs temps réel + Web (`travel_apis.py` + `web_search.py`)
Pour les **données du jour**, que ni le LLM ni le RAG ne peuvent connaître (ils sont
figés dans le temps) :
- **Open-Meteo** (sans clé) : **météo actuelle + heure locale + fuseau** d'une ville.
- **Frankfurter / BCE** (sans clé) : **taux de change du jour**.
- **DuckDuckGo** (`ddgs`) : compléments (formalités, lieux à visiter…).

*Exemples* : « Quel temps fait-il à Barcelone ? » → `api` (27 °C, ciel dégagé) ·
« 200 euros en yens ? » → `api` (taux du jour) · « Quelle heure est-il à New York ? »
→ `api` (heure locale réelle).

> Les infos **stables** (capitale, langue, monnaie d'un pays) ne passent **pas** par
> une API : Gemini les connaît déjà. On n'appelle une source externe que pour ce qui
> **change** ou ce qui est **personnel**.

### State machine + NER pour les actions sensibles
Modifier / annuler / réclamer **ne sont jamais laissés au LLM** (il halluciner ait).
Une **machine à états** déterministe guide le parcours :

```
intention détectée → numéro de billet → nom → prénom → date de naissance
→ vérification identité (base) → exécution RÉELLE (modif / réclamation / annulation)
→ email + PDF envoyés
```

Le **NER CamemBERT** sert de raccourci : si l'utilisateur donne déjà ses infos dans
sa phrase, on saute les questions correspondantes.

---

## 6. Sécurité du chatbot

| Couche | Mécanisme |
|---|---|
| Sanitization | Suppression des balises HTML, normalisation, contrôle des caractères |
| Garde-fous | Regex insultes / sujets dangereux / injections de prompt |
| Anti-extraction | Numéro de billet cité sans identité → redirection vers la procédure |
| Switch de flow | Changement de parcours en cours → confirmation explicite |
| SYSTEM_PROMPT | Périmètre strict + refus codifiés (Gemini ne sort pas du cadre) |
| Base de données | SQLAlchemy paramétré (anti-injection SQL natif) |
| Rendu | React échappe le HTML par défaut (anti-XSS natif) |
| Identité | Vérification croisée : numéro + nom + prénom + date de naissance |
| Secrets | Aucune clé dans le code : variables d'environnement / secrets HF |

---

## 7. Mise en ligne (déploiement) — comment on a procédé

L'application est **réellement en ligne** : https://optimalako-voyage-assistant.hf.space

### 7.1 Le choix d'architecture (et pourquoi)

Le RAG impose **torch + 2 modèles Transformers** chargés en mémoire (~700 Mo–1 Go de
RAM). C'est ce qui a dicté l'hébergeur :

- **Render / Railway / Fly (offres gratuites)** : ~**512 Mo de RAM** → l'appli
  **plante (OOM)** dès le chargement des modèles. **Écartés.**
- **Hugging Face Spaces (gratuit)** : **16 Go de RAM**, conçu pour les modèles ML,
  met en cache les téléchargements de modèles. **Choisi.**

On a retenu une architecture **mono-service** : **un seul** conteneur sert à la fois
l'**API**, le **RAG** et le **front statique** (même origine → aucun problème de CORS,
et l'URL de l'API est automatiquement celle du site). La base de données est
**externe** (Neon), pour que les données **persistent** même si le conteneur redémarre.

```
Navigateur ─► Hugging Face Space (Docker, 16 Go RAM)
                ├─ FastAPI (API)
                ├─ RAG (gte-small + reranker, torch CPU)
                └─ Front statique (servi par FastAPI)
                        │
                        └─► Neon (PostgreSQL) : users, 182k routes, billets…
```

### 7.2 La base de données — Neon (PostgreSQL)

1. Création d'un projet Postgres gratuit sur Neon, région **AWS us-east-1**
   (volontairement **co-localisée** avec les Spaces HF → latence app↔base minimale).
2. **Migration des données existantes.** La table `routes` (**182 511 lignes**) n'est
   pas régénérée par le seed : elle n'existait que dans le fichier SQLite local. On a
   donc écrit **`backend/migrate_to_postgres.py`** qui recrée le schéma sur Neon et
   **copie toutes les tables** (routes, users, billets, sessions de chat…) par lots,
   dans l'ordre des clés étrangères.
3. Le code est **agnostique** à la base : il suffit de pointer la variable
   `DATABASE_URL` (`postgresql+psycopg://…`) sur Neon, le driver **psycopg 3** fait
   le reste.

### 7.3 L'application — Hugging Face Space (Docker)

- **`Dockerfile`** dédié : on installe **torch en version CPU-only** (~200 Mo au lieu
  de la version CUDA de 1,2 Go), puis les dépendances, puis on **pré-télécharge les
  modèles RAG dans l'image** pour réduire le démarrage à froid. Le conteneur écoute
  sur le **port 7860** (attendu par HF) et **sert aussi le front**.
- **Secrets** (jamais dans le code, configurés côté HF) : `DATABASE_URL`,
  `AUTH_SECRET` (signature des tokens), `GEMINI_API_KEY`, et en option
  `BREVO_API_KEY`, `PIXABAY_API_KEY`.
- **Build & run** : HF construit l'image et démarre l'appli. Au premier démarrage,
  FastAPI crée les index SQL manquants et indexe les CGV dans FAISS.

### 7.4 Connexion Google

Le bouton Google ne fonctionne sur un nouveau domaine qu'après avoir ajouté l'URL du
Space dans **Google Cloud Console → Identifiants → Origines JavaScript autorisées** :
`https://optimalako-voyage-assistant.hf.space`.

### 7.5 Validation en production

Tests end-to-end passés directement sur l'URL publique : front servi, connexion d'un
compte, recherche dans les 182k routes, durée du vol (base), météo et change
(APIs temps réel). Tout répond correctement.

> **Note** : sur l'offre gratuite, le Space se **met en veille** après ~48 h
> d'inactivité ; le premier accès suivant prend ~30 s pour se réveiller, puis tout
> redevient instantané.

Le détail clic par clic est dans **`DEPLOY.md`**.

---

## 8. Difficultés rencontrées & solutions

### 8.1 DuckDuckGo bloqué (`202 Ratelimit`)
La librairie `duckduckgo-search` était rate-limitée après quelques requêtes.
**Solution** : passage à **`ddgs`** (multi-backend avec rotation automatique
`auto/html/lite`), plus de blocage après 50+ requêtes.

### 8.2 Google ne fournit pas la date de naissance
Le scope OAuth standard ne renvoie pas la date de naissance, ce qui faisait échouer la
vérification d'identité du chatbot. **Solution** : le formulaire de réservation devient
la **source de vérité** (mise à jour des infos du voyageur), et la vérification tolère
l'**inversion nom ↔ prénom**.

### 8.3 Hallucinations sur les actions
Gemini pouvait répondre « réservation confirmée » sans rien modifier. **Solution** :
séparation stricte **state machine (exécute) ↔ LLM (rédige seulement)**.

### 8.4 Recherche de vols avec escales lente (15 s)
Sur 182k routes sans index, la recherche multi-escales faisait des milliers de scans
complets. **Solution** : **index SQL** (`depart_code`, `arrivee_code` + composites)
créés au démarrage, + **cache TTL en mémoire**. Paris→New York : **15 s → 0,34 s**
(puis quelques ms en cache).

### 8.5 RAG « classique » → vectoriel (retour du prof)
La 1re version utilisait des embeddings cloud + un store JSON + similarité codée à la
main. **Solution** : réécriture complète en **LangChain + FAISS + embeddings locaux
gte-small + reranker CrossEncoder** (Séance 1) et ajout du **NER CamemBERT** (Séance 4).

### 8.6 Déploiement : torch CUDA de 1,2 Go
L'environnement local installait torch en version **CUDA** (1,2 Go), incompatible avec
une image légère. **Solution** : dans le Dockerfile, installation de **torch CPU-only**
depuis l'index PyTorch dédié.

### 8.7 Déploiement : 512 Mo de RAM insuffisants
Premier réflexe d'héberger sur Render gratuit → OOM garanti avec torch + 2 modèles.
**Solution** : **Hugging Face Spaces** (16 Go gratuits), voir §7.

### 8.8 Déploiement : migration des 182k routes
Les routes n'existaient que dans le SQLite local. **Solution** : script
**`migrate_to_postgres.py`** qui copie les données vers Neon par lots.

---

## 9. Installation & lancement en local

### Prérequis
- **Python 3.12+**
- (Optionnel) clé Gemini, compte Brevo

### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # puis remplir GEMINI_API_KEY, etc.
python seed.py                # peuple la base SQLite locale
uvicorn app.main:app --port 8000 --reload
```
Un script `start.sh` à la racine automatise tout cela (venv dédié + seed + lancement).

### Frontend
```bash
cd frontend
python3 -m http.server 5173
# Ouvrir http://localhost:5173/
```

### Comptes de test
- `camille@test.fr` / `test1234` (utilisateur standard)
- `admin@voyage.local` / `changeme` (admin)

---

## 10. Endpoints de l'API

**Auth** — `POST /auth/signup` · `POST /auth/login` · `POST /auth/google` · `GET /auth/me`
**Voyage** — `GET /trajets` · `GET /trajets/{id}` · `GET /trajets/destinations` · `GET /lieux`
**Billets** — `POST /billets` · `GET /billets/mine` · `POST /billets/access` · `POST /billets/{num}/modifier` · `POST /billets/{num}/annuler`
**Réclamations** — `POST /reclamations` · `GET /reclamations/{num_suivi}`
**Chat** — `POST /chat/start` · `POST /chat/message` · `GET /chat/sessions` · `POST /chat/sessions/{token}/end`
**Admin** — `POST /admin/login` · `GET /admin/stats` · `/admin/billets` · `/admin/reclamations`
**Meta** — `GET /health` · `GET /docs` (doc interactive Swagger)

---

## 11. Tests de robustesse

Le chatbot a été testé en conditions « adversariales » :

| Test | Résultat |
|---|---|
| Insultes | Désescalade fixe |
| Injection de prompt (`ignore previous instructions`) | Refus codifié |
| Sujet dangereux | Refus poli ciblé |
| Hors-sujet (`écris-moi du Python`) | Refus via SYSTEM_PROMPT |
| Vol d'infos billet sans identité | Redirection vers la procédure |
| XSS (`<script>…`) | Strip HTML + échappement React |
| Injection SQL (`'; DROP TABLE`) | Neutralisée par SQLAlchemy paramétré |
| Message vide / 1 caractère | Demande de reformulation |
| Switch de flow en plein parcours | Confirmation explicite |
| Message > 4000 caractères | Troncature transparente |
| Inversion nom/prénom | Tolérée |

---

## 12. Réponse au cahier des charges

| Exigence du sujet | Où, dans le projet |
|---|---|
| **Domaine spécialisé** | Transport de voyageurs (avion/train/bateau/bus) |
| **Application full-stack** | FastAPI (back) + React (front) + PostgreSQL |
| **LLM** | Google Gemini 2.5 Flash (`gemini.py`) |
| **RAG / vectorisation** | LangChain + FAISS + embeddings gte-small + reranker (`rag.py`, `reranker.py`) |
| **Base de session (users + historique)** | Tables `users`, `chat_sessions`, `chat_messages` |
| **Voix (option)** | Web Speech API : dictée + lecture des réponses |
| **Recherche web (bonus)** | DuckDuckGo (`ddgs`) + APIs temps réel (météo, heure, change) |
| **Déploiement en ligne** | **Hugging Face Spaces + Neon** → https://optimalako-voyage-assistant.hf.space |

---

## Crédits

Projet **SAE2 BUT3**, promotion 2025-2026 · Encadrement : **Bilal Faye**
(LIPN, CNRS UMR 7030).

| Membre | Rôle |
|---|---|
| **Ako Christian** | Développement ML / Android |
| **Carl Similien** | Développement Android / Intégration |
| **Noé Cervera** | Entraînement des modèles / Évaluation |
| **Dhanoush Kessavane** | Front-end / Design / Documentation |

Stack : Python (FastAPI · SQLAlchemy · LangChain · FAISS · ReportLab), React,
Google Gemini, Hugging Face Transformers, Open-Meteo, Frankfurter, DuckDuckGo,
Brevo, Google OAuth — déployé sur Hugging Face Spaces & Neon.
