"""Campos de petróleo e gás (ANP) -> dados/pontos/petroleo.csv

- Produção 2025 por poço (mar: producao-mar-2025.csv; terra: 4 arquivos trimestrais), somada por campo.
- Coordenada: ponto representativo do polígono do campo (shapefile "campos-producao" da ANP,
  dados georreferenciados das bacias sedimentares, versão 08/08/2023).
Unidades: óleo e condensado em m³; gás em mil m³ (ANP: "Mm³" = mil m³).
"""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import shapefile  # noqa: E402
from shapely.geometry import shape  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from pontos_comum import BRUTOS, baixar, normalizar, num_br, salvar, completar_cod  # noqa: E402

DIR = BRUTOS / "anp"
DIR.mkdir(exist_ok=True)
B = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos"
P = B + "/arquivos-fase-de-desenvolvimento-e-producao/arquivos-producao-de-petroleo-e-gas-natural-nacional"
URLS = {
    "producao-mar-2025.csv": P + "/pm/producao-mar-2025.csv",
    **{f"producao_por_poco_terra_2025_{t}_trim.csv": P + f"/pt/2025/producao_por_poco_terra_2025_{t}_trim.csv" for t in range(1, 5)},
}
URL_CAMPOS = B + "/arquivos-dados-georreferenciados-das-bacias-sedimentares-brasileiras/campos-producao.zip"
ANO = 2025
M3_BBL = 6.289811

UFS = {"Alagoas": "AL", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE", "Espírito Santo": "ES",
       "Maranhão": "MA", "Paraná": "PR", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
       "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE", "Pará": "PA", "Amapá": "AP",
       "Piauí": "PI", "Pernambuco": "PE", "Paraíba": "PB", "Minas Gerais": "MG", "Mato Grosso": "MT"}


def producao() -> pd.DataFrame:
    partes = []
    for nome, url in URLS.items():
        arq = baixar(url, DIR / nome)
        d = pd.read_csv(arq, dtype=str, encoding="utf-8-sig")
        d.columns = [c.strip("[]") for c in d.columns]
        partes.append(d)
    d = pd.concat(partes, ignore_index=True)
    d = d[d.Ano == str(ANO)]
    print("meses:", sorted(d["Mês/Ano"].unique()))
    for c, n in [("Produção de Óleo (m³)", "oleo"), ("Produção de Condensado (m³)", "cond"),
                 ("Produção de Gás Associado (Mm³)", "ga"), ("Produção de Gás Não Associado (Mm³)", "gna")]:
        d[n] = num_br(d[c]).fillna(0)
    g = d.groupby(["Campo", "Bacia", "Estado", "Ambiente"]).agg(
        oleo_m3=("oleo", "sum"), condensado_m3=("cond", "sum"),
        gas_assoc=("ga", "sum"), gas_nao_assoc=("gna", "sum"), pocos=("Poço", "nunique")).reset_index()
    # campo pode aparecer em dois estados/ambientes: fica com o de maior produção como rótulo
    g["total"] = g.oleo_m3 + g.condensado_m3 + g.gas_assoc + g.gas_nao_assoc
    rot = g.sort_values("total", ascending=False).drop_duplicates("Campo")[["Campo", "Bacia", "Estado", "Ambiente"]]
    s = g.groupby("Campo")[["oleo_m3", "condensado_m3", "gas_assoc", "gas_nao_assoc", "pocos"]].sum().reset_index()
    return s.merge(rot, on="Campo")


