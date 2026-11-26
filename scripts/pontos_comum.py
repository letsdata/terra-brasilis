"""Funções comuns aos scripts pontos_*.py (Terra Brasilis).

- Caminhos de dados brutos e limpos.
- Tabela de municípios do IBGE (API de localidades) para casar nome+UF com o código de 7 dígitos.
- Checagem de coordenadas dentro do Brasil.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
BRUTOS = RAIZ / "dados" / "brutos" / "pontos"
SAIDA = RAIZ / "dados" / "pontos"
BRUTOS.mkdir(parents=True, exist_ok=True)
SAIDA.mkdir(parents=True, exist_ok=True)

URL_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
UA = {"User-Agent": "terra-brasilis-dados/0.1"}


def baixar(url: str, destino: Path, timeout: int = 300, forcar: bool = False, **kw) -> Path:
    """Baixa um arquivo de dados (com cache local)."""
    if destino.exists() and destino.stat().st_size > 0 and not forcar:
        return destino
    for tentativa in range(3):
        try:
            r = requests.get(url, timeout=timeout, headers=UA, stream=True, **kw)
            r.raise_for_status()
            tmp = destino.with_suffix(destino.suffix + ".part")
            with open(tmp, "wb") as f:
                for bloco in r.iter_content(1 << 20):
                    f.write(bloco)
            tmp.rename(destino)
            return destino
        except Exception as e:  # noqa: BLE001
            print(f"  falha ao baixar {url} ({tentativa + 1}/3): {e}")
    raise RuntimeError(f"não foi possível baixar {url}")


def normalizar(txt: str) -> str:
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return ""
    t = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode()
    t = t.upper().replace("'", "").replace("`", "").replace("-", " ")
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# grafias alternativas comuns em bases federais -> grafia IBGE (normalizada)
ALIASES = {
    ("SP", "MOJI MIRIM"): "MOGI MIRIM",
    ("SP", "MOJI DAS CRUZES"): "MOGI DAS CRUZES",
    ("SP", "MOJI GUACU"): "MOGI GUACU",
    ("SP", "EMBU"): "EMBU DAS ARTES",
    ("SP", "SAO LUIS DO PARAITINGA"): "SAO LUIZ DO PARAITINGA",
    ("RN", "ACU"): "ASSU",
    ("RN", "ARES"): "AREZ",
    ("SP", "IPAUCU"): "IPAUSSU",
    ("MT", "POXOREO"): "POXOREU",
    ("RJ", "TRAJANO DE MORAIS"): "TRAJANO DE MORAES",
    ("RJ", "PARATI"): "PARATY",
    ("RN", "BOA SAUDE"): "JANUARIO CICCO",
    ("PB", "SANTAREM"): "JOCA CLAUDINO",
    ("PB", "SAO DOMINGOS DE POMBAL"): "SAO DOMINGOS",
    ("PE", "BELEM DE SAO FRANCISCO"): "BELEM DO SAO FRANCISCO",
    ("PE", "ILHA DE ITAMARACA"): "ITAMARACA",
    ("PE", "LAGOA DO ITAENGA"): "LAGOA DE ITAENGA",
    ("BA", "SANTA TERESINHA"): "SANTA TEREZINHA",
    ("TO", "SAO VALERIO DA NATIVIDADE"): "SAO VALERIO",
    ("TO", "COUTO DE MAGALHAES"): "COUTO MAGALHAES",
    ("MT", "SANTO ANTONIO DO LEVERGER"): "SANTO ANTONIO DE LEVERGER",
    ("MS", "BATAIPORA"): "BATAYPORA",
    ("PA", "ELDORADO DOS CARAJAS"): "ELDORADO DO CARAJAS",
    ("PA", "SANTA ISABEL DO PARA"): "SANTA IZABEL DO PARA",
    ("MG", "SAO THOME DAS LETRAS"): "SAO TOME DAS LETRAS",
    ("MG", "DONA EUSEBIA"): "DONA EUZEBIA",
    ("MG", "BRASOPOLIS"): "BRAZOPOLIS",
    ("MG", "PINGO D AGUA"): "PINGO DAGUA",
    ("MG", "PASSA VINTE"): "PASSA VINTE",
    ("RS", "SANTANA DO LIVRAMENTO"): "SANTANA DO LIVRAMENTO",
    ("SC", "PICARRAS"): "BALNEARIO PICARRAS",
    ("SC", "PRESIDENTE CASTELO BRANCO"): "PRESIDENTE CASTELLO BRANCO",
    ("SC", "SAO LOURENCO D OESTE"): "SAO LOURENCO DO OESTE",
    ("SC", "HERVAL D OESTE"): "HERVAL DOESTE",
    ("GO", "SAO LUIZ DO NORTE"): "SAO LUIZ DO NORTE",
    ("AM", "PARINTINS"): "PARINTINS",
}


def tabela_municipios() -> pd.DataFrame:
    destino = BRUTOS / "ibge_municipios.json"
    baixar(URL_MUNICIPIOS, destino)
    dados = json.loads(destino.read_text(encoding="utf-8"))
    linhas = []
    for m in dados:
        try:
            uf = m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
        except (TypeError, KeyError):
            uf = m["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]
        linhas.append({"cod": str(m["id"]), "municipio": m["nome"], "uf": uf, "chave": normalizar(m["nome"])})
    return pd.DataFrame(linhas)


class CasadorMunicipio:
    def __init__(self):
        t = tabela_municipios()
        self.tab = t
        self.mapa = {(r.uf, r.chave): r.cod for r in t.itertuples()}
        # sem espaços, para "D OESTE" vs "DOESTE"
        self.mapa_sem_espaco = {(r.uf, r.chave.replace(" ", "")): r.cod for r in t.itertuples()}
        self.nomes = dict(zip(t.cod, t.municipio))
        self.ufs = dict(zip(t.cod, t.uf))
        self.falhas: set[tuple[str, str]] = set()

    def cod(self, municipio, uf) -> str:
        if not isinstance(uf, str) or not uf.strip():
            return ""
        uf = uf.strip().upper()
        k = normalizar(municipio)
        if not k:
            return ""
        k = ALIASES.get((uf, k), k)
        c = self.mapa.get((uf, k)) or self.mapa_sem_espaco.get((uf, k.replace(" ", "")))
        if not c:
            # último recurso: grafia muito parecida dentro da mesma UF
            cands = [kk for (u, kk) in self.mapa if u == uf]
            m = difflib.get_close_matches(k, cands, n=1, cutoff=0.9)
            if m:
                c = self.mapa[(uf, m[0])]
        if not c:
            self.falhas.add((uf, str(municipio)))
            return ""
        return c


def dentro_do_brasil(lat, lon) -> pd.Series:
    lat = pd.to_numeric(lat, errors="coerce")
    lon = pd.to_numeric(lon, errors="coerce")
    return lat.between(-34, 6) & lon.between(-74, -28)


def num_br(s: pd.Series) -> pd.Series:
    """Converte números no formato brasileiro ("1.234,56") para float."""
    s = s.astype(str).str.strip().str.replace(" ", "", regex=False)
    tem_virgula = s.str.contains(",", regex=False)
    s = s.where(~tem_virgula, s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    return pd.to_numeric(s.replace({"": None, "nan": None, "None": None}), errors="coerce")


def salvar(df: pd.DataFrame, nome: str) -> Path:
    destino = SAIDA / nome
    df.to_csv(destino, index=False, encoding="utf-8")
    print(f"gravado {destino} ({len(df)} linhas)")
    return destino


# --- código IBGE pelo ponto (fallback) -------------------------------------------------------
# Usa a malha municipal do IBGE já baixada por scripts/ibge_base.py
# (dados/brutos/ibge/api_malhas_BR_municipio_intermediaria.geojson). Se não existir, devolve "".
MALHA_MUN = RAIZ / "dados" / "brutos" / "ibge" / "api_malhas_BR_municipio_intermediaria.geojson"
_indice = None


def _carregar_malha():
    global _indice
    if _indice is None:
        from shapely.geometry import shape
        from shapely.strtree import STRtree
        if not MALHA_MUN.exists():
            _indice = (None, [], [])
            return _indice
        g = json.loads(MALHA_MUN.read_text(encoding="utf-8"))
        geoms = [shape(f["geometry"]) for f in g["features"]]
        cods = [str(f["properties"]["codarea"]) for f in g["features"]]
        _indice = (STRtree(geoms), geoms, cods)
    return _indice


def cod_por_ponto(lat, lon) -> str:
    from shapely.geometry import Point
    arvore, geoms, cods = _carregar_malha()
    if arvore is None or lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
        return ""
    p = Point(float(lon), float(lat))
    for i in arvore.query(p, predicate="intersects"):
        return cods[int(i)]
    return ""


def completar_cod(df: pd.DataFrame, metodo_existente="nome_municipio", col_lat="lat", col_lon="lon") -> pd.DataFrame:
    """Preenche 'cod' vazio pelo polígono municipal que contém o ponto; marca em 'cod_metodo'."""
    df = df.copy()
    if "cod_metodo" not in df:
        df["cod_metodo"] = df["cod"].map(lambda c: metodo_existente if isinstance(c, str) and c else "")
    vazio = ~df["cod"].map(lambda c: isinstance(c, str) and bool(c))
    novos = [cod_por_ponto(a, b) for a, b in zip(df.loc[vazio, col_lat], df.loc[vazio, col_lon])]
    df.loc[vazio, "cod"] = novos
    df.loc[vazio, "cod_metodo"] = ["ponto_no_poligono" if c else "" for c in novos]
    return df


def cod_pelo_ponto(df: pd.DataFrame, metodo_declarado: str) -> pd.DataFrame:
    """'cod' passa a ser o município que contém o ponto; o código vindo da fonte (casado pelo nome)
    fica em 'cod_declarado'. Sem polígono (ponto no mar/fronteira), mantém o declarado."""
    df = df.copy()
    df["cod_declarado"] = df["cod"]
    pip = [cod_por_ponto(a, b) for a, b in zip(df["lat"], df["lon"])]
    df["cod"] = [p or c for p, c in zip(pip, df["cod_declarado"])]
    df["cod_metodo"] = ["ponto_no_poligono" if p else (metodo_declarado if c else "") for p, c in zip(pip, df["cod_declarado"])]
    return df
