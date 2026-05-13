# Frontend Chatbot Finance — React + Vite + Tailwind

Le chatbot est packagé comme un **widget intégrable** (`<ChatbotWidget />`). Le projet contient en plus une fausse app finance pour démontrer l'intégration.

## Architecture

```
src/
├── widget/                      ← LE WIDGET (à intégrer dans l'app du coéquipier)
│   ├── ChatbotWidget.tsx        ← point d'entrée — UNE LIGNE à ajouter
│   ├── ChatBubble.tsx           ← bouton flottant en bas à droite
│   ├── ChatPopup.tsx            ← popup (header + vues liste/chat)
│   ├── SessionList.tsx          ← liste des conversations
│   └── ChatView.tsx             ← messages + input + inactivité + feedback
│
├── components/                  ← composants réutilisés par le widget
│   ├── MessageBubble.tsx        ← bulle user/assistant + badges outils
│   ├── ChatInput.tsx            ← textarea avec Entrée
│   ├── FeedbackModal.tsx        ← modal note 5⭐
│   └── InactivityModal.tsx      ← modal "vous êtes toujours là ?"
│
├── auth/AuthContext.tsx         ← user state + login/signup/logout
├── api/                         ← client HTTP
│   ├── client.ts                ← fetch wrapper (auth automatique)
│   └── types.ts                 ← types TS qui matchent les Pydantic
│
├── pages/                       ← pages auth (Login, Signup)
├── demo-app/DemoApp.tsx         ← FAKE app finance (à remplacer par l'app du coéquipier)
└── App.tsx                      ← Routes : / → DemoApp, /login, /signup
```

## Démarrage

```bash
# Backend (autre terminal)
cd ..
.venv/bin/uvicorn api:app --reload --port 8000

# Frontend
cd frontend
npm install
cp .env.example .env       # VITE_API_URL=http://localhost:8000
npm run dev
# → http://localhost:5173
```

## Pour le coéquipier qui développe l'app finance

**Intégrer le chatbot dans ton app prend 2 lignes** :

```tsx
import ChatbotWidget from "./widget/ChatbotWidget";

function App() {
  return (
    <>
      <TonAppFinance />
      <ChatbotWidget />   {/* 👈 c'est tout */}
    </>
  );
}
```

### Prérequis côté ton app
1. Le widget utilise `AuthContext` et `BrowserRouter` → garde-les autour (cf. `src/main.tsx`).
2. Tailwind doit être configuré (`tailwind.config.js` doit inclure `src/widget/**`).
3. Variable d'env : `VITE_API_URL` pointant vers le backend FastAPI.

### Comportement du widget
- Bouton flottant rond en bas à droite (`bottom-5 right-5`).
- Clic → popup 400×600px.
- Liste des conversations + bouton "Nouvelle question".
- Auth :
  - Si user connecté (JWT) → ses conversations sont sauvées en BDD.
  - Sinon → mode anonyme (UUID localStorage), un bandeau invite à se connecter.
- Persistance : les messages survivent au refresh (rechargés depuis l'API).
- Inactivité 2 min → modal "Continuer / Terminer".
- Fin de conversation → message farewell + modal feedback (5⭐ + commentaire).

### Personnalisation rapide
| Élément | Fichier | Ligne |
|---|---|---|
| Position du bouton | `widget/ChatBubble.tsx` | `fixed bottom-5 right-5` |
| Couleur du bouton | `tailwind.config.js` | `brand.600` |
| Délai inactivité | `widget/ChatView.tsx` | `INACTIVITY_MS` |
| Texte du farewell | côté backend `chatbot.py` | endpoint `/end` |
| Texte du popup header | `widget/ChatPopup.tsx` | `<h2>Assistant Finance</h2>` |

## Pages auth disponibles

- `/login` — formulaire email/mot de passe + bouton Google (désactivé tant que pas de clés OAuth)
- `/signup` — inscription
- `/` — la fake app finance avec le widget

## Comptes de test (créés par `seed.py` côté backend)

| Email | Mot de passe |
|---|---|
| alice@test.com | alice123 |
| bob@test.com | bob123 |

Ou clique sur la bulle directement → mode anonyme.

## Build production

```bash
npm run build       # → dist/
npm run preview     # test du build
```

Déploiement Vercel : import du repo, root = `frontend`, variable `VITE_API_URL=https://ton-backend.com`.
