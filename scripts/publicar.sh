#!/bin/sh
# Publica o mapa no GitHub Pages: monta _site/ e envia para a branch gh-pages.
# Uso: sh scripts/publicar.sh
set -e
cd "$(dirname "$0")/.."
python3 scripts/site.py
cd _site
git init -q -b gh-pages
git add -A
git commit -q -m "Publica o mapa"
git push -q -f "$(git -C .. remote get-url origin)" gh-pages
echo "publicado"
