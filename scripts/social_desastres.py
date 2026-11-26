"""Desastres com reconhecimento federal por município, a partir da base consolidada do
Atlas Digital de Desastres no Brasil (MIDR / Defesa Civil, registros do S2iD).

Uso: .venv/bin/python scripts/social_desastres.py  ->  dados/desastres.csv
Arquivo bruto: dados/brutos/social/atlas_desastres/BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv
(https://atlasdigital.mdr.gov.br/arquivos/2026/BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv)
"""
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "dados" / "brutos" / "social" / "atlas_desastres"
NOME = "BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv"
URL = f"https://atlasdigital.mdr.gov.br/arquivos/2026/{NOME}"
ANO_INICIO, ANO_FIM = 2016, 2025  # últimos 10 anos completos da base

# Agrupamento pela tipologia do Atlas (COBRADE)
GRUPOS = {
    "Estiagem e Seca": "seca_estiagem",                  # 14110, 14120
    "Inundações": "inundacao_enxurrada_alagamento",      # 12100
    "Enxurradas": "inundacao_enxurrada_alagamento",      # 12200
    "Alagamentos": "inundacao_enxurrada_alagamento",     # 12300
    "Movimento de Massa": "deslizamento",                # 113xx (deslizamentos, quedas, corridas, subsidências)
    "Chuvas Intensas": "chuvas_intensas",                # 13214
}
COLS = ["seca_estiagem", "inundacao_enxurrada_alagamento", "deslizamento",
        "chuvas_intensas", "outros"]

arq = PASTA / NOME
if not arq.exists():
    PASTA.mkdir(parents=True, exist_ok=True)
    r = requests.get(URL, timeout=600)
    r.raise_for_status()
    arq.write_bytes(r.content)

d = pd.read_csv(arq, sep=";", encoding="latin1", low_memory=False,
                usecols=["Protocolo_S2iD", "Data_Evento", "Cod_Cobrade", "descricao_tipologia",
                         "Cod_IBGE_Mun", "Status"])
d["ano"] = pd.to_datetime(d["Data_Evento"], dayfirst=True, errors="coerce").dt.year
d = d[d["ano"].between(ANO_INICIO, ANO_FIM)].drop_duplicates("Protocolo_S2iD")
d["cod"] = d["Cod_IBGE_Mun"].astype(int)
d["grupo"] = d["descricao_tipologia"].map(GRUPOS).fillna("outros")

rec = d[d["Status"] == "Reconhecido"]
out = rec.pivot_table(index="cod", columns="grupo", values="Protocolo_S2iD",
                      aggfunc="count", fill_value=0).reindex(columns=COLS, fill_value=0)
out["total"] = out[COLS].sum(axis=1)
out["registros_todos"] = d.groupby("cod").size()  # inclui registros sem reconhecimento

# todos os municípios (lista do Censo 2022 em dados/social.csv); sem registro = 0
munis = pd.read_csv(RAIZ / "dados" / "social.csv", usecols=["cod"])["cod"]
fora = sorted(set(out.index) - set(munis))
if fora:
    print("códigos fora da lista de municípios:", fora)
out = out.reindex(munis.sort_values()).fillna(0).astype(int)
out["ano_inicio"], out["ano_fim"] = ANO_INICIO, ANO_FIM
out = out.reset_index()[["cod", "total"] + COLS + ["registros_todos", "ano_inicio", "ano_fim"]]
out.to_csv(RAIZ / "dados" / "desastres.csv", index=False)
print(out.shape)
print(out.drop(columns="cod").sum())
print("municípios com >=1 reconhecimento:", (out.total > 0).sum())
