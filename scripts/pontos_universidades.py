"""Instituições de ensino superior (INEP, Censo da Educação Superior 2024) -> dados/pontos/universidades.csv

- IES: MICRODADOS_ED_SUP_IES_2024.CSV (nome, sigla, município-sede, categoria, organização).
- matriculas: soma de QT_MAT dos cursos de graduação (MICRODADOS_CADASTRO_CURSOS_2024.CSV) por CO_IES,
  presencial + EaD. O arquivo de cursos (~450 MB) é agregado e apagado; fica só o agregado.
- programas_nota7: programas CAPES (Coleta Sucupira 2024) com CD_CONCEITO_PROGRAMA = 7,
  ligados pela chave CD_ENTIDADE_EMEC = CO_IES.
- lat/lon: sede do município da IES (dados/municipios.csv, Base de Localidades IBGE 2022);
  NÃO é o endereço do campus.
"""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402

from pontos_comum import BRUTOS, RAIZ, baixar, salvar  # noqa: E402

DIR = BRUTOS / "inep"
DIR.mkdir(exist_ok=True)
ANO = 2024
URL_INEP = f"https://download.inep.gov.br/microdados/microdados_censo_da_educacao_superior_{ANO}.zip"
URL_CAPES = ("https://dadosabertos.capes.gov.br/dataset/414275c0-2056-4a12-b1a6-b525b74850d5/resource/"
             "76ccbd76-7f3a-40c3-a4dc-7d6f65858db8/download/br-capes-colsucup-prog-2024-2025-12-01.csv")

CATEGORIA = {1: "pública federal", 2: "pública estadual", 3: "pública municipal",
             4: "privada com fins lucrativos", 5: "privada sem fins lucrativos", 7: "especial"}
ORGANIZACAO = {1: "universidade", 2: "centro universitário", 3: "faculdade",
               4: "instituto federal", 5: "centro federal de educação tecnológica"}


def arquivos_inep():
    ies = DIR / f"MICRODADOS_ED_SUP_IES_{ANO}.CSV"
    agreg = DIR / f"matriculas_por_ies_{ANO}.csv"
    if ies.exists() and agreg.exists():
        return ies, agreg
    z = DIR / f"microdados_censo_da_educacao_superior_{ANO}.zip"
    baixar(URL_INEP, z, timeout=3600)
    with zipfile.ZipFile(z) as zf:
        for n in zf.namelist():
            if n.endswith(f"MICRODADOS_ED_SUP_IES_{ANO}.CSV"):
                ies.write_bytes(zf.read(n))
            if n.endswith(f"MICRODADOS_CADASTRO_CURSOS_{ANO}.CSV"):
                with zf.open(n) as f:
                    cur = pd.read_csv(f, sep=";", encoding="latin1",
                                      usecols=["CO_IES", "TP_NIVEL_ACADEMICO", "TP_MODALIDADE_ENSINO", "QT_MAT", "QT_CURSO"])
    cur["QT_MAT"] = pd.to_numeric(cur.QT_MAT, errors="coerce").fillna(0)
    cur["pres"] = cur.QT_MAT.where(cur.TP_MODALIDADE_ENSINO == 1, 0)
    cur["ead"] = cur.QT_MAT.where(cur.TP_MODALIDADE_ENSINO == 2, 0)
    g = cur.groupby("CO_IES").agg(
        matriculas=("QT_MAT", "sum"), matriculas_presencial=("pres", "sum"),
        matriculas_ead=("ead", "sum"), cursos=("QT_MAT", "size"),
    ).reset_index()
    g.to_csv(agreg, index=False)
    return ies, agreg


def main():
    ies_csv, agreg_csv = arquivos_inep()
    d = pd.read_csv(ies_csv, sep=";", encoding="latin1", dtype=str)
    m = pd.read_csv(agreg_csv, dtype={"CO_IES": str})
    d = d.merge(m, on="CO_IES", how="left")

    capes = pd.read_csv(baixar(URL_CAPES, BRUTOS / "capes" / "br-capes-colsucup-prog-2024-2025-12-01.csv"),
                        sep=";", encoding="latin1", dtype=str)
    capes = capes[capes.DS_SITUACAO_PROGRAMA == "EM FUNCIONAMENTO"]
    n7 = capes[capes.CD_CONCEITO_PROGRAMA == "7"].groupby("CD_ENTIDADE_EMEC").size().rename("programas_nota7")
    n6 = capes[capes.CD_CONCEITO_PROGRAMA == "6"].groupby("CD_ENTIDADE_EMEC").size().rename("programas_nota6")
    ntot = capes.groupby("CD_ENTIDADE_EMEC").size().rename("programas_pos")
    pos = pd.concat([n7, n6, ntot], axis=1).fillna(0).astype(int).reset_index().rename(columns={"CD_ENTIDADE_EMEC": "CO_IES"})
    sem_ies = set(pos.CO_IES) - set(d.CO_IES)
    print("entidades CAPES sem IES no INEP:", len(sem_ies), "| programas nota 7 perdidos:",
          int(pos[pos.CO_IES.isin(sem_ies)].programas_nota7.sum()))
    d = d.merge(pos, on="CO_IES", how="left")

    mun = pd.read_csv(RAIZ / "dados" / "municipios.csv", dtype={"cod": str})[["cod", "lat", "lon"]]
    d["cod"] = d.CO_MUNICIPIO_IES.str.strip()
    d = d.merge(mun, on="cod", how="left")
    print("sem coordenada (descartadas):", d.lat.isna().sum())
    d = d.dropna(subset=["lat"])

    cat = pd.to_numeric(d.TP_CATEGORIA_ADMINISTRATIVA, errors="coerce").astype("Int64")
    org = pd.to_numeric(d.TP_ORGANIZACAO_ACADEMICA, errors="coerce").astype("Int64")
    out = pd.DataFrame({
        "nome": d.NO_IES.str.strip(),
        "sigla": d.SG_IES.fillna("").str.strip(),
        "lat": d.lat, "lon": d.lon,
        "cod": d.cod, "uf": d.SG_UF_IES,
        "municipio": d.NO_MUNICIPIO_IES,
        "categoria": cat.map(CATEGORIA),
        "publica": cat.isin([1, 2, 3]),
        "organizacao": org.map(ORGANIZACAO),
        "matriculas": d.matriculas.fillna(0).astype(int),
        "matriculas_presencial": d.matriculas_presencial.fillna(0).astype(int),
        "matriculas_ead": d.matriculas_ead.fillna(0).astype(int),
        "programas_pos": d.programas_pos.fillna(0).astype(int),
        "programas_nota6": d.programas_nota6.fillna(0).astype(int),
        "programas_nota7": d.programas_nota7.fillna(0).astype(int),
        "co_ies": d.CO_IES,
        "coord_metodo": "sede_municipal",
        "ano": ANO,
    }).sort_values("matriculas", ascending=False)
    print(out.categoria.value_counts(dropna=False).to_dict())
    print(out.organizacao.value_counts(dropna=False).to_dict())
    print(f"matrículas: {out.matriculas.sum():,}; nota 7: {out.programas_nota7.sum()}")
    print(out.sort_values("programas_nota7", ascending=False).head(8)[["sigla", "nome", "programas_nota7", "matriculas"]].to_string())
    salvar(out, "universidades.csv")


if __name__ == "__main__":
    main()
