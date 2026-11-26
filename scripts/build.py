"""Junta todos os dados na grade e gera os JSON da página (web/dados/).

Entradas: dados/grade.csv, dados/elevacao.csv, dados/municipios.csv, dados/social.csv,
dados/empregos.csv, dados/cobertura.csv, dados/agro.csv, dados/pontos/*.csv e as malhas
do IBGE em dados/brutos/ibge/. Arquivos que faltarem são pulados.

Uso: .venv/bin/python scripts/build.py
"""
import csv, json, math, re, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
import shapely.prepared
from pyproj import Transformer
from shapely.geometry import shape, Polygon, Point, box
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grade import R, PROJ, centro, poligono, VIZ  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
D = RAIZ / "dados"
OUT = RAIZ / "web/dados"
OUT.mkdir(parents=True, exist_ok=True)
fwd = Transformer.from_crs("EPSG:4326", PROJ, always_xy=True)


def proj_geom(g):
    return shapely.transform(g, lambda c: np.column_stack(fwd.transform(c[:, 0], c[:, 1])))


def ler(nome, **kw):
    p = D / nome
    if not p.exists():
        print("  (sem", nome + ")")
        return None
    return pd.read_csv(p, **kw)


def r2(x, n=2):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), n)


# ---------------------------------------------------------------- municípios
print("municípios")
mun = pd.read_csv(D / "municipios.csv")
mun = mun.sort_values("cod").reset_index(drop=True)
ufs = pd.read_csv(D / "ufs.csv").sort_values("cod").reset_index(drop=True)
uf_idx = {s: i for i, s in enumerate(ufs.sigla)}
mi = {c: i for i, c in enumerate(mun.cod)}
NM = len(mun)
col = {}
meta = {}
mil = 1000.0
col["pop"] = mun.pop2022.astype(float)
col["area"] = mun.area_km2.astype(float)
for k in ["pib", "va_agro", "va_ind", "va_serv", "va_adm", "impostos"]:
    col[k] = mun[k].astype(float) * mil
meta["ano_pib"] = str(int(mun.pib_ano.dropna().iloc[0])) if "pib_ano" in mun else ""
col["pibpc"] = col["pib"] / col["pop"]
col["pib_va"] = mun.pib_va.astype(float) * mil
meta["ano_va"] = str(int(mun.va_ano.dropna().iloc[0]))
col["dens"] = col["pop"] / col["area"]

soc = ler("social.csv")
if soc is not None:
    soc = soc.set_index("cod").reindex(mun.cod)
    mapa = {"alfabetizacao_15mais": "alfab", "superior_25mais": "superior", "renda_pc": "renda",
            "religiao_catolica": "rel_cat", "religiao_evangelica": "rel_evan", "religiao_sem": "rel_sem",
            "religiao_espirita": "rel_esp", "religiao_afro": "rel_afro", "esgoto_rede": "esgoto",
            "agua_rede": "agua", "idade_mediana": "idade", "pct_indigena": "pct_indig", "pct_quilombola": "pct_quil"}
    for a, b in mapa.items():
        if a in soc:
            col[b] = soc[a].astype(float).values
    meta["ano_religiao"] = "Censo " + str(int(soc["ano_religiao"].dropna().iloc[0])) if "ano_religiao" in soc and soc["ano_religiao"].notna().any() else "Censo 2022"
    if "superior" in col:
        # pessoas com superior: % de 25+ aplicada à população 25+ não está disponível; usa população total como aproximação? Não.
        pass

idh = ler("idhm.csv")
if idh is not None:
    idh = idh.set_index("cod").reindex(mun.cod)
    col["idhm"] = idh["idhm"].astype(float).values

des = ler("desastres.csv")
if des is not None:
    des = des.set_index("cod").reindex(mun.cod)
    for a, b in [("total", "desastres"), ("seca_estiagem", "des_seca"), ("inundacao_enxurrada_alagamento", "des_chuva"), ("chuvas_intensas", "des_chuvas_int")]:
        if a in des and b not in col:
            col[b] = des[a].astype(float).values
    meta["anos_desastres"] = f"{int(des['ano_inicio'].dropna().iloc[0])}–{int(des['ano_fim'].dropna().iloc[0])}" if "ano_inicio" in des else ""

cob = ler("cobertura.csv")
if cob is not None:
    cob = cob.set_index("cod").reindex(mun.cod)
    tot = cob[["floresta", "savana_campo", "pastagem", "agricultura", "silvicultura", "mosaico", "urbano", "mineracao", "agua", "outros"]].sum(axis=1)
    for a, b in [("floresta", "flor_pct"), ("savana_campo", "sav_pct"), ("pastagem", "past_pct"), ("agricultura", "agri_pct"),
                 ("silvicultura", "silv_pct"), ("urbano", "urb_pct"), ("agua", "agua_pct"), ("mosaico", "mos_pct")]:
        col[b] = (cob[a] / tot * 100).values
    col["perda_flor"] = np.where(cob.floresta_1985 > 100, (1 - cob.floresta / cob.floresta_1985).clip(lower=0) * 100, np.nan)
    col["flor_ha"] = cob.floresta.values
    meta["ano_cobertura"] = str(int(cob.ano.dropna().iloc[0]))
    COB = {k: (cob[k] / tot).fillna(0).values for k in ["floresta", "savana_campo", "pastagem", "agricultura", "silvicultura", "mosaico", "urbano", "agua"]}
