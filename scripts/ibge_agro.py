"""Produção agropecuária, extrativa e da silvicultura por município (SIDRA/IBGE), formato longo.

Gera dados/agro.csv: cod, fonte, produto, valor_mil_reais, quantidade, unidade, ano

  PAM   tabela 5457  lavouras temporárias e permanentes (quantidade e valor)
  PPM   tabela 3939  efetivo dos rebanhos (cabeças; sem valor)
  PPM   tabela 74    produção de origem animal (leite, ovos, mel, ...: quantidade e valor)
  PEVS  tabela 289   extração vegetal (quantidade e valor)
  PSILV tabela 291   silvicultura (quantidade e valor)

Usa o último ano disponível de cada tabela. As consultas são feitas por UF (n6 in n3)
para ficar abaixo do limite de linhas da API. Respostas brutas em dados/brutos/ibge/sidra/agro/.

Executar: .venv/bin/python scripts/ibge_agro.py
"""
from __future__ import annotations

import json
import re
import time

import pandas as pd

from ibge_comum import BRUTOS, DADOS, baixar, numero, sidra

PASTA = BRUTOS / "sidra" / "agro"
UFS = [11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 35,
       41, 42, 43, 50, 51, 52, 53]

# tabela: (fonte, classificação, var. quantidade, var. valor, categorias excluídas, só estas categorias)
TABELAS = {
    # PAM: exclui o Total e as subdivisões do café (fica "Café (em grão) Total")
    5457: ("PAM", 782, 214, 215, {"0", "40140", "40141"}, None),
    # PPM rebanhos: exclui subtotais aninhados (matrizes de suínos, galinhas)
    3939: ("PPM", 79, 105, None, {"32795", "32793"}, None),
    74: ("PPM", 80, 106, 215, {"0"}, None),
    # PEVS: só categorias-folha (sem Total nem cabeçalhos de grupo) -> calculado dos metadados
    289: ("PEVS", 193, 144, 145, None, None),
    # PSILV: produtos por finalidade, sem a abertura por espécie
    291: ("PSILV", 194, 142, 143, None, {"3455", "3456", "3458", "3459", "3461", "3462", "3463"}),
}


def metadados(t):
    arq = baixar(f"https://servicodados.ibge.gov.br/api/v3/agregados/{t}/metadados",
                 PASTA / f"metadados_{t}.json")
    return json.loads(arq.read_text(encoding="utf-8"))


def ultimo_ano(t):
    arq = baixar(f"https://servicodados.ibge.gov.br/api/v3/agregados/{t}/periodos",
                 PASTA / f"periodos_{t}.json")
    return max(int(p["id"]) for p in json.loads(arq.read_text(encoding="utf-8")))


def folhas(cats):
    """Categorias sem filhas (a lista vem em ordem hierárquica, com o campo nivel)."""
    out = []
    for i, c in enumerate(cats):
        prox = cats[i + 1]["nivel"] if i + 1 < len(cats) else -1
        if prox <= c["nivel"] and c["id"] != 0:
            out.append(str(c["id"]))
    return out


def limpa_produto(nome):
    nome = re.sub(r"^\d+(\.\d+)*\s*-\s*", "", nome)  # "1.1 - Açaí (fruto)" -> "Açaí (fruto)"
    nome = nome.replace("*", "").strip()
    return {"Café (em grão) Total": "Café (em grão)"}.get(nome, nome)


def nomes_produtos(cats):
    """Nome limpo de cada categoria; folhas ambíguas ganham o grupo entre parênteses
    (PEVS: "Outros" de vários grupos, fibras de buriti/carnaúba/piaçava)."""
    out, pai = {}, {}
    for c in cats:
        pai[c["nivel"]] = limpa_produto(c["nome"])
        nome = limpa_produto(c["nome"])
        grupo = pai.get(c["nivel"] - 1, "")
        if nome in ("Outros", "Outras") and grupo:
            nome = f"{nome} ({grupo.lower()})"
        elif grupo == "Fibras":
            nome = f"{nome} (fibra)"
        out[str(c["id"])] = nome
    return out


def coleta(t, ano):
    fonte, cl, vq, vv, excl, so = TABELAS[t]
    meta = metadados(t)
    cats = next(c["categorias"] for c in meta["classificacoes"] if c["id"] == cl)
    if so is not None:
        ids = [str(c["id"]) for c in cats if str(c["id"]) in so]
    elif excl is None:
        ids = folhas(cats)
    else:
        ids = [str(c["id"]) for c in cats if str(c["id"]) not in excl]
    nomes = nomes_produtos(cats)
    variaveis = [v for v in (vq, vv) if v is not None]
    linhas = []
    for uf in UFS:
        for v in variaveis:  # uma variável por consulta (SP na PAM passa de 100 mil valores)
            caminho = f"t/{t}/n6/in%20n3%20{uf}/v/{v}/p/{ano}/c{cl}/{','.join(ids)}"
            destino = PASTA / f"t{t}_{ano}_uf{uf}_v{v}.json"
            novo = not destino.exists()
            for r in sidra(caminho, destino):
                linhas.append({"cod": int(r["D1C"]), "var": int(r["D2C"]), "cat": r["D4C"],
                               "produto": nomes[r["D4C"]], "valor": numero(r["V"]),
                               "unidade": r["MN"]})
            if novo:
                time.sleep(0.3)
    df = pd.DataFrame(linhas)
    q = df[df["var"] == vq][["cod", "cat", "produto", "valor", "unidade"]].rename(
        columns={"valor": "quantidade"})
    if vv is not None:
        val = df[df["var"] == vv][["cod", "cat", "valor"]].rename(columns={"valor": "valor_mil_reais"})
        out = q.merge(val, on=["cod", "cat"], how="outer")
        out = out[out["valor_mil_reais"].fillna(0) > 0]
    else:
        out = q.assign(valor_mil_reais=None)
        out = out[out["quantidade"].fillna(0) > 0]
    out["fonte"], out["ano"] = fonte, ano
    print(f"tabela {t} ({fonte}) {ano}: {len(out)} linhas, {out['produto'].nunique()} produtos")
    return out


def main():
    partes = [coleta(t, ultimo_ano(t)) for t in TABELAS]
    agro = pd.concat(partes, ignore_index=True)
    agro["quantidade"] = agro["quantidade"].astype(float)
    agro["valor_mil_reais"] = agro["valor_mil_reais"].astype(float)
    # números inteiros saem sem ".0"
    for c in ("quantidade", "valor_mil_reais"):
        agro[c] = agro[c].map(lambda x: "" if pd.isna(x) else (str(int(x)) if float(x).is_integer() else repr(x)))
    assert not agro.duplicated(["cod", "fonte", "produto"]).any()
    agro = agro.sort_values(["cod", "fonte", "produto"])
    agro[["cod", "fonte", "produto", "valor_mil_reais", "quantidade", "unidade", "ano"]].to_csv(
        DADOS / "agro.csv", index=False, encoding="utf-8")
    print("total:", len(agro), "linhas;", agro["cod"].nunique(), "municípios")


if __name__ == "__main__":
    main()
