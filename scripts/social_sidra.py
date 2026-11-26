"""Baixa do SIDRA/IBGE o emprego por seção da CNAE (CEMPRE) e indicadores do Censo 2022
por município e grava dados/empregos.csv e dados/social.csv.

Uso: .venv/bin/python scripts/social_sidra.py
Os JSON brutos ficam em dados/brutos/social/sidra_*.json (reaproveitados se já existirem).
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "dados" / "brutos" / "social"
BRUTOS.mkdir(parents=True, exist_ok=True)
API = "https://apisidra.ibge.gov.br/values"

UFS = [11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29,
       31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53]


def sidra(nome, caminho):
    """Consulta a API SIDRA (com cache em disco) e devolve DataFrame com cabeçalho."""
    arq = BRUTOS / f"sidra_{nome}.json"
    if arq.exists():
        dados = json.loads(arq.read_text(encoding="utf-8"))
    else:
        url = f"{API}{caminho}"
        for tentativa in range(5):
            try:
                r = requests.get(url, timeout=300)
                r.raise_for_status()
                dados = r.json()
                break
            except Exception as e:  # noqa: BLE001
                print(f"  falha {nome} ({tentativa + 1}/5): {e}")
                time.sleep(5 * (tentativa + 1))
        else:
            raise RuntimeError(f"SIDRA falhou: {url}")
        arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    cab = dados[0]
    df = pd.DataFrame(dados[1:])
    df.attrs["cab"] = cab
    return df


def valor(s):
    """Converte o campo V do SIDRA. '-' é zero absoluto; '..', '...', 'X' são ausentes."""
    s = s.astype(str).str.strip()
    out = pd.to_numeric(s, errors="coerce")
    out[s == "-"] = 0.0
    return out


# --------------------------------------------------------------------------- CEMPRE
def empregos():
    meta = json.loads(requests.get(
        "https://servicodados.ibge.gov.br/api/v3/agregados/9528/metadados", timeout=60).text)
    (BRUTOS / "meta_9528.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    cats = [c for c in meta["classificacoes"][0]["categorias"] if c["nivel"] <= 1]
    ids = ",".join(str(c["id"]) for c in cats)
    ano = meta["periodicidade"]["fim"]
    partes = []
    for uf in UFS:
        df = sidra(f"9528_{ano}_uf{uf}",
                   f"/t/9528/n6/in%20n3%20{uf}/v/707,708/p/{ano}/c12762/{ids}")
        partes.append(df)
    df = pd.concat(partes, ignore_index=True)
    df["cod"] = df["D1C"].astype(int)
    df["v"] = valor(df["V"])
    total = df["D4C"] == "117897"  # categoria "Total" (todas as seções)
    df["secao"] = df["D4N"].str[0].where(~total, "Total")
    df["descricao"] = df["D4N"].str[2:].str.strip().where(~total, "Total de todas as seções")
    var = {"707": "pessoal_ocupado", "708": "assalariados"}
    df["var"] = df["D2C"].map(var)
    out = (df.set_index(["cod", "secao", "descricao", "var"])["v"]
             .unstack("var").reset_index())
    out["ano"] = int(ano)
    out = out[["cod", "secao", "descricao", "pessoal_ocupado", "assalariados", "ano"]]
    out = out.sort_values(["cod", "secao"])
    for c in ["pessoal_ocupado", "assalariados"]:
        out[c] = out[c].astype("Int64")
    out.to_csv(RAIZ / "dados" / "empregos.csv", index=False)
    print("empregos.csv", out.shape, "municípios", out.cod.nunique(),
          "ausentes (X/..):", out.pessoal_ocupado.isna().sum())
    return out


# --------------------------------------------------------------------------- Censo 2022
def serie(nome, caminho, filtro=None):
    df = sidra(nome, caminho)
    df["cod"] = df["D1C"].astype(int)
    df["v"] = valor(df["V"])
    return df


def social():
    cols = {}
    # Alfabetização 15+ (taxa %, tabela 9543)
    d = serie("9543", "/t/9543/n6/all/v/2513/p/2022/c2/6794/c86/95251/c287/100362")
    cols["alfabetizacao_15mais"] = d.set_index("cod")["v"]

    # Superior completo, 25+ (tabela 10141, contagens; % calculado)
    d = serie("10141", "/t/10141/n6/all/v/1643/p/2022/c1568/120704,99713/c2/6794/c839/46583")
    p = d.pivot_table(index="cod", columns="D4C", values="v", aggfunc="first")
    cols["superior_25mais"] = 100 * p["99713"] / p["120704"]

    # Rendimento domiciliar per capita médio e mediano (tabela 10295)
    d = serie("10295", "/t/10295/n6/all/v/13431,13534/p/2022/c2/6794/c86/95251/c58/95253")
    p = d.pivot_table(index="cod", columns="D2C", values="v", aggfunc="first")
    cols["renda_pc"] = p["13431"]
    cols["renda_pc_mediana"] = p["13534"]

    # Religião, pessoas de 10+ (tabela 9537, contagens; % calculado sobre o total 10+)
    rel = {"95278": "total", "95263": "religiao_catolica", "95277": "religiao_evangelica",
           "2836": "religiao_sem", "2826": "religiao_espirita", "2827": "religiao_afro"}
    d = serie("9537", f"/t/9537/n6/all/v/140/p/2022/c133/{','.join(rel)}/c2/6794/c58/95253")
    p = d.pivot_table(index="cod", columns="D4C", values="v", aggfunc="first")
    for k, nome in rel.items():
        if nome != "total":
            cols[nome] = 100 * p[k] / p["95278"]

    # Esgotamento sanitário: moradores com rede geral, pluvial ou fossa ligada à rede (7555)
    d = serie("7555", "/t/7555/n6/all/v/382/p/2022/c11558/46292,46290/c58/95253/c86/95251")
    p = d.pivot_table(index="cod", columns="D4C", values="v", aggfunc="first")
    cols["esgoto_rede"] = 100 * p["46290"] / p["46292"]

    # Água: moradores com ligação à rede geral usada como forma principal (6894)
    d = serie("6894", "/t/6894/n6/all/v/382/p/2022/c1821/72129,72144/c58/95253/c86/95251")
    p = d.pivot_table(index="cod", columns="D4C", values="v", aggfunc="first")
    cols["agua_rede"] = 100 * p["72144"] / p["72129"]

    # Idade mediana (9515)
    d = serie("9515", "/t/9515/n6/all/v/10613/p/2022")
    cols["idade_mediana"] = d.set_index("cod")["v"]

    # Indígenas (9718): pessoas indígenas (cor ou raça indígena + se considera indígena)
    d = serie("9718", "/t/9718/n6/all/v/350,93/p/2022/c1714/60024/c2661/32776")
    p = d.pivot_table(index="cod", columns="D2C", values="v", aggfunc="first")
    cols["pct_indigena"] = 100 * p["350"] / p["93"]

    # Quilombolas (9578)
    d = serie("9578", "/t/9578/n6/all/v/4709,93/p/2022/c2661/32776")
    p = d.pivot_table(index="cod", columns="D2C", values="v", aggfunc="first")
    cols["pct_quilombola"] = 100 * p["4709"] / p["93"]

    out = pd.DataFrame(cols)
    out.index.name = "cod"
    out = out.reset_index().sort_values("cod")
    for c in out.columns:
        if c == "cod":
            continue
        out[c] = out[c].round(2)
    out["ano"] = 2022
    out.to_csv(RAIZ / "dados" / "social.csv", index=False)
    print("social.csv", out.shape)
    print(out.describe().T[["count", "mean", "min", "max"]])
    return out


if __name__ == "__main__":
    empregos()
    social()