else:
    COB = None

# empregos por seção
emp = ler("empregos.csv")
EMP = None
if emp is not None:
    emp["v"] = emp.pessoal_ocupado.fillna(emp.assalariados)
    secoes = sorted(s for s in emp.secao.dropna().unique() if s != "Total" and len(str(s)) == 1)
    desc = emp.drop_duplicates("secao").set_index("secao").descricao.to_dict()
    piv = emp[emp.secao.isin(secoes)].pivot_table(index="cod", columns="secao", values="v", aggfunc="sum").reindex(mun.cod)
    vals = piv[secoes].values
    EMP = {"ano": str(int(emp.ano.dropna().iloc[0])), "secoes": [{"l": s, "d": CURTO.get(s, desc[s]) if (CURTO := {
        "A": "Agropecuária e pesca", "B": "Indústria extrativa", "C": "Indústria de transformação", "D": "Eletricidade e gás",
        "E": "Água, esgoto e resíduos", "F": "Construção", "G": "Comércio", "H": "Transporte e armazenagem",
        "I": "Hotéis e restaurantes", "J": "Informação e comunicação", "K": "Finanças e seguros", "L": "Atividades imobiliárias",
        "M": "Serviços técnicos e científicos", "N": "Serviços administrativos", "O": "Administração pública",
        "P": "Educação", "Q": "Saúde", "R": "Artes, cultura e esporte", "S": "Outros serviços", "T": "Serviço doméstico",
        "U": "Organismos internacionais"}) else desc[s]} for s in secoes],
        "v": [[int(x) if x == x else 0 for x in row] if not np.all(np.isnan(row)) else None for row in vals]}
    EMP["br"] = [int(np.nansum(vals[:, k])) for k in range(len(secoes))]
    tot_row = emp[emp.secao == "Total"].set_index("cod").v.reindex(mun.cod).values
    col["empregos"] = np.where(np.isfinite(tot_row), tot_row, np.nansum(vals, axis=1))
    if "J" in secoes and "M" in secoes:
        col["ciencia"] = np.nan_to_num(vals[:, secoes.index("J")]) + np.nan_to_num(vals[:, secoes.index("M")])
    if "R" in secoes:
        col["cultura"] = np.nan_to_num(vals[:, secoes.index("R")])

# graduados (ciência): % superior aplicado à população de 25+ não está aqui; usa matrículas se houver
# energia por município (usinas)
PTS_DIR = D / "pontos"

# agro
agro = ler("agro.csv")
AGRO = None
ICONE_AGRO = {"soja": "🫘", "milho": "🌽", "cana": "🎋", "café": "☕", "cafe": "☕", "laranja": "🍊", "algodão": "🧶", "algodao": "🧶",
              "arroz": "🍚", "feijão": "🫘", "mandioca": "🥔", "cacau": "🍫", "uva": "🍇", "banana": "🍌", "trigo": "🌾",
              "fumo": "🍂", "tabaco": "🍂", "açaí": "🫐", "acai": "🫐", "castanha": "🌰", "erva-mate": "🧉", "madeira": "🪵",
              "maçã": "🍎", "batata": "🥔", "tomate": "🍅", "mamão": "🥭", "manga": "🥭", "abacaxi": "🍍", "coco": "🥥",
              "borracha": "🌳", "eucalipto": "🌲", "pinus": "🌲", "leite": "🥛", "bovino": "🐄", "suíno": "🐖", "galin": "🐔",
              "carvão": "🔥", "lenha": "🪵", "sorgo": "🌾", "melancia": "🍉", "cebola": "🧅", "alho": "🧄", "pimenta": "🌶",
              "babaçu": "🌴", "piaçava": "🌴", "carnaúba": "🌴", "guaraná": "🍒", "dendê": "🌴", "girassol": "🌻", "amendoim": "🥜"}


def icone_agro(p):
    p = str(p).lower()
    for k, v in ICONE_AGRO.items():
        if k in p:
            return v
    return "🌱"


if agro is not None:
    ag = agro[agro.valor_mil_reais.fillna(0) > 0].copy()
    ag["valor"] = ag.valor_mil_reais * mil
    ag["nome"] = ag.produto.astype(str).str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
    meta["ano_agro"] = str(int(ag.ano.max()))
    top = defaultdict(list)
    for cod, g in ag.sort_values("valor", ascending=False).groupby("cod"):
        if cod in mi:
            top[mi[cod]] = [[n, round(v), icone_agro(n)] for n, v in zip(g.nome.head(5), g.valor.head(5))]
    AGRO = {"ano": meta["ano_agro"], "top": [top.get(i, []) for i in range(NM)]}
    col["agro_valor"] = ag.groupby("cod").valor.sum().reindex(mun.cod).values

