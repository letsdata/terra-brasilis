"""Monta _site/ para o GitHub Pages a partir de web/: copia a página e os dados e põe no
topo do index.html o doctype e as etiquetas de prévia de link (X, WhatsApp, LinkedIn).

Uso: python3 scripts/site.py [endereço público]
"""
import shutil, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = RAIZ / "_site"
URL = (sys.argv[1] if len(sys.argv) > 1 else "https://letsdata.github.io/terra-brasilis/").rstrip("/") + "/"

TITULO = "Terra Brasilis"
DESC = ("O Brasil como jogo de estratégia: 15.790 hexágonos, 5.571 municípios e dados públicos "
        "do IBGE, MapBiomas, ANEEL e outros.")

CABECA = f"""<!doctype html>
<html lang="pt-BR">
<meta name="description" content="{DESC}">
<meta property="og:type" content="website">
<meta property="og:title" content="{TITULO}">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="{URL}capa.png">
<meta property="og:image:width" content="1600">
<meta property="og:image:height" content="1000">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{TITULO}">
<meta name="twitter:description" content="{DESC}">
<meta name="twitter:image" content="{URL}capa.png">
"""


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    shutil.copytree(RAIZ / "web", SITE)
    shutil.copy(RAIZ / "divulgacao/mapa-terreno.png", SITE / "capa.png")
    html = (RAIZ / "web/index.html").read_text()
    (SITE / "index.html").write_text(CABECA + html)
    (SITE / ".nojekyll").write_text("")
    print("ok", SITE)


if __name__ == "__main__":
    main()
