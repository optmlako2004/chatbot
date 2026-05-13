# Frontend Chatbot Finance — React + Vite + Tailwind

UI du chatbot RAG finance. Branche `frontend` du dépôt.

## Stack

- **Vite** + **React 18** + **TypeScript** : tooling moderne, build rapide, déploiement Vercel one-click
- **React Router** : navigation login/signup/chat
- **Tailwind CSS** : styling utilitaire, pas de fichier CSS à maintenir
- **Fetch natif** (pas d'axios) avec wrapper auth dans `src/api/client.ts`

## Démarrage

```bash
# 1. Installer les dépendances
cd frontend
npm install

# 2. Configurer l'URL de l'API
cp .env.example .env
# (par défaut : http://localhost:8000)

# 3. Démarrer le backend dans un autre terminal :
#    cd .. && uvicorn api:app --reload --port 8000

# 4. Démarrer le frontend
npm run dev
# → http://localhost:5173
```

## Comptes de test (créés par `seed.py` côté backend)

| Email | Mot de passe |
|---|---|
| alice@test.com | alice123 |
| bob@test.com | bob123 |

Tu peux aussi cliquer sur "Continuer sans compte" → mode anonyme (UUID en localStorage).

## Architecture

```
src/
├── main.tsx                ← Bootstrap, monte l'AuthProvider + Router
├── App.tsx                 ← Routes
├── api/
│   ├── client.ts           ← Fetch wrapper (auth automatique, parsing JSON)
│   └── types.ts            ← Types TS qui matchent les schémas Pydantic
├── auth/
│   └── AuthContext.tsx     ← user state global + login/signup/logout
├── pages/
│   ├── Login.tsx           ← Formulaire email/mot de passe + bouton Google (stub)
│   ├── Signup.tsx          ← Inscription
│   └── Chat.tsx            ← Page principale (sidebar + chat)
├── components/
│   ├── Sidebar.tsx         ← Liste des conversations + bouton "+ Nouvelle"
│   ├── MessageBubble.tsx   ← Bulle user / assistant + badges outils
│   ├── ChatInput.tsx       ← Textarea + bouton envoyer (Entrée pour envoyer)
│   ├── FeedbackModal.tsx   ← Note 5 étoiles + commentaire
│   └── InactivityModal.tsx ← Pop-up "vous êtes toujours là ?"
└── hooks/
    └── useInactivity.ts    ← Timer + listeners souris/clavier
```

## Comportements implémentés

| Comportement | Implémentation |
|---|---|
| Auth email/mot de passe | `AuthContext` + endpoints `/auth/signup`, `/auth/login` |
| Auth Google | Bouton désactivé (`disabled`), prêt à brancher quand clés OAuth dispo |
| Mode anonyme | UUID en `localStorage` envoyé via `X-Anonymous-Id` |
| Persistance JWT | Token dans `localStorage`, injecté en `Authorization: Bearer ...` |
| Sidebar conversations | `GET /sessions`, refresh quand on crée/supprime/edit |
| **Survie au refresh** | À l'ouverture d'une conversation, `GET /sessions/{id}/messages` recharge l'historique |
| **Inactivité 2 min** | Hook `useInactivity` écoute mousemove/click/key → modal "Continuer / Terminer" |
| Fin de conversation | `POST /sessions/{id}/end` → message farewell injecté → modal feedback |
| Note + commentaire | 5 étoiles + textarea optionnel → `POST /sessions/{id}/feedback` |
| Badges outils utilisés | "📚 Base finance" (rag) ou "🌐 Recherche web" (DuckDuckGo) sur les bulles assistant |

## Build production

```bash
npm run build
# → dist/ contient les fichiers à déployer (Vercel, Netlify, S3...)
```

## Déploiement Vercel

1. `cd frontend`
2. `vercel` (ou import du repo via le dashboard, root = `frontend`)
3. Variable d'environnement : `VITE_API_URL=https://ton-api-en-prod.com`