# ---------------------------------------------------------------- pontos
print("pontos")
pontos = []
REGRAS = []


MIN = {"de", "do", "da", "dos", "das", "e", "d'"}


def bonito(n):
    n = str(n).replace("_", " ")
    if n.upper() != n:
        return n
    t = " ".join(w.capitalize() if i == 0 or w.lower() not in MIN else w.lower() for i, w in enumerate(n.lower().split()))
    return re.sub(r"/(\w)", lambda m: "/" + m.group(1).upper(), t)


def add_ponto(t, nome, lat, lon, v, ic, d="", f="c", z=2, mar=False, regra="", vt=None, cod=None):
    if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))) or lat != lat or lon != lon:
        return
    x, y = fwd.transform(lon, lat)
    pontos.append({"t": t, "n": str(nome), "lat": lat, "lon": lon, "x": round(x, 2), "y": round(y, 2), "v": r2(v, 1) if v is not None else None,
                   "ic": ic, "d": d, "f": f, "z": z, "mar": 1 if mar else 0, "regra": regra, "vt": vt,
                   "cod": int(cod) if cod is not None and cod == cod else None})


ICONE_USINA = {"UHE": "💧", "PCH": "💧", "CGH": "💧", "UTE": "🔥", "EOL": "🌬", "UFV": "☀", "UTN": "☢"}
NOME_USINA = {"UHE": "Hidrelétrica", "PCH": "Pequena hidrelétrica", "CGH": "Microcentral hidrelétrica", "UTE": "Termelétrica",
              "EOL": "Eólica", "UFV": "Solar", "UTN": "Nuclear"}
us = ler("pontos/usinas.csv")
energia_mun = defaultdict(float)
if us is not None:
    us = us.sort_values("potencia_mw", ascending=False)
    top_us = set(us.head(5).index)
    for ix, u in us.iterrows():
        mw = float(u.potencia_mw)
        z = 0 if mw >= 3000 else 1 if mw >= 500 else 2 if mw >= 150 else 3 if mw >= 30 else 4
        comb = f" · {u.combustivel}" if u.tipo == "UTE" and isinstance(u.combustivel, str) else ""
        add_ponto("usina", u.nome, u.lat, u.lon, mw, ICONE_USINA.get(u.tipo, "⚡"), NOME_USINA.get(u.tipo, u.tipo) + comb, "mw", z,
                  ix in top_us, "Grande Usina: as cinco maiores usinas em operação no Brasil por potência (ANEEL)", cod=u.cod)
        if u.cod == u.cod and int(u.cod) in mi:
            energia_mun[mi[int(u.cod)]] += mw
    col["energia_mw"] = np.array([energia_mun.get(i, 0.0) for i in range(NM)])
    REGRAS.append("Grande Usina: as cinco maiores usinas em operação por potência instalada (ANEEL/SIGA).")

un = ler("pontos/patrimonio_unesco.csv")
if un is not None:
    for _, u in un.iterrows():
        ic = "🏞" if str(u.tipo).startswith("nat") else "🏛"
        add_ponto("unesco", u.nome, u.lat, u.lon, None, ic, f"Patrimônio Mundial da Unesco ({u.tipo}, {int(u.ano_inscricao)})", z=0, mar=True,
                  regra="Patrimônio Mundial: todo sítio brasileiro inscrito na lista da Unesco", cod=u.cod)
    REGRAS.append("Patrimônio Mundial: todos os sítios brasileiros na lista do Patrimônio Mundial da Unesco.")

nomes_unesco = set(un.nome) if un is not None else set()
ap = ler("pontos/areas_protegidas.csv")
if ap is not None:
    if "visitantes" in ap:
        parques = ap[ap.categoria.astype(str).str.contains("Parque", case=False)].sort_values("visitantes", ascending=False)
        top_par = set(parques.dropna(subset=["visitantes"]).head(10).index)
    else:
        top_par = set()
    for ix, a in ap.iterrows():
        cat = str(a.categoria)
        vis = a.visitantes if "visitantes" in ap and a.visitantes == a.visitantes else None
        parque = "Parque" in cat
        area = a.area_km2 if "area_km2" in ap else None
        z = 1 if (area or 0) > 20000 or (vis or 0) > 100000 else 2 if parque else 3
        add_ponto("uc", a.nome, a.lat, a.lon, vis if vis else area, "🌳" if parque else "🍃",
                  cat + (f" · {area:,.0f} km²".replace(",", ".") if area == area and area else ""), "int" if vis else "km2", z,
                  ix in top_par and a.nome not in nomes_unesco, "Parque Nacional mais visitado: os dez parques nacionais com mais visitantes no último ano publicado pelo ICMBio",
                  vt=(f"{int(vis):,} visitantes".replace(",", ".") if vis else None), cod=a.get("cod"))
    if top_par:
        REGRAS.append("Parque famoso: os dez parques nacionais com mais visitantes no último ano publicado pelo ICMBio.")

