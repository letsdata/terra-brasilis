"""CFEM arrecadada por município (ANM) -> dados/pontos/mineracao_municipio.csv

Fonte: ANM, Dados Abertos, "Compensação Financeira pela Exploração de Recursos Minerais (CFEM)",
arquivo CFEM_Arrecadacao_2022_2026.csv. Ano usado: último ano completo (2025).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402

from pontos_comum import BRUTOS, CasadorMunicipio, baixar, num_br, salvar  # noqa: E402

DIR = BRUTOS / "anm"
DIR.mkdir(exist_ok=True)
URL = "https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv"
ANO = 2025


def harmonizar(s: str) -> str:
    """Junta rótulos equivalentes da ANM ("MINÉRIO DE FERRO" e "FERRO")."""
    s = str(s).strip().upper()
    if s.startswith("MINÉRIO DE "):
        s = s[len("MINÉRIO DE "):]
    if s.startswith("ÁGUA MINERAL"):
        return "ÁGUA MINERAL"
    return {"CARVÃO MINERAL": "CARVÃO", "ALUMÍNIO": "BAUXITA"}.get(s, s)


def main():
    arq = baixar(URL, DIR / "CFEM_Arrecadacao_2022_2026.csv", timeout=1800)
    d = pd.read_csv(arq, encoding="latin1", dtype=str)
    d.columns = [c.strip() for c in d.columns]
    print(d.columns.tolist())
    print("meses por ano:", d.groupby("Ano")["Mês"].nunique().to_dict())
    d = d[d.Ano == str(ANO)].copy()
    d["valor"] = num_br(d.ValorRecolhido).fillna(0)
    d["cod"] = d.CodigoMunicipio.str.strip().str.replace(r"\.0$", "", regex=True)
    cm = CasadorMunicipio()
    validos = set(cm.tab.cod)
    sem = ~d.cod.isin(validos)
    print("linhas com código fora da tabela IBGE:", sem.sum(), "R$", round(d[sem].valor.sum()))
    # tenta casar pelo nome quando o código não bate
    d.loc[sem, "cod"] = [cm.cod(m, u) for m, u in zip(d[sem]["Município"], d[sem].UF)]
    print("ainda sem código:", (d.cod == "").sum(), "R$", round(d[d.cod == ""].valor.sum()), d[d.cod == ""][["Município", "UF"]].drop_duplicates().head(10).values.tolist())
    d = d[d.cod != ""]
    d["substancia_original"] = d["Substância"].str.strip()
    d["substancia"] = d.substancia_original.map(harmonizar)

    por_sub = d.groupby(["cod", "substancia"]).valor.sum().reset_index()
    princ = por_sub.sort_values("valor", ascending=False).drop_duplicates("cod")
    tot = d.groupby("cod").agg(cfem_reais=("valor", "sum"), n_substancias=("substancia", "nunique")).reset_index()
    out = tot.merge(princ.rename(columns={"substancia": "substancia_principal", "valor": "cfem_substancia_principal"}), on="cod")
    out["uf"] = out.cod.map(cm.ufs)
    out["municipio"] = out.cod.map(cm.nomes)
    out["ano"] = ANO
    out["cfem_reais"] = out.cfem_reais.round(2)
    out["cfem_substancia_principal"] = out.cfem_substancia_principal.round(2)
    out = out[out.cfem_reais > 0]
    out = out[["cod", "uf", "municipio", "cfem_reais", "substancia_principal", "cfem_substancia_principal", "n_substancias", "ano"]]
    out = out.sort_values("cfem_reais", ascending=False)
    print(f"total {ANO}: R$ {out.cfem_reais.sum():,.0f} em {len(out)} municípios")
    print(out.head(10).to_string())
    salvar(out, "mineracao_municipio.csv")


if __name__ == "__main__":
    main()
