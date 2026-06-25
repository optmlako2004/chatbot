#!/usr/bin/env bash
# Déploiement de Voyage Assistant sur Hugging Face Spaces.
# Le Space est un dépôt git séparé ; ce script y copie le code et pousse,
# ce qui déclenche le build Docker automatique (~10-15 min, onglet Logs).
#
# Usage :
#   HF_TOKEN=hf_xxx ./deploy.sh
# Variables optionnelles : HF_USER (défaut: optimalako), HF_SPACE (défaut: voyage-assistant)

set -euo pipefail

HF_USER="${HF_USER:-optimalako}"
HF_SPACE="${HF_SPACE:-voyage-assistant}"
SRC="$(cd "$(dirname "$0")" && pwd)"

if [ -z "${HF_TOKEN:-}" ]; then
  echo "ERREUR : exporte ton token HF Write d'abord -> HF_TOKEN=hf_xxx ./deploy.sh" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo ">> Clonage du Space $HF_USER/$HF_SPACE ..."
git clone "https://oauth2:${HF_TOKEN}@huggingface.co/spaces/${HF_USER}/${HF_SPACE}" "$TMP/space"

echo ">> Synchronisation des fichiers ..."
# README du Space (en-tête YAML HF) + image + code
cp "$SRC/SPACE_README.md" "$TMP/space/README.md"
cp "$SRC/Dockerfile" "$TMP/space/"
cp "$SRC/.dockerignore" "$TMP/space/" 2>/dev/null || true
rsync -a --delete \
  --exclude '__pycache__' --exclude '*.pyc' --exclude '.venv' \
  --exclude 'voyage.db' --exclude '*.db' --exclude 'faiss_index' \
  --exclude 'data/rag_store.json' --exclude 'data/image_cache.json' \
  "$SRC/backend/" "$TMP/space/backend/"
rsync -a --delete "$SRC/frontend/" "$TMP/space/frontend/"

cd "$TMP/space"
git add -A
if git diff --cached --quiet; then
  echo ">> Aucun changement à déployer."
  exit 0
fi
git -c user.email="deploy@voyage" -c user.name="deploy" commit -m "Déploiement : multilingue FR/EN/ES + pièce jointe + recherche conversationnelle"
echo ">> Push vers le Space (déclenche le build) ..."
git push
echo ">> OK. Suis le build : https://huggingface.co/spaces/${HF_USER}/${HF_SPACE}  (onglet Logs)"
echo ">> App : https://${HF_USER}-${HF_SPACE}.hf.space"