ae = ler("pontos/aeroportos.csv")
if ae is not None:
    pas = "passageiros" if "passageiros" in ae else None
    if pas:
        ae = ae.sort_values(pas, ascending=False)
    top_ae = set(ae.dropna(subset=[pas]).head(5).index) if pas else set()
    for ix, a in ae.iterrows():
        p = a[pas] if pas and a[pas] == a[pas] else None
        if not p:
            continue
        z = 0 if p >= 10e6 else 1 if p >= 2e6 else 2 if p >= 3e5 else 3
        icao = a.get("icao", "")
        nm = bonito(str(a.nome).split(" - ")[0])
        add_ponto("aeroporto", "Aeroporto " + nm if "aeroporto" not in nm.lower() else nm, a.lat, a.lon, p, "✈", f"{bonito(a.nome)} ({icao})", "int", z, ix in top_ae,
                  "Grande Aeroporto: os cinco aeroportos com mais passageiros (ANAC)", vt=f"{compact(p) if False else ''}", cod=a.get("cod"))
        pontos[-1]["vt"] = f"{p/1e6:.1f} mi de passageiros".replace(".", ",") if p >= 1e6 else f"{int(p):,} passageiros".replace(",", ".")
    if top_ae:
        REGRAS.append("Grande Aeroporto: os cinco aeroportos com mais passageiros no ano (ANAC).")

po = ler("pontos/portos.csv")
if po is not None:
    ton = "toneladas" if "toneladas" in po else None
    if ton:
        po = po.sort_values(ton, ascending=False)
    top_po = set(po.dropna(subset=[ton]).head(5).index) if ton else set()
    for ix, a in po.iterrows():
        t = a[ton] if ton and a[ton] == a[ton] else None
        if not t:
            continue
        z = 0 if t >= 50e6 else 1 if t >= 10e6 else 2 if t >= 1e6 else 3
        add_ponto("porto", a.nome, a.lat, a.lon, t, "⚓", str(a.get("tipo", "Porto")), "c", z, ix in top_po,
                  "Grande Porto: as cinco instalações com mais carga movimentada (ANTAQ)",
                  vt=f"{t/1e6:.1f} mi de toneladas".replace(".", ","), cod=a.get("cod"))
    if top_po:
        REGRAS.append("Grande Porto: as cinco instalações portuárias com mais carga movimentada no ano (ANTAQ).")

pe = ler("pontos/petroleo.csv")
if pe is not None:
    vcol = next((c for c in pe.columns if "boe" in c or "producao" in c or "petroleo" in c), None)
    if vcol:
        pe = pe.sort_values(vcol, ascending=False)
        for k, (ix, a) in enumerate(pe.iterrows()):
            v = a[vcol] if a[vcol] == a[vcol] else None
            if not v:
                continue
            add_ponto("petroleo", "Campo de " + bonito(a.nome), a.lat, a.lon, v, "🛢",
                      f"Petróleo e gás · bacia de {a.bacia}" + (f" · lâmina d'água de {int(a.lamina_dagua_m):,} m".replace(",", ".") if a.get("lamina_dagua_m") == a.get("lamina_dagua_m") and a.get("lamina_dagua_m") else ""),
                      "c", 1 if k < 10 else 2 if k < 40 else 3,
                      k < 3, "Grande Campo: os três campos de petróleo e gás com maior produção (ANP)",
                      vt=f"{v / 1000:,.0f} mil barris de óleo equivalente por dia".replace(",", "."), cod=a.get("cod"))
        REGRAS.append("Grande Campo: os três campos de petróleo e gás com maior produção (ANP).")

un2 = ler("pontos/universidades.csv")
if un2 is not None and "lat" in un2:
    mcol = "matriculas" if "matriculas" in un2 else None
    if mcol:
        un2 = un2.sort_values(mcol, ascending=False)
    n7 = "programas_nota7" if "programas_nota7" in un2 else None
    top_u = set(un2.sort_values(n7, ascending=False).dropna(subset=[n7]).head(8).index) if n7 else set(un2.head(8).index)
    for ix, a in un2.iterrows():
        if "organizacao" in un2 and "niversidade" not in str(a.organizacao):
            continue
        m = a[mcol] if mcol and a[mcol] == a[mcol] else None
        z = 1 if (m or 0) > 40000 else 2 if (m or 0) > 10000 else 3
        nome = a.get("sigla") if isinstance(a.get("sigla"), str) and len(str(a.nome)) > 34 else bonito(a.nome)
        add_ponto("universidade", nome, a.lat, a.lon, m, "🎓", bonito(a.nome), "int", z, ix in top_u,
                  "Grande Universidade: as oito universidades com mais programas de pós-graduação nota 7 na CAPES" if n7 else
                  "Grande Universidade: as oito universidades com mais matrículas",
                  vt=(f"{int(m):,} matrículas".replace(",", ".") if m else None), cod=a.get("cod"))
        pontos[-1]["x"] += round(R * 0.7, 2); pontos[-1]["y"] -= round(R * 0.7, 2)
    REGRAS.append("Grande Universidade: as oito universidades com mais programas nota 7 na CAPES." if n7 else
                  "Grande Universidade: as oito universidades com mais matrículas (INEP).")

