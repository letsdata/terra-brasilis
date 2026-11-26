"""Patrimônio Mundial da UNESCO no Brasil (Wikidata SPARQL) -> dados/pontos/patrimonio_unesco.csv

Duas consultas ao Wikidata (o serviço limita a 1 consulta/min; as respostas ficam em cache em
dados/brutos/pontos/):
  1) itens com P1435 = Q9259 (Patrimônio Mundial), P17 = Brasil e P757 (ID do Patrimônio Mundial);
  2) detalhes (rótulos pt/en, critérios P2614, município P131 com código IBGE P1585).

A lista do Wikidata mistura sítios e componentes; a escolha de UM item por sítio (pelo ID base da
UNESCO) está na tabela SITIOS abaixo. Tipo vem dos critérios: (i)-(vi) cultural, (vii)-(x) natural,
os dois = misto.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from pontos_comum import BRUTOS, CasadorMunicipio, dentro_do_brasil, salvar, completar_cod  # noqa: E402

ENDPOINT = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "TerraBrasilisBot/0.1 (data research)", "Accept": "application/sparql-results+json"}

Q_LISTA = """SELECT ?item ?itemLabel ?idUnesco ?inicio ?coord WHERE { ?item p:P1435 ?st . ?st ps:P1435 wd:Q9259 .
 ?item wdt:P17 wd:Q155 . ?item wdt:P757 ?idUnesco . OPTIONAL { ?st pq:P580 ?inicio . }
 OPTIONAL { ?item wdt:P625 ?coord . } SERVICE wikibase:label { bd:serviceParam wikibase:language "pt,en". } }"""

# id_base: (item Wikidata escolhido, UF principal, município-sede para o código IBGE ou None, lon preferida)
SITIOS = {
    "124": ("Q3845692", "MG", "Ouro Preto", None),
    "189": ("Q8343764", "PE", "Olinda", None),
    "275": ("Q465960", "RS", "São Miguel das Missões", None),  # transfronteiriço; componente brasileiro
    "309": ("Q5572706", "BA", "Salvador", None),
    "334": ("Q1595417", "MG", "Congonhas", None),
    "355": ("Q742315", "PR", "Foz do Iguaçu", -53.95),
    "445": ("Q3391360", "DF", "Brasília", None),
    "606": ("Q267394", "PI", "São Raimundo Nonato", None),
    "821": ("Q8343768", "MA", "São Luís", None),
    "890": ("Q8343760", "MG", "Diamantina", None),
    "892": ("Q2487302", "BA", None, -39.25),
    "893": ("Q2521895", "SP", None, None),
    "993": ("Q8343761", "GO", "Goiás", None),
    "998": ("Q2990490", "AM", None, None),
    "999": ("Q99237891", "MT", None, None),  # sem coordenada no item: usa a de Q157603 (Pantanal)
    "1000": ("Q15224654", "PE", "Fernando de Noronha", None),
    "1035": ("Q137787234", "GO", None, -47.412),
    "1100": ("Q3374972", "RJ", "Rio de Janeiro", None),
    "1272": ("Q7214285", "SE", "São Cristóvão", None),
    "1308": ("Q66057630", "RJ", "Paraty", None),
    "1493": ("Q9850285", "MG", "Belo Horizonte", None),
    "1548": ("Q20048515", "RJ", "Rio de Janeiro", None),
    "1611": ("Q647777", "MA", "Barreirinhas", None),
    "1620": ("Q56695607", "RJ", "Rio de Janeiro", None),
    "1747": ("Q5055056", "MG", "Januária", None),
    "1774": ("Q65561204", "AM", "Manaus", -60.023397222),  # dois teatros: Manaus e Belém
}
COORD_SUBSTITUTA = {"Q99237891": "Q157603"}
NOME_PT_FALTANTE = {
    # item sem rótulo em português no Wikidata: nome oficial em português usado pelo IPHAN/ICMBio
    "Q137787234": "Áreas Protegidas do Cerrado: Parques Nacionais da Chapada dos Veadeiros e das Emas",
}
NOTAS = {
    "1747": "No Wikidata o ID 1747 está no item da APA Cavernas do Peruaçu (o do Parque Nacional traz ID 1035, erro).",
    "1774": "Inscrição de 2026 segundo o Wikidata; não conferida na lista oficial (whc.unesco.org bloqueia acesso automatizado).",
    "275": "Sítio transfronteiriço (Argentina e Brasil); coordenada de São Miguel das Missões (RS).",
    "999": "Coordenada do item Q157603 (Pantanal), pois o item do sítio não tem P625.",
}


def sparql(consulta: str, destino: Path) -> list[dict]:
    if not destino.exists():
        for t in range(3):
            r = requests.get(ENDPOINT, params={"query": consulta}, headers=UA, timeout=120)
            if r.ok and r.text.lstrip().startswith("{"):
                destino.write_text(r.text, encoding="utf-8")
                break
            print("Wikidata recusou (limite de 1 consulta/min?), nova tentativa em 65 s")
            time.sleep(65)
        else:
            raise RuntimeError("Wikidata indisponível")
    return json.loads(destino.read_text(encoding="utf-8"))["results"]["bindings"]


def ponto(wkt: str):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", wkt or "")
    return (float(m.group(2)), float(m.group(1))) if m else (None, None)


def main():
    lista = sparql(Q_LISTA, BRUTOS / "wikidata_unesco_lista.json")
    itens = " ".join(f"wd:{q}" for q in {v[0] for v in SITIOS.values()} | set(COORD_SUBSTITUTA.values()))
    q_det = ("SELECT ?item ?pt ?en ?critLabel ?munLabel ?cod ?instLabel WHERE { VALUES ?item { " + itens + " } "
             'OPTIONAL { ?item rdfs:label ?pt . FILTER(LANG(?pt)="pt") } OPTIONAL { ?item rdfs:label ?en . FILTER(LANG(?en)="en") } '
             "OPTIONAL { ?item wdt:P2614 ?crit . } OPTIONAL { ?item wdt:P131 ?mun . OPTIONAL { ?mun wdt:P1585 ?cod . } } "
             'OPTIONAL { ?item wdt:P31 ?inst . } SERVICE wikibase:label { bd:serviceParam wikibase:language "pt,en". } }')
    det = sparql(q_det, BRUTOS / "wikidata_unesco_detalhes.json")

    coords, anos = {}, {}
    for b in lista:
        q = b["item"]["value"].rsplit("/", 1)[-1]
        if "coord" in b:
            coords.setdefault(q, []).append(ponto(b["coord"]["value"]))
        if "inicio" in b:
            anos.setdefault(q, set()).add(int(b["inicio"]["value"][:4]))
    info = {}
    for b in det:
        q = b["item"]["value"].rsplit("/", 1)[-1]
        i = info.setdefault(q, {"crit": set()})
        for k in ("pt", "en"):
            if k in b:
                i[k] = b[k]["value"]
        if "critLabel" in b:
            i["crit"].add(b["critLabel"]["value"])

    romano = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}
    cm = CasadorMunicipio()
    linhas = []
    for idb, (q, uf, mun, lon_pref) in SITIOS.items():
        i = info.get(q, {"crit": set()})
        cs = coords.get(COORD_SUBSTITUTA.get(q, q), [])
        if lon_pref is not None:
            cs = sorted(cs, key=lambda c: abs(c[1] - lon_pref))
        lat, lon = cs[0] if cs else (None, None)
        nums = sorted(romano[c.strip("()")] for c in i["crit"] if c.strip("()") in romano)
        cult, nat = any(n <= 6 for n in nums), any(n >= 7 for n in nums)
        tipo = "misto" if cult and nat else "cultural" if cult else "natural" if nat else ""
        ano = min(anos.get(q, {None}) - {None}, default=None)
        linhas.append({
            "nome": i.get("pt") or NOME_PT_FALTANTE.get(q, ""),
            "nome_en": i.get("en", ""),
            "lat": lat, "lon": lon,
            "cod": cm.cod(mun, uf) if mun else "",
            "uf": uf,
            "tipo": tipo,
            "criterios": ",".join(f"({k})" for k, n in sorted(romano.items(), key=lambda x: x[1]) if n in nums),
            "ano_inscricao": ano,
            "id_unesco": idb,
            "wikidata": q,
            "nota": NOTAS.get(idb, ""),
        })
    d = pd.DataFrame(linhas).sort_values("ano_inscricao")
    d["ano_inscricao"] = d.ano_inscricao.astype("Int64")
    assert dentro_do_brasil(d.lat, d.lon).all() or print(d[~dentro_do_brasil(d.lat, d.lon)])
    print(d[["nome", "tipo", "ano_inscricao", "lat", "lon", "cod"]].to_string())
    d = completar_cod(d)
    salvar(d, "patrimonio_unesco.csv")


if __name__ == "__main__":
    main()
