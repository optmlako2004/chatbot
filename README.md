# Chatbot RAG Finance — SAE2 BUT3

Chatbot spécialisé en éducation financière, basé sur une approche RAG (Retrieval-Augmented Generation) avec recherche web en complément.

## Stack

- **LLM** : Ollama (llama3 en local) / Gemini ou OpenRouter en prod
- **RAG** : LangChain + FAISS + embeddings HuggingFace (`thenlper/gte-small`)
- **Recherche web** : DuckDuckGo (via LangChain agent)
- **Frontend** : Gradio
- **Base de données** : SQLAlchemy + SQLite (sessions / historique)
- **Déploiement** : HuggingFace Spaces

## Sources de données

- Guide Éducation Financière — INC
- Banque de France — Éducation Financière
- 2 PDFs finance complémentaires

## Lancement local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Lancer Ollama dans un autre terminal
ollama serve
ollama pull llama3

# Lancer l'app
python app.py
```