mn = ler("pontos/mineracao_municipio.csv")
SUBST = None
if mn is not None:
    mn = mn.set_index("cod").reindex(mun.cod)
    col["cfem"] = mn.cfem_reais.astype(float).values
    SUBST = [s if isinstance(s, str) else None for s in mn.substancia_principal]
    meta["ano_cfem"] = str(int(mn["ano"].dropna().iloc[0])) if "ano" in mn else ""

# recursos do agro como pontos: os 25 maiores municípios de cada produto principal
if agro is not None:
    PRODS = ag.groupby("nome").valor.sum().sort_values(ascending=False).head(22).index
    for p in PRODS:
        g = ag[ag.nome == p].sort_values("valor", ascending=False).head(25)
        for k, (_, a) in enumerate(g.iterrows()):
            if a.cod not in mi:
                continue
            i = mi[a.cod]
            add_ponto("agro", f"{p} de {mun.nome[i]}", float(mun.lat[i]), float(mun.lon[i]), a.valor, icone_agro(p),
                      f"{k + 1}º maior produtor do Brasil", "brl", 2 if k < 5 else 3, cod=a.cod)
            # desloca um pouco para não cobrir a cidade
            pontos[-1]["x"] += round(R * 0.9 * math.cos(sum(map(ord, p)) % 6), 2)
            pontos[-1]["y"] += round(R * 0.9 * math.sin(sum(map(ord, p)) % 6), 2)

if agro is not None:
    bov = agro[(agro.produto == "Bovino") & (agro.quantidade.fillna(0) > 0)].sort_values("quantidade", ascending=False).head(25)
    for k, (_, a) in enumerate(bov.iterrows()):
        if a.cod not in mi:
            continue
        i = mi[a.cod]
        add_ponto("agro", f"Gado de {mun.nome[i]}", float(mun.lat[i]), float(mun.lon[i]), a.quantidade, "🐄",
                  f"{k + 1}º maior rebanho bovino do Brasil", "int", 2 if k < 5 else 3, vt=f"{int(a.quantidade):,} cabeças".replace(",", "."), cod=a.cod)
        pontos[-1]["x"] -= round(R * 0.8, 2)
    col["bovinos"] = agro[agro.produto == "Bovino"].groupby("cod").quantidade.sum().reindex(mun.cod).values

# ---------------------------------------------------------------- grade e pesos
print("grade")
gr = pd.read_csv(D / "grade.csv")
el = ler("elevacao.csv")
elev = {}
if el is not None:
    elev = {(q, r): e for q, r, e in zip(el.q, el.r, el.elev)}
NH = len(gr)
hq, hr = gr.q.values, gr.r.values
hidx = {(q, r): i for i, (q, r) in enumerate(zip(hq, hr))}
terra = gr.terra.values > 0

print("  malha municipal")
gj = json.load(open(D / "brutos/ibge/municipios.geojson"))
geoms = [None] * NM
for f in gj["features"]:
    c = int(f["properties"]["cod"])
    if c in mi:
        geoms[mi[c]] = proj_geom(shape(f["geometry"]).buffer(0))
faltam = [mun.nome[i] for i in range(NM) if geoms[i] is None]
print("  sem geometria:", faltam[:5], len(faltam))
validos = [i for i in range(NM) if geoms[i] is not None]
tree = STRtree([geoms[i] for i in validos])
area_mun = {i: geoms[i].area for i in validos}

w_h, w_m, w_s = [], [], []
hex_mun = np.full(NH, -1)
hex_fr = defaultdict(list)
for h in range(NH):
    if not terra[h]:
        continue
    pol = poligono(hq[h], hr[h])
    best, bf = -1, 0
    for j in tree.query(pol, predicate="intersects"):
        i = validos[j]
        a = geoms[i].intersection(pol).area
        if a <= 0:
            continue
        w_h.append(h); w_m.append(i); w_s.append(a / area_mun[i])
        hex_fr[h].append((i, a / pol.area))
        if a > bf:
            best, bf = i, a
    if best < 0:
        # ilha fora da malha simplificada: município mais próximo
        cx, cy = centro(hq[h], hr[h])
        j = tree.nearest(Point(cx, cy))
        best = validos[j]
        hex_fr[h].append((best, 1.0))
    hex_mun[h] = best
# municípios pequenos que não ganharam nenhum hexágono: soma garantida pelos pesos; checa cobertura
cob_share = defaultdict(float)
for m, s in zip(w_m, w_s):
    cob_share[m] += s
