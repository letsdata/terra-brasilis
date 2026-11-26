"""Unidades de conservação federais (CNUC/MMA + visitação ICMBio) -> dados/pontos/areas_protegidas.csv

- Atributos: CNUC 2026_07 (CSV, MMA dados abertos).
- Geometria: polígonos CNUC 2025_08 (shapefile, SIRGAS 2000); ponto = representative_point
  (sempre dentro do polígono) e também o centroide.
- Visitação: ICMBio, "Visitação em Unidades de Conservação Federais" (2000-2024), último ano
  com dado por UC.
RPPNs (reservas privadas, 826 federais) ficam de fora.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import shapefile  # noqa: E402
from shapely.geometry import shape  # noqa: E402

from pontos_comum import BRUTOS, CasadorMunicipio, baixar, dentro_do_brasil, num_br, salvar, cod_pelo_ponto  # noqa: E402

DIR = BRUTOS / "cnuc"
DIR.mkdir(exist_ok=True)
BASE = "https://dados.mma.gov.br/dataset/44b6dc8a-dc82-4a84-8d95-1b0da7c85dac/resource/"
URL_CSV = BASE + "72dd3d2d-3cca-4b97-b382-a1c90531e379/download/cnuc_2026_07.csv"
URL_SHP = BASE + "6ba9a557-87e8-4882-acb7-b3e0f0ea192d/download/shp_cnuc_2025_08.zip"
URL_VIS = ("https://www.gov.br/icmbio/pt-br/acesso-a-informacao/dados-abertos/arquivos/atualizacao-novembro-2025/"
           "visitacao-em-unidades/visitacao_em_ucs_federais__2000___2024____atualizado30_10.xlsx")

CATEGORIA = {
    "Parque": "Parque Nacional",
    "Floresta": "Floresta Nacional",
}
MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "no", "na", "nos", "nas"}
SIGLAS = {"APA", "ARIE", "RESEX", "RDS", "REBIO", "ESEC", "FLONA", "II", "III", "IV"}


def titulo(nome: str) -> str:
    out = []
    for i, p in enumerate(str(nome).lower().split()):
        if p.upper() in SIGLAS:
            out.append(p.upper())
        elif i > 0 and p in MINUSCULAS:
            out.append(p)
        else:
            out.append("-".join(s[:1].upper() + s[1:] for s in p.split("-")))
    return " ".join(out)


def pontos_poligonos() -> pd.DataFrame:
    shp = DIR / "shp" / "cnuc_2025_08.shp"
    if not shp.exists():
        import zipfile
        z = baixar(URL_SHP, DIR / "shp_cnuc_2025_08.zip", timeout=900)
        zipfile.ZipFile(z).extractall(DIR / "shp")
    r = shapefile.Reader(str(shp.with_suffix("")))
    linhas = []
    for sr in r.iterShapeRecords(fields=["cd_cnuc", "esfera"]):
        if sr.record["esfera"] != "Federal" or not sr.shape.points:
            continue
        g = shape(sr.shape.__geo_interface__)
        if not g.is_valid:
            g = g.buffer(0)
        p, c = g.representative_point(), g.centroid
        linhas.append({"codigo_uc": sr.record["cd_cnuc"], "lat": p.y, "lon": p.x, "lat_centroide": c.y, "lon_centroide": c.x})
    return pd.DataFrame(linhas).drop_duplicates("codigo_uc")


def visitacao() -> pd.DataFrame:
    arq = baixar(URL_VIS, DIR / "visitacao_ucs_2000_2024.xlsx")
    v = pd.read_excel(arq, header=1)
    anos = [c for c in v.columns if isinstance(c, (int, float)) and 1990 < c < 2100]
    v = v.dropna(subset=["CNUC"])
    linhas = []
    for _, r in v.iterrows():
        serie = pd.to_numeric(r[anos], errors="coerce").dropna()
        serie = serie[serie > 0]
        if serie.empty:
            continue
        ano = int(max(serie.index))
        linhas.append({"codigo_uc": str(r.CNUC).strip(), "visitantes": int(serie[max(serie.index)]), "ano_visitacao": ano})
    return pd.DataFrame(linhas)


def main():
    arq = baixar(URL_CSV, DIR / "cnuc_2026_07.csv")
    d = pd.read_csv(arq, sep=";", encoding="latin1", dtype=str)
    d = d[(d["Esfera Administrativa"] == "Federal") & (d["Categoria de Manejo"] != "Reserva Particular do Patrimônio Natural")].copy()
    print("UCs federais (sem RPPN):", len(d))

    d["codigo_uc"] = d["Código UC"].str.strip()
    d = d.merge(pontos_poligonos(), on="codigo_uc", how="left")
    print("sem polígono:", d.lat.isna().sum(), d[d.lat.isna()]["Nome da UC"].tolist())
    d = d.dropna(subset=["lat"])

    vis = visitacao()
    d = d.merge(vis, on="codigo_uc", how="left")

    cm = CasadorMunicipio()
    mun = d["Municípios Abrangidos"].fillna("").str.split(r"\s+-\s+|,", regex=True).str[0].str.strip()
    nm = mun.str.extract(r"^(.*)\((\w\w)\)\s*$")
    d["cod"] = [cm.cod(a, b) if isinstance(a, str) else "" for a, b in zip(nm[0].str.strip(), nm[1])]

    area_ha = num_br(d["Área soma biomas"])
    area_ato = num_br(d["Área Ato Legal de Criação"])
    area_ha = area_ha.where(area_ha > 0, area_ato)
    out = pd.DataFrame({
        "nome": d["Nome da UC"].map(titulo),
        "lat": d.lat.round(5), "lon": d.lon.round(5),
        "cod": d.cod,
        "uf": d["UF"].str.strip(),
        "categoria": d["Categoria de Manejo"].map(lambda c: CATEGORIA.get(c, c)),
        "grupo": d["Grupo"],
        "area_km2": (area_ha / 100).round(2),
        "visitantes": d.visitantes.astype("Int64"),
        "ano_visitacao": d.ano_visitacao.astype("Int64"),
        "ano_criacao": d["Ano de Criação"],
        "bioma": d["Bioma declarado"],
        "marinha_pct": d["% Além da linha de costa"],
        "patrimonio_mundial": d["Sítios do Patrimônio Mundial"].fillna(""),
        "codigo_uc": d.codigo_uc,
        "lat_centroide": d.lat_centroide.round(5), "lon_centroide": d.lon_centroide.round(5),
        "municipios": d["Municípios Abrangidos"],
        "nome_oficial": d["Nome da UC"],
    }).sort_values(["categoria", "nome"])
    fora = ~dentro_do_brasil(out.lat, out.lon)
    print("fora da caixa do Brasil (mantidas, marinhas/oceânicas):", out[fora][["nome", "lat", "lon"]].to_string())
    print(out.categoria.value_counts())
    print("com visitação:", out.visitantes.notna().sum(), "| anos:", out.ano_visitacao.value_counts().to_dict())
    print("visitação sem casar com CNUC:", set(vis.codigo_uc) - set(out.codigo_uc))
    print("sem cod:", (out.cod == "").sum(), list(cm.falhas)[:10])
    print(out.sort_values("visitantes", ascending=False).head(10)[["nome", "visitantes", "ano_visitacao"]].to_string())
    out = cod_pelo_ponto(out, "primeiro_municipio_listado")
    salvar(out, "areas_protegidas.csv")


if __name__ == "__main__":
    main()
