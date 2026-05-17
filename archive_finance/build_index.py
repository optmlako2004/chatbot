"""
Reconstruit l'index FAISS à partir des PDFs du dossier courant.

Pourquoi ce script ?
- L'index FAISS est gitignoré (regénérable, ~Mo de binaire).
- Quand un coéquipier clone le repo, il doit pouvoir reconstruire l'index
  en une commande, sans rejouer tout le notebook.

Usage :
    python build_index.py
"""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

ROOT = Path(__file__).parent
PDF_PATTERNS = ["*.pdf", "finance/*.pdf"]
EXCLUDE = {"SAE_2__BUT_3.pdf"}  # le sujet du projet, pas une source de connaissances

EMBEDDING_MODEL = "thenlper/gte-small"
INDEX_DIR = ROOT / "faiss_index"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 51


def collect_pdfs() -> list[Path]:
    pdfs = []
    for pattern in PDF_PATTERNS:
        pdfs.extend(ROOT.glob(pattern))
    return [p for p in pdfs if p.name not in EXCLUDE]


def main():
    pdfs = collect_pdfs()
    if not pdfs:
        print("❌ Aucun PDF trouvé. Place tes PDFs à la racine ou dans finance/.")
        return

    print(f"📚 PDFs trouvés ({len(pdfs)}):")
    for p in pdfs:
        print(f"   - {p.relative_to(ROOT)}")

    print("\n📄 Chargement et extraction du texte...")
    docs = []
    for pdf in pdfs:
        loader = PyPDFLoader(str(pdf))
        docs.extend(loader.load())
    print(f"   {len(docs)} pages chargées.")

    print(f"\n✂️  Découpage en chunks (taille={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    print(f"   {len(chunks)} chunks générés.")

    print(f"\n🧠 Calcul des embeddings ({EMBEDDING_MODEL}, sur CPU)...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    print("\n💾 Construction de l'index FAISS...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    INDEX_DIR.mkdir(exist_ok=True)
    vectorstore.save_local(str(INDEX_DIR))

    print(f"\n✅ Index sauvegardé dans {INDEX_DIR}/")
    print(f"   {vectorstore.index.ntotal} vecteurs ({vectorstore.index.d} dim)")


if __name__ == "__main__":
    main()