sem_peso = [i for i in validos if cob_share[i] < 0.5]
print(f"  pesos {len(w_h)}; municípios com <50% da área na grade: {len(sem_peso)}")
# normaliza a soma dos pesos de cada município para 1 (para totais baterem)
w_s = [s / cob_share[m] if cob_share[m] > 0 else s for m, s in zip(w_m, w_s)]
# municípios sem nenhum peso (sem geometria): põe tudo no hexágono da sede
for i in range(NM):
    if cob_share.get(i, 0) == 0:
        x, y = fwd.transform(mun.lon[i], mun.lat[i])
        from grade import axial
        k = hidx.get(axial(x, y))
        if k is not None:
            w_h.append(k); w_m.append(i); w_s.append(1.0)

hex_uf = np.array([uf_idx[mun.uf[m]] if m >= 0 else -1 for m in hex_mun])

# ---------------------------------------------------------------- terreno
print("terreno")
TERRENOS = [
    ("Floresta amazônica", "#2c6a3c"), ("Mata Atlântica", "#3f7d47"), ("Cerrado", "#a6a35b"), ("Caatinga", "#c4a46e"),
    ("Pampa", "#9cba6e"), ("Pantanal", "#6c9f86"), ("Pastagem", "#d6c784"), ("Lavoura", "#dba65e"),
    ("Silvicultura", "#56704f"), ("Cidade", "#a8968c"), ("Água", "#3f7fa6"),
]
BIOMA = {"Amazônia": 0, "Mata Atlântica": 1, "Cerrado": 2, "Caatinga": 3, "Pampa": 4, "Pantanal": 5}
bioma_mun = [BIOMA.get(b, 2) for b in mun.bioma.fillna("Cerrado")]
bio_poly = []
if (D / "brutos/ibge/biomas.geojson").exists():
    for f in json.load(open(D / "brutos/ibge/biomas.geojson"))["features"]:
        bio_poly.append((BIOMA[f["properties"]["bioma"]], shapely.prepared.prep(proj_geom(shape(f["geometry"]).buffer(0)))))


def bioma_hex(h, padrao):
    pt = Point(*centro(hq[h], hr[h]))
    for b, pg in bio_poly:
        if pg.contains(pt):
            return b
    return padrao
terreno = np.zeros(NH, dtype=int)
for h in range(NH):
    if not terra[h]:
        continue
    frs = hex_fr[h]
    if COB is None:
        terreno[h] = bioma_mun[hex_mun[h]]
        continue
    acc = defaultdict(float)
    bio = defaultdict(float)
    for i, f in frs:
        for k, v in COB.items():
            acc[k] += v[i] * f
        bio[bioma_mun[i]] += f
    tot = sum(acc.values()) or 1
    fr = {k: v / tot for k, v in acc.items()}
    b = bioma_hex(h, max(bio, key=bio.get))
    natural = fr["floresta"] + fr["savana_campo"]
    pasto = fr["pastagem"] + fr["mosaico"] * 0.5
    lav = fr["agricultura"] + fr["mosaico"] * 0.5
    if fr["agua"] > 0.5:
        terreno[h] = 10
    elif fr["urbano"] > 0.22:
        terreno[h] = 9
    elif natural >= max(pasto, lav, fr["silvicultura"]) or natural > 0.45:
        terreno[h] = b
    elif fr["silvicultura"] > max(pasto, lav):
        terreno[h] = 8
    elif lav > pasto:
        terreno[h] = 7
    else:
        terreno[h] = 6

E = np.array([elev.get((q, r), np.nan) for q, r in zip(hq, hr)], dtype=float)
relevo = np.zeros(NH, dtype=int)
for h in range(NH):
    if not terra[h] or E[h] != E[h]:
        continue
    viz = [E[hidx[(hq[h] + a, hr[h] + b)]] for a, b in VIZ if (hq[h] + a, hr[h] + b) in hidx]
    viz = [v for v in viz if v == v] + [E[h]]
    rel = max(viz) - min(viz)
    if rel > 520 or E[h] > 1700 or (rel > 330 and E[h] > 900):
        relevo[h] = 2
    elif rel > 210 or (rel > 120 and E[h] > 700):
        relevo[h] = 1

GLIFO = {0: {"forma": "copa", "n": 6, "r": 0.13, "cor": "rgba(16,58,30,.55)"},
         1: {"forma": "copa", "n": 4, "r": 0.13, "cor": "rgba(22,70,36,.5)"},
         2: {"forma": "tufo", "n": 3, "r": 0.16, "cor": "rgba(90,86,36,.5)"},
         3: {"forma": "ponto", "n": 5, "r": 0.08, "cor": "rgba(110,84,46,.55)"},
         4: {"forma": "risco", "n": 3, "r": 0.14, "cor": "rgba(70,110,50,.45)"},
         5: {"forma": "risco", "n": 4, "r": 0.15, "cor": "rgba(40,100,130,.55)"},
         7: {"forma": "risco", "n": 4, "r": 0.18, "cor": "rgba(150,100,40,.4)"},
         8: {"forma": "copa", "n": 5, "r": 0.09, "cor": "rgba(30,50,30,.5)"}}

