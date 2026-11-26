"""Base municipal do IBGE para o Terra Brasilis.

Gera:
  dados/municipios.csv               cadastro + sede + área + população 2022 + PIB municipal + bioma
  dados/ufs.csv                      UFs com capital
  dados/brutos/ibge/municipios.geojson  malha municipal (API de malhas v3, qualidade intermediária)
                                         + correção de Boa Esperança do Norte (malha 2025)
  dados/brutos/ibge/ufs.geojson      malha das UFs (API de malhas v3, qualidade intermediária)
  dados/brutos/ibge/municipios_minima.geojson, ufs_minima.geojson  versões leves (qualidade mínima)

Executar: .venv/bin/python scripts/ibge_base.py
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import shapefile  # pyshp
from shapely.geometry import mapping, shape
from shapely.validation import make_valid

from ibge_comum import BRUTOS, DADOS, baixar, numero, sidra

GEOFTP = "https://geoftp.ibge.gov.br"
MALHAS = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"


# ---------------------------------------------------------------- cadastro
def cadastro():
    m = json.loads(baixar("https://servicodados.ibge.gov.br/api/v1/localidades/municipios",
                          BRUTOS / "localidades_municipios.json").read_text(encoding="utf-8"))
    e = json.loads(baixar("https://servicodados.ibge.gov.br/api/v1/localidades/estados",
                          BRUTOS / "localidades_estados.json").read_text(encoding="utf-8"))
    linhas = []
    for x in m:
        uf = x["regiao-imediata"]["regiao-intermediaria"]["UF"]
        linhas.append({"cod": int(x["id"]), "nome": x["nome"], "uf": uf["sigla"],
                       "cod_uf": int(uf["id"]), "regiao": uf["regiao"]["nome"]})
    ufs = pd.DataFrame([{"cod": int(x["id"]), "sigla": x["sigla"], "nome": x["nome"],
                         "regiao": x["regiao"]["nome"]} for x in e])
    return pd.DataFrame(linhas), ufs


# ---------------------------------------------------------------- sedes
def sedes():
    """Coordenadas das sedes municipais: Base de Localidades do Brasil 2022 (IBGE)."""
    pasta = BRUTOS / "localidades_2022"
    z = baixar(f"{GEOFTP}/organizacao_do_territorio/estrutura_territorial/localidades/"
               "Localidades_do_Brasil/2022/Localidades_Brasil_shp.zip",
               pasta / "Localidades_Brasil_shp.zip")
    shp = pasta / "BR_localidades_2022.shp"
    if not shp.exists():
        zipfile.ZipFile(z).extractall(pasta)
    r = shapefile.Reader(str(shp), encoding="utf-8")
    sede, capital = {}, set()
    for rec in r.iterRecords():
        d = rec.as_dict()
        cod = int(d["CD_MUN"])
        tipo = (d["CT_LOCALID"], d["SCT_LOCALI"])
        ponto = (d["LAT_LOCALI"], d["LONG_LOCAL"])
        if tipo[1] in ("Capital Estadual", "Capital Federal"):
            capital.add(cod)
            sede.setdefault(cod, ponto)
        elif tipo == ("Cidade", "Sede Municipal"):
            sede[cod] = ponto
        elif tipo[0].startswith("Distrito Estadual"):  # Fernando de Noronha
            sede.setdefault(cod, ponto)
    return sede, capital


# ---------------------------------------------------------------- área
def areas():
    arq = baixar(f"{GEOFTP}/organizacao_do_territorio/estrutura_territorial/areas_territoriais/"
                 "2025/AR_BR_RG_UF_RGINT_RGI_MUN_2025.xls",
                 BRUTOS / "areas" / "AR_BR_RG_UF_RGINT_RGI_MUN_2025.xls")
    a = pd.read_excel(arq, sheet_name="AR_BR_MUN_2025")
    a = a.dropna(subset=["CD_MUN"])
    return {int(c): float(v) for c, v in zip(a["CD_MUN"], a["AR_MUN_2025"])}


# ---------------------------------------------------------------- SIDRA
def populacao():
    linhas = sidra("t/4714/n6/all/v/93/p/2022", BRUTOS / "sidra" / "t4714_pop2022.json")
    return {int(r["D1C"]): numero(r["V"]) for r in linhas}


PIB_VARS = {"37": "pib", "513": "va_agro", "517": "va_ind", "6575": "va_serv",
            "525": "va_adm", "543": "impostos"}


def _pib_ano(caminho, destino, nomes):
    out, anos = {}, set()
    for r in sidra(caminho, destino):
        out.setdefault(int(r["D1C"]), {})[nomes[r["D2C"]]] = numero(r["V"])
        anos.add(int(r["D3C"]))
    assert len(anos) == 1, anos
    return out, anos.pop()


def pib():
    """PIB do último ano publicado + decomposição (VA por setor e impostos) do último ano
    em que ela existe. Para 2022 e 2023 o IBGE divulgou só o PIB total (nota técnica
    02/2024 das Contas Nacionais), então a decomposição vem de outro ano (2021)."""
    out, ano = _pib_ano("t/5938/n6/all/v/37/p/last%201",
                        BRUTOS / "sidra" / "t5938_pib_ultimo.json", {"37": "pib"})
    serie = sidra("t/5938/n1/all/v/513/p/all", BRUTOS / "sidra" / "t5938_vaagro_brasil_serie.json")
    ano_va = max(int(r["D3C"]) for r in serie if numero(r["V"]) is not None)
    nomes = dict(PIB_VARS, **{"37": "pib_va"})
    dec, ano2 = _pib_ano(f"t/5938/n6/all/v/{','.join(nomes)}/p/{ano_va}",
                         BRUTOS / "sidra" / f"t5938_decomposicao_{ano_va}.json", nomes)
    assert ano2 == ano_va
    for cod, d in dec.items():
        d.pop("pib", None)
        out.setdefault(cod, {}).update(d)
    return out, ano, ano_va


# ---------------------------------------------------------------- bioma
def biomas():
    arq = baixar(f"{GEOFTP}/informacoes_ambientais/estudos_ambientais/biomas/documentos/"
                 "Bioma_Predominante_por_Municipio_2024.csv",
                 BRUTOS / "biomas" / "Bioma_Predominante_por_Municipio_2024.csv")
    b = pd.read_csv(arq, sep=";", encoding="utf-8-sig", dtype=str)
    b.columns = [c.strip() for c in b.columns]
    b = b[b.iloc[:, 0].str.strip().str.fullmatch(r"\d{7}", na=False)]
    return {int(c): v.strip() for c, v in zip(b.iloc[:, 0], b["Bioma predominante"])}


# ---------------------------------------------------------------- malhas
def nvert(g):
    return sum(len(p.exterior.coords) + sum(len(i.coords) for i in p.interiors)
               for p in getattr(g, "geoms", [g]))


def poligonal(g):
    g = make_valid(g) if not g.is_valid else g
    if g.geom_type == "GeometryCollection":
        from shapely.geometry import MultiPolygon
        ps = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon")]
        flat = []
        for p in ps:
            flat.extend(getattr(p, "geoms", [p]))
        g = MultiPolygon(flat) if len(flat) > 1 else flat[0]
    return g


def malhas(cad: pd.DataFrame, qualidade: str, sufixo: str):
    bruto = baixar(f"{MALHAS}?formato=application/vnd.geo+json&qualidade={qualidade}&intrarregiao=municipio",
                   BRUTOS / f"api_malhas_BR_municipio_{qualidade}.geojson")
    ufb = baixar(f"{MALHAS}?formato=application/vnd.geo+json&qualidade={qualidade}&intrarregiao=UF",
                 BRUTOS / f"api_malhas_BR_UF_{qualidade}.geojson")
    nomes = dict(zip(cad["cod"], cad["nome"]))
    siglas = dict(zip(cad["cod"], cad["uf"]))
    feats = json.loads(bruto.read_text(encoding="utf-8"))["features"]
    geoms = {int(f["properties"]["codarea"]): poligonal(shape(f["geometry"])) for f in feats}
    corrigidos = []

    # A malha da API é a de 2022 (5.570 municípios). Boa Esperança do Norte (MT, 5101837),
    # instalado em 2025, vem da Malha Municipal 2025 (FTP), junto com os municípios dos quais
    # foi desmembrado, para não haver sobreposição.
    faltam = sorted(set(cad["cod"]) - set(geoms))
    if faltam:
        pasta = BRUTOS / "malha_2025_MT"
        z = baixar(f"{GEOFTP}/organizacao_do_territorio/malhas_territoriais/malhas_municipais/"
                   "municipio_2025/UFs/MT/MT_Municipios_2025.zip", pasta / "MT_Municipios_2025.zip")
        shp = next(pasta.glob("*.shp"), None)
        if shp is None:
            zipfile.ZipFile(z).extractall(pasta)
            shp = next(pasta.glob("*.shp"))
        r = shapefile.Reader(str(shp), encoding="utf-8")
        g25 = {int(sr.record.as_dict()["CD_MUN"]): poligonal(shape(sr.shape.__geo_interface__))
               for sr in r.iterShapeRecords()}
        for cod in faltam:
            if cod not in g25:
                print("sem geometria:", cod)
                continue
            novo = g25[cod]
            pais = [c for c, g in geoms.items() if c in g25 and g.intersects(novo)
                    and g.intersection(novo).area > 0.01 * novo.area]
            alvo = sum(nvert(geoms[c]) for c in pais)
            # tolerância que reproduz a densidade de vértices da malha mínima
            melhor = None
            for tol in (0.0005, 0.001, 0.002, 0.003, 0.005, 0.008, 0.012, 0.02):
                n = sum(nvert(g25[c].simplify(tol)) for c in pais)
                if melhor is None or abs(n - alvo) < abs(melhor[1] - alvo):
                    melhor = (tol, n)
            tol = melhor[0]
            for c in pais + [cod]:
                geoms[c] = poligonal(g25[c].simplify(tol, preserve_topology=True))
                corrigidos.append(c)
            print(f"[{qualidade}] {cod}: geometria da malha 2025; recortados {pais}; tolerância {tol}")

    saida = {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {"cod": c, "nome": nomes.get(c), "uf": siglas.get(c),
                        "fonte_geom": "malha2025_MT" if c in corrigidos else f"api_malhas_v3_{qualidade}"},
         "geometry": mapping(g)} for c, g in sorted(geoms.items())]}
    (BRUTOS / f"municipios{sufixo}.geojson").write_text(json.dumps(saida, ensure_ascii=False), encoding="utf-8")

    uf = json.loads(ufb.read_text(encoding="utf-8"))
    sig = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI",
           23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES",
           33: "RJ", 35: "SP", 41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}
    for f in uf["features"]:
        c = int(f["properties"]["codarea"])
        f["properties"] = {"cod": c, "sigla": sig.get(c)}
        f["geometry"] = mapping(poligonal(shape(f["geometry"])))
    (BRUTOS / f"ufs{sufixo}.geojson").write_text(json.dumps(uf, ensure_ascii=False), encoding="utf-8")
    return geoms, corrigidos


# ---------------------------------------------------------------- principal
def main():
    cad, ufs = cadastro()
    sede, capitais = sedes()
    area = areas()
    pop = populacao()
    p, ano, ano_va = pib()
    bio = biomas()
    # principal: qualidade intermediária (na mínima, 77 sedes caem fora do próprio polígono);
    # a mínima fica como versão leve para desenho.
    geoms, corrigidos = malhas(cad, "intermediaria", "")
    malhas(cad, "minima", "_minima")

    cad["capital"] = cad["cod"].isin(capitais).astype(int)
    lat, lon, met = [], [], []
    for c in cad["cod"]:
        if c in sede:
            lat.append(sede[c][0]); lon.append(sede[c][1]); met.append("sede")
        elif c in geoms:  # alternativa: ponto sobre a superfície do polígono
            pt = geoms[c].representative_point()
            lat.append(round(pt.y, 4)); lon.append(round(pt.x, 4)); met.append("poligono")
        else:
            lat.append(None); lon.append(None); met.append("")
    cad["lat"], cad["lon"], cad["coord_metodo"] = lat, lon, met
    cad["area_km2"] = cad["cod"].map(area)
    cad["pop2022"] = cad["cod"].map(pop).astype("Int64")
    for col in list(PIB_VARS.values()) + ["pib_va"]:
        cad[col] = cad["cod"].map(lambda c: p.get(c, {}).get(col)).astype("Int64")
    cad["pib_ano"] = cad["cod"].map(lambda c: ano if p.get(c, {}).get("pib") is not None else None).astype("Int64")
    cad["va_ano"] = cad["cod"].map(lambda c: ano_va if p.get(c, {}).get("va_agro") is not None else None).astype("Int64")
    cad["bioma"] = cad["cod"].map(bio)
    cols = ["cod", "nome", "uf", "regiao", "capital", "lat", "lon", "coord_metodo", "area_km2",
            "pop2022", "pib", "pib_ano", "va_agro", "va_ind", "va_serv", "va_adm", "impostos",
            "pib_va", "va_ano", "bioma"]
    cad = cad.sort_values("cod")[cols]
    cad.to_csv(DADOS / "municipios.csv", index=False, encoding="utf-8")

    cap = cad[cad["capital"] == 1][["cod", "nome", "uf"]]
    ufs = ufs.merge(cap.rename(columns={"cod": "cod_capital", "nome": "capital", "uf": "sigla"}),
                    on="sigla", how="left").sort_values("cod")
    ufs[["cod", "sigla", "nome", "regiao", "capital", "cod_capital"]].to_csv(
        DADOS / "ufs.csv", index=False, encoding="utf-8")

    print("municípios:", len(cad), "| ano PIB:", ano, "| ano decomposição:", ano_va)
    print(cad.isna().sum()[lambda s: s > 0].to_dict())
    print(cad["coord_metodo"].value_counts().to_dict())


if __name__ == "__main__":
    main()