def campos() -> pd.DataFrame:
    shp = DIR / "campos" / "CAMPOS_DE_PRODUCAO_08082023.shp"
    if not shp.exists():
        zipfile.ZipFile(baixar(URL_CAMPOS, DIR / "campos-producao.zip")).extractall(DIR / "campos")
    r = shapefile.Reader(str(shp.with_suffix("")), encoding="latin1")
    geoms, info = {}, {}
    for sr in r.iterShapeRecords():
        rec = sr.record.as_dict()
        k = normalizar(rec["NOM_CAMPO"])
        g = shape(sr.shape.__geo_interface__)
        if not g.is_valid:
            g = g.buffer(0)
        geoms.setdefault(k, []).append(g)
        info.setdefault(k, rec)
    linhas = []
    for k, gs in geoms.items():
        g = unary_union(gs)
        p = g.representative_point()
        rec = info[k]
        linhas.append({"chave": k, "lat": p.y, "lon": p.x, "operador": rec["OPERADOR_C"], "etapa": rec["ETAPA"],
                       "fluido_principal": rec["FLUIDO_PRI"], "localizacao": rec["Localizaca"],
                       "lamina_dagua_m": rec["MED_LAMINA"], "inicio_producao": rec["DAT_INICIO"]})
    return pd.DataFrame(linhas)


def main():
    s = producao()
    s["chave"] = s.Campo.map(normalizar)
    # "AnC_X" (área não contratada adjacente ao campo X, ex.: AnC_MERO, AnC_Jubarte_Sudoeste):
    # usa o polígono do campo X
    anc = s.chave.str.startswith("ANC ")
    s.loc[anc, "chave"] = s.loc[anc, "chave"].str[4:].str.split(" ").str[0]
    s.loc[anc & (s.chave == "NORTE"), "chave"] = "ATAPU"
    c = campos()
    d = s.merge(c, on="chave", how="left")
    d["oleo_total_m3"] = d.oleo_m3 + d.condensado_m3
    d["gas_mil_m3"] = d.gas_assoc + d.gas_nao_assoc
    sem = d[d.lat.isna()]
    print(f"campos produtores {ANO}: {len(d)}; sem polígono: {len(sem)} "
          f"({sem.oleo_total_m3.sum() / d.oleo_total_m3.sum():.2%} do óleo, {sem.gas_mil_m3.sum() / d.gas_mil_m3.sum():.2%} do gás)")
    print(sem.sort_values("oleo_total_m3", ascending=False).head(15)[["Campo", "Bacia", "oleo_total_m3", "gas_mil_m3"]].to_string())
    d = d.dropna(subset=["lat"])
    d = d[(d.oleo_total_m3 > 0) | (d.gas_mil_m3 > 0)]
    out = pd.DataFrame({
        "nome": d.Campo.str.strip(),
        "lat": d.lat.round(5), "lon": d.lon.round(5),
        "cod": "",
        "uf": d.Estado.map(UFS),
        "bacia": d.Bacia, "ambiente": d.Ambiente.str.lower().map({"mar": "mar", "terra": "terra"}),
        "operador": d.operador, "fluido_principal": d.fluido_principal,
        "oleo_m3": d.oleo_total_m3.round(1),
        "oleo_bbl_dia": (d.oleo_total_m3 * M3_BBL / 365).round(1),
        "gas_mil_m3": d.gas_mil_m3.round(1),
        "gas_mil_m3_dia": (d.gas_mil_m3 / 365).round(2),
        "boe_dia": ((d.oleo_total_m3 * M3_BBL + d.gas_mil_m3 * 1000 / 1000 * M3_BBL) / 365).round(1),
        "pocos": d.pocos.astype(int),
        "lamina_dagua_m": d.lamina_dagua_m,
        "ano": ANO,
    }).sort_values("oleo_bbl_dia", ascending=False)
    print("UF faltando:", out[out.uf.isna()].nome.tolist()[:10])
    print(f"óleo total {out.oleo_bbl_dia.sum():,.0f} bbl/d; gás {out.gas_mil_m3_dia.sum():,.0f} mil m³/d")
    print(out.head(10)[["nome", "bacia", "uf", "oleo_bbl_dia", "gas_mil_m3_dia", "lat", "lon"]].to_string())
    # só campos em terra recebem código de município (mar fica vazio)
    terra = out.ambiente == "terra"
    out.loc[terra] = completar_cod(out[terra]).drop(columns="cod_metodo")
    print("terra sem cod:", (out[terra].cod == "").sum())
    salvar(out, "petroleo.csv")


if __name__ == "__main__":
    main()