# ---------------------------------------------------------------- rios e vizinhos
print("rios e vizinhos")
br_g = proj_geom(shape(json.load(open(D / "brutos/grade/brasil.geojson"))["features"][0]["geometry"]).buffer(0))
minx, miny, maxx, maxy = br_g.bounds
moldura = box(minx - 1400, miny - 900, maxx + 900, maxy + 900)
rios = []
for f in json.load(open(D / "brutos/grade/ne_rios.geojson"))["features"]:
    if not f["geometry"]:
        continue
    sr = f["properties"].get("scalerank") or 9
    if sr > 8:
        continue
    g0 = shape(f["geometry"])
    if not g0.intersects(box(-75, -35, -33, 7)):
        continue
    g = proj_geom(g0.intersection(box(-75, -35, -33, 7))).intersection(br_g.buffer(30))
    if g.is_empty:
        continue
    g = g.simplify(2.5)
    partes = getattr(g, "geoms", [g])
    for p in partes:
        if p.geom_type != "LineString" or p.length < 15:
            continue
        cs = np.round(np.asarray(p.coords), 1).ravel().tolist()
        w = 0 if sr <= 2 else 1 if sr <= 4 else 2 if sr <= 6 else 3
        rios.append({"n": f["properties"].get("name") or "", "w": w, "p": cs})
paises = []
for f in json.load(open(D / "brutos/grade/ne_paises.geojson"))["features"]:
    pr = f["properties"]
    if pr.get("CONTINENT") not in ("South America",) or pr.get("ADM0_A3") == "BRA":
        continue
    g = proj_geom(shape(f["geometry"]).buffer(0)).intersection(moldura).difference(br_g.buffer(8)).simplify(4)
    if g.is_empty:
        continue
    aneis = []
    for p in getattr(g, "geoms", [g]):
        if p.geom_type != "Polygon" or p.area < 200:
            continue
        aneis.append(np.round(np.asarray(p.exterior.coords), 1).ravel().tolist())
    if aneis:
        paises.append({"n": pr.get("NAME_PT") or pr.get("NAME"), "p": aneis})

# ---------------------------------------------------------------- pontos -> hexágono e município
from grade import axial  # noqa: E402
for p in pontos:
    k = hidx.get(axial(p["x"], p["y"]))
    p["h"] = int(k) if k is not None else -1
    m = mi.get(p.pop("cod")) if p.get("cod") is not None else None
    if m is None and k is not None and terra[k]:
        m = int(hex_mun[k])
    p["m"] = int(m) if m is not None else -1
    p.pop("lat"); p.pop("lon")
    if not p["regra"]:
        p.pop("regra")
    if not p["vt"]:
        p.pop("vt")

