# Guide d'intégration du chatbot dans l'app React

Ce guide est pour le membre de l'équipe qui développe le **frontend React**. Il explique comment appeler l'API du chatbot depuis React et afficher les réponses.

---

## 1. Démarrer l'API en local

Dans un terminal côté chatbot :

```bash
cd SAE2
source .venv/bin/activate
uvicorn api:app --reload --port 8000
```

L'API est alors disponible sur `http://localhost:8000`. La doc interactive (Swagger) est sur `http://localhost:8000/docs` — pratique pour tester les endpoints à la souris.

> ⚠️ **Ollama doit aussi tourner** (`ollama serve` dans un autre terminal). Si Ollama est éteint, l'API renverra une erreur 500.

---

## 2. Endpoints disponibles

### `POST /chat`

Envoie un message au bot et reçoit la réponse.

**Requête** :
```json
{
  "message": "C'est quoi un livret A ?",
  "thread_id": "user-42"
}
```

- `message` : texte de la question (obligatoire).
- `thread_id` : identifiant de conversation (optionnel). Si absent, l'API en génère un nouveau et le renvoie. **Renvoie toujours le même `thread_id` pour conserver l'historique d'un utilisateur.**

**Réponse** :
```json
{
  "answer": "Un Livret A est un produit d'épargne réglementé...",
  "tools_used": ["rag_finance"],
  "thread_id": "user-42"
}
```

- `answer` : la réponse en français.
- `tools_used` : liste des outils que l'agent a appelés. Permet d'afficher un badge « cherché sur le web » dans l'UI.
- `thread_id` : à conserver côté client.

### `POST /chat/reset`

Renvoie un nouveau `thread_id` → la conversation repart de zéro.

```json
{ "thread_id": "nouveau-uuid-ici" }
```

### `GET /health`

Vérifie que le bot est chargé. À utiliser pour afficher un indicateur de statut.

---

## 3. Code React minimal

### a) Hook `useChat` (gestion d'état + appels API)

```javascript
// src/hooks/useChat.js
import { useState, useRef } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const threadId = useRef(null); // persiste entre les renders

  async function sendMessage(text) {
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          thread_id: threadId.current,
        }),
      });
      const data = await res.json();
      threadId.current = data.thread_id;

      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: data.answer,
          toolsUsed: data.tools_used,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "❌ Erreur réseau.", error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function resetConversation() {
    const res = await fetch(`${API_URL}/chat/reset`, { method: "POST" });
    const data = await res.json();
    threadId.current = data.thread_id;
    setMessages([]);
  }

  return { messages, loading, sendMessage, resetConversation };
}
```

### b) Composant `Chat` (UI)

```jsx
// src/components/Chat.jsx
import { useState } from "react";
import { useChat } from "../hooks/useChat";

export default function Chat() {
  const { messages, loading, sendMessage, resetConversation } = useChat();
  const [input, setInput] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    sendMessage(input);
    setInput("");
  }

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            {m.toolsUsed?.includes("web_search") && (
              <span className="badge">🌐 web</span>
            )}
            {m.toolsUsed?.includes("rag_finance") && (
              <span className="badge">📚 base finance</span>
            )}
            <p>{m.content}</p>
          </div>
        ))}
        {loading && <div className="message assistant">⏳ ...</div>}
      </div>

      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Pose ta question finance..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>Envoyer</button>
        <button type="button" onClick={resetConversation}>🔄</button>
      </form>
    </div>
  );
}
```

### c) Variable d'environnement (Vite)

Dans le projet React, créer `.env` :

```
VITE_API_URL=http://localhost:8000
```

En prod (quand l'API sera déployée), remplacer par l'URL réelle.

---

## 4. CORS — ce qui est déjà configuré

L'API autorise déjà les origines :
- `http://localhost:3000` (Create React App)
- `http://localhost:5173` (Vite)

Si tu déploies le React sur un autre domaine, il faut **ajouter l'URL** dans `api.py` :

```python
allow_origins=[
    "http://localhost:5173",
    "https://ton-app-en-prod.com",  # ← à ajouter
],
```

---

## 5. Streaming (optionnel, pour plus tard)

L'API actuelle renvoie la réponse complète d'un coup. Pour afficher la réponse token par token (style ChatGPT), il faudra :
1. Modifier `api.py` pour streamer (SSE ou WebSocket)
2. Côté React, utiliser `EventSource` ou un fetch en stream

À voir si on a le temps — pas critique pour la note.

---

## 6. Erreurs courantes

| Erreur | Cause | Fix |
|---|---|---|
| `CORS blocked` | Origine pas dans `allow_origins` | Ajouter ton URL dans `api.py` |
| `Failed to fetch` | API pas lancée | `uvicorn api:app --reload --port 8000` |
| Réponse `500` | Ollama pas lancé | `ollama serve` dans un autre terminal |
| Réponse très lente (10+ sec) | Premier appel : chargement embeddings + index | Normal au démarrage. Les appels suivants sont rapides (~2-5s). |
| Réponse vide / bot qui répond n'importe quoi | Modèle trop petit | Tester avec `llama3.1:8b` ou `mistral-nemo` (cf. `OLLAMA_MODEL` dans `.env`) |

---

## 7. Checklist intégration

- [ ] API lancée sur `localhost:8000`
- [ ] Test `curl http://localhost:8000/health` → renvoie `{"status":"ok",...}`
- [ ] Hook `useChat` copié et adapté au style du projet
- [ ] Composant `Chat` intégré dans une page
- [ ] `.env` côté React avec `VITE_API_URL`
- [ ] Test : envoyer un message, vérifier qu'on reçoit une réponse
- [ ] Test : envoyer 2 messages liés ("livret A ?" puis "et son plafond ?") → vérifier que le bot se souvient
- [ ] Test : bouton reset → nouvelle conversation OK
