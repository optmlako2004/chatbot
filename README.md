# Chatbot RAG Finance — SAE2 BUT3

Chatbot spécialisé en **éducation financière**, basé sur :
- une approche **RAG** (Retrieval-Augmented Generation) sur des documents officiels (Banque de France, INC),
- un agent IA capable de **chercher sur Internet** quand la question concerne une info récente (taux, actualité). ← *bonus du sujet*

---

## 🧠 Architecture

```
                    ┌──────────────────────────────┐
   Question utilisateur ───────────▶│  Agent LangGraph (llama3.2) │
                    │                              │
                    │  Choisit dynamiquement       │
                    │  l'outil approprié :         │
                    │                              │
                    │   ┌──── rag_finance ─────┐  │
                    │   │  FAISS (PDFs BdF/INC)│  │
                    │   │  embeddings gte-small│  │
                    │   └──────────────────────┘  │
                    │                              │
                    │   ┌──── web_search ──────┐  │
                    │   │  DuckDuckGo (récent) │  │ ← BONUS
                    │   └──────────────────────┘  │
                    │                              │
                    │  Mémoire conversationnelle   │
                    │  par thread_id (LangGraph)   │
                    └──────────────────────────────┘
                                 ▼
                          Réponse en français
```

---

## 📦 Stack technique et justifications

| Brique | Outil choisi | Pourquoi |
|---|---|---|
| **LLM** | `llama3.2:3b` via **Ollama** | Tourne en local, gratuit, **supporte le tool calling natif** (indispensable pour l'agent). On a testé `llama3:latest` mais la v1 ne supporte pas les tools (erreur 400 d'Ollama). |
| **Framework agent** | **LangGraph** (`create_react_agent`) | Imposé par le prof (LangChain), et LangGraph est l'évolution moderne de LangChain pour les agents. Plus fiable que ReAct par prompt textuel : utilise le tool calling natif du LLM → pas d'hallucinations sur le format. |
| **Base vectorielle** | **FAISS** (local, fichier) | Standard, rapide, pas de serveur à déployer. L'index existe déjà (`faiss_index/`, généré en TP). |
| **Embeddings** | `thenlper/gte-small` (HuggingFace) | C'est le modèle utilisé pour générer l'index existant — on **doit** garder le même sinon les vecteurs sont incompatibles. Petit (130 MB), rapide, multilingue correct. |
| **Recherche web** | **DuckDuckGo** (`ddgs`) | Pas de clé API requise (Tavily / SerpAPI / Bing en demandent). Cité explicitement dans le cours comme option n°1. |
| **Mémoire** | `InMemorySaver` de LangGraph | Permet à l'agent de se souvenir des échanges précédents dans une même session (`thread_id`). Pour la prod : remplacer par un checkpointer SQLite. |
| **API** | **FastAPI** | Async, doc auto (`/docs`), validation Pydantic. Standard moderne, mieux que Flask. |
| **UI de test** | **Gradio** | Juste pour valider visuellement le bot. L'UI finale sera en **React** (cf. `INTEGRATION_REACT.md`). |
| **Variables d'env** | `python-dotenv` (`.env`) | Garde les secrets hors du code et hors de git. |

---

## 🗂️ Structure du projet

```
SAE2/
├── chatbot.py                  ← Module principal (agent + outils + mémoire)
├── ui_test.py                  ← Interface Gradio de TEST (pas la finale)
├── api.py                      ← API REST FastAPI pour le frontend React
├── faiss_index/                ← Index vectoriel (gitignoré, regénérable)
├── finance/, *.pdf             ← Sources de données pour le RAG
├── .env                        ← Secrets (gitignoré)
├── 02_chatbot_rag_web.ipynb    ← Notebook de démo / debug
├── README.md                   ← Tu es ici
└── INTEGRATION_REACT.md        ← Guide pour brancher le bot dans le React
```

---

## 🚀 Lancement

### Pré-requis

```bash
# 1. Ollama installé + serveur lancé
ollama serve  # à laisser tourner dans un terminal
ollama pull llama3.2:3b

# 2. Venv Python + dépendances
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Trois manières de tester le bot

**A. CLI (le plus rapide)**
```bash
python chatbot.py
> C'est quoi un livret A ?
> Et son plafond ?
> q
```

**B. UI Gradio (visuel, dans le navigateur)**
```bash
python ui_test.py
# ouvre http://localhost:7860
```

**C. API REST (pour brancher le React)**
```bash
uvicorn api:app --reload --port 8000
# doc interactive : http://localhost:8000/docs
```

---

## 🔍 Comment l'agent choisit ses outils

L'agent regarde la **docstring** de chaque outil et le **system prompt**. Concrètement :

| Question utilisateur | Outil choisi | Pourquoi |
|---|---|---|
| « C'est quoi un Livret A ? » | `rag_finance` | Définition générale → cherche dans les PDFs BdF/INC |
| « Quel est le taux du Livret A en 2026 ? » | `web_search` | Chiffre récent → DuckDuckGo |
| « Comment cuisiner ? » | (aucun) | Hors finance → l'agent refuse poliment |

Tu peux modifier ce comportement en éditant `SYSTEM_PROMPT` dans `chatbot.py`.

---

## 🧪 Concepts clés (pour le rapport)

### RAG (Retrieval-Augmented Generation)
On **augmente** le LLM avec des connaissances externes. Au lieu de demander au modèle de répondre de mémoire (risque d'hallucination), on lui fournit les passages pertinents extraits des PDFs. Pipeline : question → embedding → recherche similarité dans FAISS → top-K passages → injection dans le prompt → réponse.

### Embeddings
Transforment du texte en vecteurs numériques. Deux textes sémantiquement proches → vecteurs proches. C'est ce qui permet la recherche par similarité dans FAISS.

### Tool calling natif vs ReAct textuel
- **ReAct textuel** (`Action: tool_name\nAction Input: ...`) : le LLM doit générer du texte structuré → fragile sur les petits modèles open-source (parsing failures, boucles).
- **Tool calling natif** (utilisé ici) : le LLM renvoie directement un objet JSON structuré côté API Ollama → 100% fiable. Nécessite un modèle entraîné pour (llama3.1+, llama3.2+, mistral-nemo, qwen2.5...).

### Mémoire conversationnelle
LangGraph maintient l'historique des messages par `thread_id`. Côté client, il suffit de renvoyer le même `thread_id` pour que le bot se souvienne des échanges. Deux utilisateurs = deux `thread_id` différents = pas de fuite d'historique.

---

## 🔮 Améliorations possibles

- [ ] Mémoire persistante (SQLite checkpointer) au lieu de RAM
- [ ] BDD SQLAlchemy pour stocker les utilisateurs + historiques
- [ ] Réindexer FAISS avec un meilleur splitter (les chunks actuels sont moyens)
- [ ] Streaming des réponses (token par token) pour une UX plus fluide
- [ ] Switch dynamique Ollama / Gemini via variable d'env (pour le déploiement HF Spaces qui n'a pas Ollama)
- [ ] Voix avec Whisper (option du sujet)