# ---------------------------------------------------------------- saída
print("gravando")
sede = [fwd.transform(lo, la) for lo, la in zip(mun.lon, mun.lat)]
COLUNAS = [
    ("pop", "População", "soma", "int", "Censo 2022"), ("area", "Área (km²)", "soma", "km2", "IBGE"),
    ("dens", "Densidade (hab/km²)", "media", "dens", "Censo 2022"),
    ("pib", "PIB", "soma", "brl", "IBGE, PIB dos Municípios"), ("pibpc", "PIB por habitante", "media", "brl0", "IBGE"),
    ("va_agro", "Agropecuária (valor adicionado)", "soma", "brl", "IBGE"), ("va_ind", "Indústria (valor adicionado)", "soma", "brl", "IBGE"),
    ("va_serv", "Serviços (valor adicionado)", "soma", "brl", "IBGE"), ("va_adm", "Administração pública (valor adicionado)", "soma", "brl", "IBGE"),
    ("renda", "Renda domiciliar por pessoa", "media", "brl0", "Censo 2022"), ("alfab", "Alfabetização 15+ (%)", "media", "pct", "Censo 2022"),
    ("superior", "Superior completo 25+ (%)", "media", "pct", "Censo 2022"), ("esgoto", "Esgoto adequado (%)", "media", "pct", "Censo 2022"),
    ("agua", "Água da rede geral (%)", "media", "pct", "Censo 2022"), ("idade", "Idade mediana", "media", "anos", "Censo 2022"),
    ("rel_cat", "Católicos (%)", "media", "pct", "Censo"), ("rel_evan", "Evangélicos (%)", "media", "pct", "Censo"),
    ("rel_sem", "Sem religião (%)", "media", "pct", "Censo"), ("rel_esp", "Espíritas (%)", "media", "pct", "Censo"),
    ("rel_afro", "Umbanda e candomblé (%)", "media", "pct", "Censo"),
    ("pct_indig", "Indígenas (%)", "media", "pct", "Censo 2022"), ("pct_quil", "Quilombolas (%)", "media", "pct", "Censo 2022"),
    ("idhm", "IDHM 2010", "media", "dec3", "Atlas Brasil"),
    ("flor_pct", "Floresta natural (%)", "media", "pct", "MapBiomas", "area"), ("sav_pct", "Cerrado e campos (%)", "media", "pct", "MapBiomas", "area"),
    ("past_pct", "Pastagem (%)", "media", "pct", "MapBiomas", "area"), ("agri_pct", "Agricultura (%)", "media", "pct", "MapBiomas", "area"),
    ("silv_pct", "Silvicultura (%)", "media", "pct", "MapBiomas", "area"), ("urb_pct", "Área urbana (%)", "media", "pct", "MapBiomas", "area"),
    ("agua_pct", "Água (%)", "media", "pct", "MapBiomas", "area"),
    ("perda_flor", "Floresta perdida desde 1985 (%)", "media", "pct", "MapBiomas", "area"),
    ("bovinos", "Rebanho bovino (cabeças)", "soma", "int", "IBGE PPM"),
    ("pib_va", "PIB do ano do valor adicionado", "soma", "brl", "IBGE"),
    ("energia_mw", "Potência das usinas (MW)", "soma", "mw", "ANEEL"), ("cfem", "Royalties da mineração (CFEM)", "soma", "brl", "ANM"),
    ("agro_valor", "Valor da produção agrícola", "soma", "brl", "IBGE PAM/PPM/PEVS"),
    ("empregos", "Empregos formais", "soma", "int", "IBGE CEMPRE"), ("cultura", "Empregos em cultura e esporte", "soma", "int", "IBGE CEMPRE"),
    ("ciencia", "Empregos em tecnologia e ciência", "soma", "int", "IBGE CEMPRE"),
    ("desastres", "Desastres reconhecidos", "media", "int", "MIDR/S2ID", "area"),
    ("des_chuva", "Inundações e enxurradas reconhecidas", "media", "int", "MIDR/S2ID", "area"), ("des_seca", "Secas reconhecidas", "media", "int", "MIDR/S2ID", "area"),
]
cols_meta = []
cols_out = {}
for c in COLUNAS:
    k = c[0]
    if k not in col:
        continue
    v = np.asarray(col[k], dtype=float)
    if not np.isfinite(v).any():
        continue
    nd = 0 if c[3] in ("int", "brl", "brl0", "km2") else 3 if c[3] == "dec3" else 2
    cols_out[k] = [None if not math.isfinite(x) else (round(x, nd) if nd else round(x)) for x in v]
    m = {"k": k, "nome": c[1], "tipo": c[2], "fmt": c[3], "fonte": c[4]}
    if len(c) > 5:
        m["peso"] = c[5]
    cols_meta.append(m)

municipios = {
    "cod": mun.cod.astype(int).tolist(), "nome": mun.nome.tolist(), "uf": [uf_idx[u] for u in mun.uf],
    "x": [round(s[0], 2) for s in sede], "y": [round(s[1], 2) for s in sede], "capital": mun.capital.astype(int).tolist(),
    "ufs": [{"sigla": u.sigla, "nome": u.nome, "regiao": u.regiao, "cod": int(u.cod)} for u in ufs.itertuples()],
    "col": cols_out, "colunas": cols_meta, "meta": meta,
}
if EMP:
    municipios["empregos"] = EMP
if AGRO:
    municipios["agro"] = AGRO
if SUBST:
    municipios["subst"] = SUBST
json.dump(municipios, open(OUT / "municipios.json", "w"), ensure_ascii=False, separators=(",", ":"))

usados = sorted(set(int(t) for t, tt in zip(terreno, terra) if tt))
mapa = {
    "R": round(R, 4), "q": hq.tolist(), "r": hr.tolist(),
    "terra": [int(round(min(1, max(0.35, f)) * 100)) if t else 0 for f, t in zip(gr.terra, terra)],
    "anel": gr.anel_mar.astype(int).tolist(),
    "elev": [None if not (t and e == e) else int(e) for e, t in zip(E, terra)],
    "terreno": terreno.tolist(), "relevo": relevo.tolist(), "uf": hex_uf.tolist(), "m": hex_mun.tolist(),
    "w_h": w_h, "w_m": w_m, "w_s": [round(s, 5) for s in w_s],
    "terrenos": [{"nome": n, "cor": c, "usado": i in usados} for i, (n, c) in enumerate(TERRENOS)],
    "glifo": {str(k): v for k, v in GLIFO.items()},
    "rios": rios, "paises": paises, "bbox": [round(v, 1) for v in br_g.bounds],
}
json.dump(mapa, open(OUT / "mapa.json", "w"), ensure_ascii=False, separators=(",", ":"))

# conselheiros e fontes são gerados em conselho.py (usa os JSON acima)
json.dump({"pontos": pontos, "regras": REGRAS}, open(D / "pontos_build.json", "w"), ensure_ascii=False, separators=(",", ":"))
for f in ["mapa.json", "municipios.json"]:
    print(f, round((OUT / f).stat().st_size / 1e6, 2), "MB")
print("pontos", len(pontos), "terrenos", {TERRENOS[k][0]: int((terreno[terra] == k).sum()) for k in usados},
      "relevo", np.bincount(relevo[terra]).tolist())
