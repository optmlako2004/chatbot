# Voyage Assistant — SAE2 BUT3

Plateforme web complète de réservation transport multi-mode (avion, train, bateau, bus
longue distance) avec un **assistant IA conversationnel** capable de modifier les
réservations, signaler des retards, déposer des réclamations et répondre aux
questions des voyageurs.

Projet réalisé dans le cadre de la **SAE2 BUT3** (Mr FAYE & Mme AZZAG), domaine *transport*.

---

## 1. Sommaire

1. [Vue d'ensemble](#2-vue-densemble)
2. [Stack technique](#3-stack-technique)
3. [Architecture](#4-architecture)
4. [Concepts clés expliqués](#5-concepts-clés-expliqués)
5. [Le chatbot pas à pas](#6-le-chatbot-pas-à-pas)
6. [Difficultés rencontrées & solutions](#7-difficultés-rencontrées--solutions)
7. [Installation & lancement](#8-installation--lancement)
8. [Endpoints API](#9-endpoints-api)
9. [Tests de robustesse](#10-tests-de-robustesse)

---

## 2. Vue d'ensemble

L'utilisateur peut :

- Rechercher un trajet (aller simple, aller-retour, retour seul) avec autocomplétion
  des villes et filtrage par mode/horaire/escales
- Réserver son billet en choisissant la **classe** (Éco / Premium / Affaires / Première
  selon le mode) et en ajoutant des **bagages** payants
- Recevoir un **email de confirmation HTML** avec le **billet en PDF** en pièce jointe
- Retrouver l'**historique de ses billets** dans son compte (Google OAuth ou email/mdp)
- Discuter avec un **assistant IA** qui :
  - vérifie son identité (numéro de billet + nom + prénom + date de naissance)
  - **modifie réellement** sa réservation en BDD (avec ré-émission du PDF + email)
  - dépose une réclamation ou demande d'indemnité avec numéro de suivi
  - répond aux questions sur le voyage (météo, durée, horaires, à voir…)
  - reste robuste face aux insultes, injections de prompt, tentatives d'extraction
    d'infos et sujets hors-périmètre

---

## 3. Stack technique

### Backend — `backend/`

| Composant | Technologie | Rôle |
|---|---|---|
| Framework web | **FastAPI** | Routes HTTP + validation auto via OpenAPI |
| ORM | **SQLAlchemy 2.0** | Mapping objet ↔ SQLite |
| Validation | **Pydantic 2** | Schémas d'entrée/sortie typés |
| BDD | **SQLite** (`voyage.db`) | Stockage local, ~2000 trajets, users, billets |
| LLM | **Google Gemini 2.5 Flash** | Génération de réponses conversationnelles |
| Recherche web | **DuckDuckGo via `ddgs`** | Réponses temps réel (météo, prix, grèves…) |
| Email | **Brevo (ex-Sendinblue)** | Envoi mail transactionnel + pièce jointe |
| PDF | **ReportLab** | Génération du billet PDF A4 |
| Auth | JWT-like HMAC custom | Tokens email/mdp + Google OAuth |

### Frontend — `frontend/`

| Composant | Technologie | Rôle |
|---|---|---|
| UI | **React 18** (via Babel inline, pas de build) | Composants déclaratifs |
| Style | CSS custom (variables, dark/light/system) | Identité « Claude Design » |
| Auth Google | **Google Identity Services** | Sign-In Web, Web Client ID projet `sae2026` |
| HTTP | `fetch` natif | Appel direct au backend FastAPI |

---

## 4. Architecture

```
/Projet/SAE2/
├── backend/
│   ├── app/
│   │   ├── main.py             # Bootstrap FastAPI + CORS
│   │   ├── config.py           # Settings via .env (pydantic_settings)
│   │   ├── database.py         # Engine SQLAlchemy + get_db()
│   │   ├── models.py           # Tables : User, Trajet, Billet, Reclamation,
│   │   │                       #          ChatSession, ChatMessage, Admin
│   │   ├── schemas.py          # Pydantic in/out
│   │   ├── data/lieux.py       # Catalogue 117 lieux réels (40 aéroports, 29 gares…)
│   │   ├── routers/
│   │   │   ├── auth.py         # /auth/signup, /login, /google, /me
│   │   │   ├── trajets.py      # /trajets (recherche + filtres)
│   │   │   ├── billets.py      # /billets (CRUD + /mine + /access + modif/annuler)
│   │   │   ├── reclamations.py # /reclamations + /reclamations/{num_suivi}
│   │   │   ├── chat.py         # /chat/start /chat/message /chat/sessions/{...}
│   │   │   ├── admin.py        # /admin/stats /admin/billets /admin/reclamations
│   │   │   └── lieux.py        # /lieux (autocomplete)
│   │   └── services/
│   │       ├── chatbot.py      # ❤️ State machine + détection intent + filtres sécu
│   │       ├── gemini.py       # SDK Google Generative AI
│   │       ├── web_search.py   # ddgs wrapper + détection « should_search »
│   │       ├── billet_pdf.py   # ReportLab — billet PDF A4
│   │       ├── email.py        # Brevo HTML + PDF en pièce jointe
│   │       ├── identity.py     # verify_billet_identity (tolérant à l'inversion)
│   │       └── numeros.py      # Génération TRV-2026-XXXXXX
│   ├── seed.py                 # 1866+ trajets, 21 users, lieux réels
│   └── voyage.db
└── frontend/
    ├── index.html              # Charge Babel + Google Identity + tous les .jsx
    ├── api.js                  # window.VA_API.* (wrappers fetch)
    ├── voyage-shared.jsx       # Composants UI + helpers (PaxStepper, classes, total)
    ├── voyage-search.jsx       # Barre de recherche éditable + autocomplete
    ├── voyage-pages.jsx        # HomePage / ResultsPage / BookingPage / Confirm / MesBillets
    ├── voyage-chatbot-interactive.jsx  # Assistant IA — modales, sidebar, inactivité, rating
    ├── voyage-auth.jsx         # useAuth + AuthModal Google/email
    └── voyage-prototype-app.jsx # Routeur frontend + UserChip + NavInt
```

---

## 5. Concepts clés expliqués

### 5.1 LLM (Large Language Model) — Google Gemini 2.5 Flash

Modèle de langage qui prend du texte en entrée et produit du texte en sortie. On
l'utilise pour la **partie conversationnelle libre** du chatbot. Le modèle reçoit :

1. Un **SYSTEM_PROMPT** strict définissant son rôle, son périmètre, sa langue, ses
   refus (sujets dangereux, injections, hors-périmètre)
2. L'**historique** des messages de la conversation en cours (12 derniers messages)
3. Un éventuel **bloc CONTEXTE BILLET** (si l'utilisateur a déjà vérifié son
   identité — voir RAG ci-dessous)
4. Un éventuel **bloc web** (résultats DuckDuckGo formatés)
5. Le **message** utilisateur courant

Voir `backend/app/services/gemini.py`.

### 5.2 RAG (Retrieval-Augmented Generation)

RAG = on **récupère de l'information externe** (BDD, web, documents) avant
d'appeler le LLM, et on l'**injecte** dans le prompt pour qu'il réponde sur du
factuel et non d'hallucinations.

Dans Voyage Assistant on a **trois sources** « retrieval » :

#### 1. RAG documentaire vectoriel (CGV + billets) — `backend/app/services/rag.py`

Le bot dispose d'une base documentaire interne indexée par **embeddings sémantiques** :

- **CGV statiques** (`backend/data/cgv/`) : 3 documents Markdown couvrant
  annulation, bagages, remboursement & assurance. Indexés au démarrage du backend.
- **Billets utilisateur** : à chaque billet généré, son contenu textuel est
  automatiquement indexé avec un `meta.user_id` permettant un filtrage par
  utilisateur (un client ne voit que ses propres billets en retrieval).

**Pipeline d'indexation**
1. Lecture du document → découpage en chunks de ~400 mots avec recouvrement de 60
2. Embedding de chaque chunk via `models/gemini-embedding-001` (Gemini API)
3. Stockage `{doc_id, chunk_id, text, embedding, meta}` dans `data/rag_store.json`

**Pipeline de recherche** (à chaque message utilisateur)
1. Embedding de la requête (`task_type=RETRIEVAL_QUERY`)
2. Similarité **cosinus** vs tous les chunks indexés (filtrés par user_id + CGV)
3. Top-K (k=3) avec seuil de pertinence > 0.3
4. Injection en bloc `CONNAISSANCES DOCUMENTAIRES` dans le prompt Gemini

Exemple : *« je peux annuler 3 jours avant ? »* → embedding → match à 0.77 sur
l'article 1 des CGV annulation → injecté → réponse fiable avec frais de 15 €
mentionnés.

#### 2. BDD interne — `CONTEXTE BILLET`

Quand l'utilisateur a un billet vérifié en session, le bloc texte est injecté
sans embedding (lookup direct par ID). Permet à Gemini de répondre à *« à quelle
heure j'arrive ? »* ou *« combien j'ai payé ? »* avec les données de production.

#### 3. Web temps réel — DuckDuckGo

Via `ddgs` (multi-backend). Déclenché quand le message contient des marqueurs
(météo, visa, grève, à voir…). Les 6 premiers extraits sont injectés dans le
prompt avec la destination du billet en cours pour enrichir le contexte.

Les trois sources sont concaténées dans l'ordre **RAG → CONTEXTE BILLET → Web**
avant l'appel à Gemini. Le `tool_used` retourné par l'API indique quelle(s)
source(s) ont contribué : `rag`, `web_search`, `rag+web`, ou `gemini` (aucune).

### 5.2.bis Voix — Web Speech API (frontend)

Le chat supporte la voix **100 % côté navigateur**, sans dépendance backend :

- **Dictée** (entrée vocale) : `webkitSpeechRecognition` en `fr-FR`. Le bouton
  micro dans la zone de saisie déclenche la transcription en temps réel,
  remplissant l'input pour validation avant envoi.
- **Synthèse vocale** (sortie vocale) : `window.speechSynthesis` lit
  automatiquement les réponses du bot quand le toggle 🔊 est activé. Préférence
  persistée dans `localStorage`.

Choix techniques : Web Speech API plutôt que Whisper backend pour éviter
l'ajout d'une dépendance lourde (~150 MB de modèle) et garder le déploiement
léger. Limitation : nécessite Chrome / Edge (Firefox ne supporte pas encore
SpeechRecognition).

### 5.3 Intent detection & state machine

Le chatbot mixe **règles déterministes** (state machine) et **LLM**.

Pour les **actions sensibles** (modifier, annuler, réclamer), on ne laisse pas
Gemini agir : il halluciner ait. À la place, une **state machine** dans
`chatbot.py` gère un parcours guidé :

```
intent détecté → demande numéro billet → demande nom → demande prénom
              → demande date naissance → vérification identité (BDD)
              → exécution de l'action (modif réelle / réclamation créée / annulation)
              → mail + PDF envoyés
```

Pour les **questions libres**, on délègue à Gemini avec contexte enrichi (BDD +
web).

Voir `backend/app/services/chatbot.py`, fonction `_detect_intent` et la suite
des handlers `awaiting=…`.

### 5.4 OAuth Google + JWT custom

L'utilisateur peut se connecter :

- avec **Google** (One Tap / popup) — le frontend reçoit un `id_token` que le
  backend transmet à `auth/google` ; on extrait `email`, `given_name`,
  `family_name`, `picture`, `sub`
- avec **email/mot de passe** — hash PBKDF2 HMAC-SHA256 stocké en BDD

Dans les deux cas, le backend renvoie un **token HMAC** custom (signé avec
`AUTH_SECRET`) que le front stocke en localStorage et envoie en header
`Authorization: Bearer …`.

Voir `backend/app/services/auth.py` et `frontend/voyage-auth.jsx`.

### 5.5 PDF du billet

Généré dynamiquement par **ReportLab** (`billet_pdf.py`) à chaque réservation
ou modification. Format A4 avec bandeau orange Voyage Assistant, infos
voyageur, départ → arrivée, compagnie, classe, siège, prix, numéro de billet.

Le PDF est **encodé en base64** puis transmis à Brevo comme pièce jointe.

### 5.6 Sécurité du chatbot — couches empilées

| Couche | Mécanisme |
|---|---|
| Sanitization | Strip HTML tags, normalisation espaces, contrôle caractères de contrôle |
| Garde-fous explicites | Regex insultes / sujets dangereux / injections de prompt |
| Anti-extraction | Mention d'un n° billet sans identité → redirection vers procédure |
| Switch de flow | Changement de flow en plein parcours → confirmation explicite |
| SYSTEM_PROMPT | Périmètre strict + refus codifiés (Gemini ne sortira pas du cadre) |
| BDD | SQLAlchemy paramétré (anti-SQLi natif) |
| Rendu | React escape HTML par défaut (anti-XSS natif au rendu) |
| Identité | Triple vérification : numéro + nom + prénom + DOB stricte |

### 5.7 Persistance des sessions de chat

Chaque session a un `session_token` UUID stocké en BDD (`chat_sessions` table)
et en `localStorage` côté navigateur. À l'actualisation de la page, on rouvre
la même session via son token — l'historique est rechargé depuis le backend.

Une session est **terminée explicitement** par l'utilisateur (bouton *Mettre
fin à la conversation*) — il note alors l'expérience avec des étoiles + un
commentaire optionnel (table `chat_sessions.rating`, `feedback`). Après 2 min
d'inactivité, une modale propose de mettre fin.

---

## 6. Le chatbot pas à pas

### Flow « Modifier ma réservation »

```
USER : Modifier ma réservation
BOT  : Donnez-moi votre numéro de billet (TRV-2026-XXXXXX).
USER : TRV-2026-LKZF67
BOT  : Trouvé. Quel est votre nom de famille ?
USER : philipe
BOT  : Merci. Et votre prénom ?
USER : jean
BOT  : Et votre date de naissance (JJ/MM/AAAA) ?
USER : 10/01/2004
BOT  : [identité vérifiée] Voici 3 alternatives :
       [chip] 04/06 12:27 - Transavia - 220€
       [chip] 08/06 09:15 - Vueling - 187€
       [chip] 12/06 14:30 - EasyJet - 195€
USER : (clique sur la 1ère)
BOT  : C'est fait ! Votre billet est maintenant sur le vol Transavia du
       04/06/2026 à 12:27 (Paris Orly → Valence). Nouveau montant : 220 €.
       Un email avec le billet mis à jour vient de partir.
```

**Ce qui s'est réellement passé en backend** :
- `billet.trajet_id` mis à jour
- `billet.prix_paye` recalculé
- `ancien_trajet.places_dispo += 1`
- `nouveau_trajet.places_dispo -= 1`
- PDF regénéré avec les nouvelles infos
- Mail Brevo HTML + PDF envoyé au voyageur
- `last_billet_id` persisté en session → Gemini peut répondre aux questions
  contextuelles ensuite (« à quelle heure j'arrive ? », « météo à
  destination ? »)

### Autres flows

- **Mon voyage a un problème** → vérif identité → état retard réel → 3 options :
  *Demander une indemnité* (crée Reclamation type=retard) / *Annuler et me
  faire rembourser* (statut=annule, places restituées, mail) / *Rien, merci*
- **Faire une réclamation** → vérif identité → création Reclamation avec numéro
  de suivi unique
- **Poser une question** → Gemini + DuckDuckGo si pertinent

---

## 7. Difficultés rencontrées & solutions

### 7.1 DuckDuckGo bloqué — `202 Ratelimit`

**Problème initial.** On utilisait la librairie `duckduckgo-search 6.3.7`. À la
2e ou 3e requête de la journée, on recevait :

```
duckduckgo_search.exceptions.RatelimitException: 202 Ratelimit
```

DuckDuckGo HTML/Lite renvoie un challenge anti-bot après quelques appels depuis
la même IP. Inutilisable pour une démo où le prof va tester en live.

**Pistes explorées.**

1. **SearXNG** (instances publiques) — testé : `403` ou `429` la plupart du
   temps, et les instances tournent / disparaissent. Pas fiable.
2. **Tavily API** — payant (signup gratuit 1000 req/mois mais carte requise).
   Bonne piste de secours.
3. **Brave Search API** — idem, payant.
4. **Google Custom Search** — quota trop strict et résultats moins riches pour
   FR.
5. **Gemini Grounding (Google Search intégré)** — n'existait que pour
   `gemini-1.5-pro` avec le param `google_search_retrieval` ; non supporté par
   `gemini-2.5-flash` ni par notre SDK `google-generativeai 0.8.5`.

**Solution adoptée.** On est passé à **`ddgs` 9.14.2** (fork actif de
`duckduckgo-search`). Ce qui a fait la différence :

- **Multi-backend rotation** — `ddgs` essaie automatiquement plusieurs backends
  (`auto`, `html`, `lite`, `duckduckgo`) et bascule si l'un est rate-limité
- **User-Agent rotatif** et requêtes plus discrètes
- Plus de `202 Ratelimit` après 50+ requêtes consécutives

Le wrapper `web_search.py` configure les backends explicitement :

```python
DDGS().text(query, max_results=6, region="fr-fr",
            safesearch="moderate", backend="auto")
```

**Bonus.** On enrichit aussi la requête avec la destination quand l'utilisateur
a un billet vérifié : *« quel temps fait-il ? »* → on cherche
*« quel temps fait-il Valence (Espagne) Manises »* — sinon DDG retourne du bruit.

### 7.2 Identité — Google ne fournit pas la date de naissance

**Problème.** Au flow chatbot de vérification d'identité, on compare nom +
prénom + date de naissance avec la BDD. Or **Google OAuth ne donne pas la
date de naissance** dans le scope standard `openid email profile` — il
faudrait `https://www.googleapis.com/auth/user.birthday.read` + appel à
People API, intrusif et souvent vide.

À l'inscription via Google, on mettait donc une **date placeholder**
`2000-01-01`. Conséquence : le user achète un billet en saisissant sa vraie
date au formulaire, mais la BDD garde le placeholder → la vérif chatbot
échoue.

**Solution.** Dans `routers/billets.py:create_billet`, si le user existe
déjà à la résa, on **met à jour ses infos** avec celles du formulaire (nom,
prénom, date de naissance, téléphone). Le formulaire de réservation devient
*source de vérité* pour le voyageur réel.

En parallèle, on a rendu la vérif chatbot **tolérante à l'inversion
nom ↔ prénom** (cas fréquent où Google met `given_name`=Jean,
`family_name`=Philipe alors que l'utilisateur considère Philipe comme son
nom — `identity.py`).

### 7.3 Hallucinations sur les actions (avant durcissement)

**Problème.** Quand l'utilisateur tapait *« oui je confirme »* après une
proposition de modification, Gemini répondait *« Votre réservation est
confirmée ! »* — alors qu'on n'avait rien modifié en BDD. Pure
hallucination, donc aucun mail réel, billet inchangé.

**Solution.** Séparation nette **state machine ↔ LLM** :
- Toute action sur la BDD passe par la state machine
- Gemini n'intervient que pour les réponses textuelles, jamais pour
  l'exécution
- Le SYSTEM_PROMPT lui interdit explicitement de prétendre avoir effectué
  une action

### 7.4 Sessions chat perdues au F5

**Problème.** Une actualisation de page créait une nouvelle session, l'ancien
échange était perdu côté UI.

**Solution.** On stocke le `session_token` en `localStorage`. Au montage du
composant chat, on tente d'abord de rouvrir cette session via
`/chat/{token}/history` ; si elle existe encore en BDD, on rejoue l'historique.

### 7.5 Brevo bloque l'IP origine

**Problème.** Après avoir configuré la clé API Brevo, premier envoi → `401
Unauthorized` avec le message *« we have detected you are using an
unrecognised IP address »*.

**Solution.** Brevo a une protection « Authorized IPs » dans
*Security → Authorised IPs*. On a désactivé la restriction (toggle global),
ce qui suffit pour le dev / la démo.

### 7.6 Identité case-sensitive

Vite réglé : `verify_billet_identity` compare en `.lower()` et tolère
l'inversion nom/prénom.

---

## 8. Installation & lancement

### Prérequis
- Python 3.12+
- (Optionnel) Compte Brevo pour les vrais envois mail
- Clé API Gemini (compte sae2026)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurer .env :
cp .env.example .env  # à créer si besoin
# Remplir GEMINI_API_KEY, BREVO_API_KEY, BREVO_SENDER_EMAIL

# (Re)peupler la BDD si besoin
python seed.py

# Lancer
uvicorn app.main:app --port 8000 --reload
```

### Frontend

```bash
cd frontend
python3 -m http.server 5173
# Ouvrir http://localhost:5173/
```

### Comptes de test

- `camille@test.fr` / `test1234` (user standard)
- `admin@voyage.local` / `changeme` (admin)

---

## 9. Endpoints API

### Auth
- `POST /auth/signup` — création compte email/mdp
- `POST /auth/login` — connexion
- `POST /auth/google` — connexion Google OAuth
- `GET  /auth/me` — utilisateur courant

### Voyage
- `GET  /trajets?depart=&arrivee=&type=&date=` — recherche cascade
- `GET  /trajets/{id}` — détail d'un trajet
- `GET  /lieux?q=` — autocomplete (117 lieux)

### Billets
- `POST   /billets` — création + mail + PDF
- `GET    /billets/mine` — historique du user connecté
- `POST   /billets/access` — accès par numéro + identité (sans login)
- `POST   /billets/{num}/modifier` — modification
- `POST   /billets/{num}/annuler` — annulation

### Réclamations
- `POST /reclamations` — création
- `GET  /reclamations/{num_suivi}` — suivi

### Chat
- `POST   /chat/start` — démarre / reprend une session
- `POST   /chat/message` — envoie un message à l'assistant
- `GET    /chat/sessions` — liste des sessions du user (auth)
- `GET    /chat/{token}/history` — messages d'une session
- `DELETE /chat/sessions/{token}` — suppression d'une session
- `POST   /chat/sessions/{token}/end` — fin avec rating + feedback

### Admin
- `POST /admin/login`
- `GET  /admin/stats`, `/admin/billets`, `/admin/reclamations`

---

## 10. Tests de robustesse

Le chatbot a été *red-teamé* sur :

| Attaque | Résultat |
|---|---|
| Insultes (`connard`, `ferme ta gueule`) | Désescalade fixe |
| Injection prompt (`ignore previous instructions`, `###SYSTEM`) | Refus codifié |
| Sujet dangereux (`fabriquer une bombe`) | Refus poli ciblé |
| Hors-sujet (`écris-moi du Python`) | Refus via SYSTEM_PROMPT |
| Vol d'infos billet sans identité | Redirection vers procédure |
| XSS (`<script>alert(1)</script>`) | Strip HTML + escape React |
| SQL injection (`'; DROP TABLE`) | Refusé via paramétrage SQLAlchemy |
| Empty / whitespace / 1 char | Demande de reformulation |
| Switch de flow en plein parcours | Confirmation explicite *Abandonner / Continuer* |
| Message ultra-long (>4000 chars) | Troncature transparente |
| Inversion nom/prénom | Tolérée par `verify_billet_identity` |

---

## Crédits

Projet réalisé par **Christian Angela Elako** dans le cadre de la SAE2 BUT3
(Mr FAYE & Mme AZZAG), promotion 2025-2026.

Stack & implémentation : Python (FastAPI / SQLAlchemy / ReportLab), React,
Google Gemini, DuckDuckGo (ddgs), Brevo, Google OAuth.
