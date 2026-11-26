"""Gera web/dados/extras.json: pontos, regras das maravilhas, fontes e os conselheiros
(frases calculadas a partir dos dados). Rodar depois de build.py.

Uso: .venv/bin/python scripts/conselho.py
"""
import json, math
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
D = RAIZ / "dados"
OUT = RAIZ / "web/dados"
MU = json.load(open(OUT / "municipios.json"))
PB = json.load(open(D / "pontos_build.json"))
col = {k: np.array([np.nan if v is None else v for v in vs], dtype=float) for k, vs in MU["col"].items()}
nome, ufi = MU["nome"], MU["uf"]
ufs = MU["ufs"]
NM = len(nome)
pop = col["pop"]


def br(v, casas=1):
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def inteiro(v):
    return br(round(v), 0)


def reais(v):
    a = abs(v)
    for lim, sg, pl in [(1e12, "trilhão", "trilhões"), (1e9, "bilhão", "bilhões"), (1e6, "milhão", "milhões")]:
        if a >= lim:
            return f"R$ {br(v / lim)} {sg if a / lim < 2 else pl}"
    return f"R$ {inteiro(v)}"


def pct(v, casas=1):
    return br(v, casas) + "%"


def lugar(i):
    return f"{nome[i]} ({ufs[ufi[i]]['sigla']})"


def top(k, n=1, filtro=None, menor=False):
    v = col[k].copy()
    ok = np.isfinite(v)
    if filtro is not None:
        ok &= filtro
    ids = np.where(ok)[0]
    ids = ids[np.argsort(v[ids])]
    if not menor:
        ids = ids[::-1]
    return [int(i) for i in ids[:n]]


def uf_soma(k):
    s = np.zeros(len(ufs))
    for i in range(NM):
        if np.isfinite(col[k][i]):
            s[ufi[i]] += col[k][i]
    return s


grandes = pop >= 50000
medios = pop >= 20000
cons = []

# --- Tesoureiro
it = []
pib = col["pib"]; tot = np.nansum(pib)
ano = MU["meta"].get("ano_pib", "")
s_uf = uf_soma("pib"); u_top = int(np.argmax(s_uf))
it.append({"t": f"O PIB somado dos municípios foi de {reais(tot)} em {ano}. Só o estado de {ufs[u_top]['nome']} produziu {pct(s_uf[u_top] / tot * 100)} disso.", "uf": u_top, "lente": "ouro"})
i = top("pib")[0]
ordem = np.sort(s_uf)
n_est = int(np.searchsorted(np.cumsum(ordem), pib[i]))
it.append({"t": f"A cidade com maior PIB é {lugar(i)}: {reais(pib[i])}, {pct(pib[i] / tot * 100)} do país. É mais do que a soma dos {n_est} estados de menor PIB.", "m": i})
a = top("pibpc", 1, medios)[0]; b = top("pibpc", 1, medios, menor=True)[0]
it.append({"t": f"Entre as cidades com mais de 20 mil habitantes, o maior PIB por habitante é o de {lugar(a)} ({reais(col['pibpc'][a])}); o menor, o de {lugar(b)} ({reais(col['pibpc'][b])}). Uma diferença de {inteiro(col['pibpc'][a] / col['pibpc'][b])} vezes.", "m": a, "lente": "pibpc"})
if "va_adm" in col and "pib_va" in col:
    g = col["va_adm"] / col["pib_va"]
    n = int(np.nansum(g > 0.4))
    it.append({"t": "Cidades em frente aos campos de petróleo do mar, como Maricá e Saquarema, sobem ao topo: o IBGE conta a produção do pré-sal na economia do município de frente para o campo.", "lente": "pibpc"})
    it.append({"t": f"Em {inteiro(n)} municípios, a administração pública (prefeitura, escolas e postos de saúde públicos) responde por mais de 40% da economia, em dados de {MU['meta'].get('ano_va', '')}.", "lente": "governo"})
cons.append({"id": "tesouro", "nome": "Tesouro", "ic": "💰", "titulo": "Conselheira do Tesouro", "papel": "Ouro é o PIB, o valor de tudo o que se produz num ano.", "itens": it})

# --- Campo
agro = pd.read_csv(D / "agro.csv") if (D / "agro.csv").exists() else None
if agro is not None:
    it = []
    mi = {c: i for i, c in enumerate(MU["cod"])}
    ag = agro[agro.valor_mil_reais.fillna(0) > 0].copy(); ag["valor"] = ag.valor_mil_reais * 1000
    ano_ag = int(ag.ano.max())
    totp = ag.groupby("produto").valor.sum().sort_values(ascending=False)
    p1, p2, p3 = [x.split(" (")[0] for x in totp.index[:3]]
    it.append({"t": f"Os produtos do campo que mais renderam em {ano_ag}: {p1} ({reais(totp.iloc[0])}), {p2} ({reais(totp.iloc[1])}) e {p3} ({reais(totp.iloc[2])}).", "lente": "comida"})
    for prod, frase in [("Soja (em grão)", "soja"), ("Café (em grão)", "café"), ("Cana-de-açúcar", "cana"), ("Açaí (fruto)", "açaí")]:
        g = ag[ag.produto == prod]
        if g.empty:
            g = ag[ag.produto.str.startswith(prod.split(" ")[0])]
        if g.empty:
            continue
        r = g.sort_values("valor", ascending=False).iloc[0]
        if r.cod in mi:
            it.append({"t": f"O maior produtor de {frase} é {lugar(mi[r.cod])}: {reais(r.valor)}, {pct(r.valor / g.valor.sum() * 100)} do valor nacional.", "m": mi[r.cod]})
    bov = agro[agro.produto == "Bovino"]
    if not bov.empty:
        r = bov.sort_values("quantidade", ascending=False).iloc[0]
        tb = bov.quantidade.sum()
        it.append({"t": f"O Brasil tem {br(tb / 1e6)} milhões de bois e vacas, mais do que gente ({br(np.nansum(pop) / 1e6)} milhões). O maior rebanho é o de {lugar(mi[r.cod])}, com {inteiro(r.quantidade)} cabeças.", "m": mi[r.cod], "lente": "pasto"})
    cons.append({"id": "campo", "nome": "Campo", "ic": "🌾", "titulo": "Conselheiro do Campo", "papel": "Comida é o valor adicionado da agropecuária; a colheita vem das pesquisas agrícolas do IBGE.", "itens": it})

# --- Indústria
it = []
ids = top("va_ind", 5)
it.append({"t": "As cinco cidades com mais produção industrial: " + ", ".join(lugar(i) for i in ids) + ".", "m": ids[0], "lente": "producao"})
sh = col["va_ind"] / col["pib_va"]
i = top("va_ind", 1, grandes & (sh > 0))[0]
j = [k for k in np.argsort(-np.nan_to_num(sh)) if grandes[k]][0]
it.append({"t": f"Entre as cidades com mais de 50 mil habitantes, a mais dependente da indústria é {lugar(int(j))}: {pct(sh[j] * 100, 0)} da economia vem de fábricas, minas ou usinas.", "m": int(j)})
if "cfem" in col:
    i = top("cfem")[0]
    it.append({"t": f"{lugar(i)} recolhe mais royalties de mineração do que qualquer outra cidade: {reais(col['cfem'][i])} no ano.", "m": i, "lente": "mineracao"})
cons.append({"id": "industria", "nome": "Indústria", "ic": "⚙", "titulo": "Conselheiro da Indústria", "papel": "Produção é o valor adicionado da indústria: transformação, extração, construção e energia.", "itens": it})

# --- Energia
us = pd.read_csv(D / "pontos/usinas.csv") if (D / "pontos/usinas.csv").exists() else None
if us is not None:
    it = []
    tot = us.potencia_mw.sum()
    por = us.groupby("tipo").potencia_mw.sum()
    hid = por.reindex(["UHE", "PCH", "CGH"]).sum()
    it.append({"t": f"As {inteiro(len(us))} usinas em operação com 1 MW ou mais somam {br(tot / 1000)} GW. A água ainda é a maior fonte: {pct(hid / tot * 100, 0)} da potência.", "lente": "energia"})
    for tipo, nomef in [("EOL", "vento"), ("UFV", "sol")]:
        g = us[us.tipo == tipo]
        if g.empty:
            continue
        u = g.groupby("uf").potencia_mw.sum().sort_values(ascending=False)
        ui = next(k for k, x in enumerate(ufs) if x["sigla"] == u.index[0])
        it.append({"t": f"Energia do {nomef}: {br(g.potencia_mw.sum() / 1000)} GW, {pct(g.potencia_mw.sum() / tot * 100, 0)} do total. {ufs[ui]['nome']} lidera, com {br(u.iloc[0] / 1000)} GW.", "uf": ui})
    b = us.sort_values("potencia_mw", ascending=False).iloc[0]
    mi = {c: i for i, c in enumerate(MU["cod"])}
    it.append({"t": f"A maior usina inteiramente brasileira é {b.nome}, no rio Xingu, com {inteiro(b.potencia_mw)} MW. Itaipu é maior, mas metade dela é do Paraguai." if b.nome == "Belo Monte" else f"A maior usina é {b.nome}, com {inteiro(b.potencia_mw)} MW.", "m": mi.get(int(b.cod))})
    cons.append({"id": "energia", "nome": "Energia", "ic": "⚡", "titulo": "Conselheira de Energia", "papel": "Potência instalada das usinas em operação, pelo cadastro da ANEEL.", "itens": it})

# --- Educação
it = []
if "superior" in col:
    i = top("superior", 1, grandes)[0]
    it.append({"t": f"Entre as cidades com mais de 50 mil habitantes, {lugar(i)} tem a maior parte de adultos com diploma: {pct(col['superior'][i])} das pessoas de 25 anos ou mais.", "m": i, "lente": "diplomas"})
    caps = [k for k in range(NM) if MU["capital"][k]]
    c = sorted(caps, key=lambda k: col["superior"][k])
    it.append({"t": f"Entre as capitais, vai de {pct(col['superior'][c[0]])} em {lugar(c[0])} a {pct(col['superior'][c[-1]])} em {lugar(c[-1])}.", "m": c[-1]})
if "alfab" in col:
    i = top("alfab", 1, None, menor=True)[0]
    n = int(np.nansum(col["alfab"] < 80))
    it.append({"t": f"Em {inteiro(n)} municípios, mais de 1 em cada 5 pessoas de 15 anos ou mais não sabe ler e escrever. A taxa mais baixa é a de {lugar(i)}: {pct(col['alfab'][i])}.", "m": i, "lente": "alfab"})
if it:
    cons.append({"id": "educacao", "nome": "Educação", "ic": "🎓", "titulo": "Conselheira de Educação", "papel": "Ciência é a gente com curso superior; dados do Censo 2022.", "itens": it})

# --- Fé
it = []
for k, nomef, lente in [("rel_evan", "evangélicos", "fe"), ("rel_cat", "católicos", "catolica"), ("rel_sem", "pessoas sem religião", "semrel"), ("rel_afro", "seguidores de umbanda e candomblé", "afro")]:
    if k not in col:
        continue
    tb = np.nansum(col[k] * pop) / np.nansum(pop[np.isfinite(col[k])])
    i = top(k, 1, medios)[0]
    it.append({"t": f"No Brasil, {pct(tb)} são {nomef}. Entre as cidades com mais de 20 mil habitantes, a maior proporção é a de {lugar(i)}: {pct(col[k][i])}.", "m": i, "lente": lente})
if "rel_evan" in col and "rel_cat" in col:
    n = int(np.nansum(col["rel_evan"] > col["rel_cat"]))
    it.append({"t": f"Em {inteiro(n)} municípios já há mais evangélicos do que católicos.", "lente": "fe"})
if it:
    cons.append({"id": "fe", "nome": "Fé", "ic": "✝", "titulo": "Conselheiro da Fé", "papel": f"Religião declarada no {MU['meta'].get('ano_religiao', 'Censo')}.", "itens": it})

# --- Natureza
cob = pd.read_csv(D / "cobertura.csv") if (D / "cobertura.csv").exists() else None
if cob is not None:
    it = []
    mi = {c: i for i, c in enumerate(MU["cod"])}
    cob = cob[cob.cod.isin(mi)]
    tot = cob[["floresta", "savana_campo", "pastagem", "agricultura", "silvicultura", "mosaico", "urbano", "mineracao", "agua", "outros"]].sum().sum()
    fl, fl85 = cob.floresta.sum(), cob.floresta_1985.sum()
    ano_c = int(cob.ano.iloc[0])
    it.append({"t": f"Floresta natural cobre {pct(fl / tot * 100, 0)} do território em {ano_c}. Em 1985 eram {pct(fl85 / tot * 100, 0)}: sumiram {inteiro((fl85 - fl) / 100)} km², uma área do tamanho de {br((fl85 - fl) / 100 / 586522, 1)} Minas Gerais.", "lente": "perda"})
    cob["perda"] = cob.floresta_1985 - cob.floresta
    r = cob.sort_values("perda", ascending=False).head(3)
    nomes = [lugar(mi[c]) for c in r.cod]
    it.append({"t": f"Os municípios que mais perderam floresta desde 1985: {nomes[0]} ({inteiro(r.perda.iloc[0] / 100)} km²), {nomes[1]} e {nomes[2]}.", "m": mi[int(r.cod.iloc[0])], "lente": "perda"})
    it.append({"t": f"Pasto ocupa {pct(cob.pastagem.sum() / tot * 100, 0)} do país; lavouras, {pct(cob.agricultura.sum() / tot * 100, 0)}; cidades, {pct(cob.urbano.sum() / tot * 100, 1)}.", "lente": "pasto"})
    cons.append({"id": "natureza", "nome": "Natureza", "ic": "🌳", "titulo": "Conselheira da Natureza", "papel": "Cobertura do solo medida por satélite pelo MapBiomas.", "itens": it})

# --- Geógrafo
it = []
i = top("area")[0]; j = top("area", 1, None, menor=True)[0]
it.append({"t": f"O maior município é {lugar(i)}, com {inteiro(col['area'][i])} km², maior que {sum(1 for u in range(len(ufs)) if uf_soma('area')[u] < col['area'][i])} estados. O menor é {lugar(j)}, com {br(col['area'][j])} km².", "m": i})
i = top("dens", 1)[0]
it.append({"t": f"A cidade mais apertada é {lugar(i)}: {inteiro(col['dens'][i])} habitantes por km².", "m": i, "lente": "populacao"})
mapa = json.load(open(OUT / "mapa.json"))
el = [e if e is not None else -1 for e in mapa["elev"]]
h = int(np.argmax(el))
if el[h] > 0:
    m = mapa["m"][h]
    it.append({"t": f"O hexágono mais alto fica em {lugar(m)}, com o centro a {inteiro(el[h])} m. Cada hexágono mostra a altitude do seu centro, não o pico.", "m": m, "lente": "altitude"})
if "idade" in col:
    a = top("idade", 1, medios)[0]; b = top("idade", 1, medios, menor=True)[0]
    it.append({"t": f"A cidade de mais de 20 mil habitantes com população mais velha é {lugar(a)} (idade mediana {inteiro(col['idade'][a])} anos); a mais jovem, {lugar(b)} ({inteiro(col['idade'][b])} anos).", "m": b, "lente": "idade"})
cons.append({"id": "geografo", "nome": "Território", "ic": "🧭", "titulo": "Geógrafo-mor", "papel": "Tamanho, gente e relevo.", "itens": it})

# --- Povos
it = []
if "pct_indig" in col:
    i = top("pct_indig")[0]
    tb = np.nansum(col["pct_indig"] * pop) / 100
    it.append({"t": f"O Censo 2022 contou cerca de {br(tb / 1e6, 2)} milhão de indígenas. Em {lugar(i)}, são {pct(col['pct_indig'][i])} da população.", "m": i, "lente": "indigena"})
if "pct_quil" in col:
    i = top("pct_quil")[0]
    tb = np.nansum(col["pct_quil"] * pop) / 100
    it.append({"t": f"Foi o primeiro censo a contar quilombolas: cerca de {br(tb / 1e6, 1)} milhão de pessoas. Em {lugar(i)}, são {pct(col['pct_quil'][i])} da população.", "m": i, "lente": "quilombola"})
if it:
    cons.append({"id": "povos", "nome": "Povos", "ic": "🪶", "titulo": "Conselheiro dos Povos", "papel": "Povos indígenas e quilombolas no Censo 2022.", "itens": it})

des = pd.read_csv(D / "desastres.csv") if (D / "desastres.csv").exists() else None
if des is not None:
    it = []
    mi = {c: i for i, c in enumerate(MU["cod"])}
    a0, a1 = int(des.ano_inicio.iloc[0]), int(des.ano_fim.iloc[0])
    t = des.total.sum()
    it.append({"t": f"De {a0} a {a1}, o governo federal reconheceu {inteiro(t)} desastres nos municípios. {pct(des.seca_estiagem.sum() / t * 100, 0)} foram secas e estiagens.", "lente": "seca"})
    r = des.sort_values("total", ascending=False).iloc[0]
    it.append({"t": f"O município com mais desastres reconhecidos no período é {lugar(mi[r.cod])}: {inteiro(r.total)}.", "m": mi[int(r.cod)], "lente": "desastres"})
    n0 = int((des.total == 0).sum())
    it.append({"t": f"{inteiro(n0)} municípios não têm nenhum reconhecimento no período. Isso não quer dizer que nada aconteceu: o reconhecimento depende de pedido da prefeitura.", "lente": "desastres"})
    cons.append({"id": "defesa", "nome": "Defesa Civil", "ic": "🌪", "titulo": "Conselheira da Defesa Civil", "papel": f"Desastres com reconhecimento federal, {a0}–{a1} (Atlas Digital de Desastres).", "itens": it})

for c in cons:
    for x in c["itens"]:
        for k in ("m", "uf"):
            if k in x and (x[k] is None or (isinstance(x[k], float) and math.isnan(x[k]))):
                x.pop(k)

# --- fontes
F = [
    ("Censo Demográfico 2022", "IBGE", "2022", "População, alfabetização, curso superior, renda, religião, saneamento, idade, povos indígenas e quilombolas", "https://sidra.ibge.gov.br/pesquisa/censo-demografico/demografico-2022/inicial", "social.csv"),
    ("PIB dos Municípios", "IBGE", f"PIB {MU['meta'].get('ano_pib','')}; setores {MU['meta'].get('ano_va','')}", "Ouro, Comida (agropecuária), Produção (indústria), serviços e administração pública", "https://sidra.ibge.gov.br/tabela/5938", None),
    ("Pesquisas agropecuárias (PAM, PPM, PEVS, PSILV)", "IBGE", MU["meta"].get("ano_agro", ""), "Colheita de cada município, rebanhos e recursos do campo", "https://sidra.ibge.gov.br/tabela/5457", "agro.csv"),
    ("Cadastro Central de Empresas (CEMPRE)", "IBGE", MU.get("empregos", {}).get("ano", ""), "Cidadãos e distritos: pessoal ocupado por seção da CNAE", "https://sidra.ibge.gov.br/pesquisa/cempre/tabelas", "empregos.csv"),
    ("Malhas territoriais, áreas e Base de Localidades", "IBGE", "2022–2025", "Fronteiras, áreas e sedes dos municípios", "https://servicodados.ibge.gov.br/api/docs/malhas?versao=3", None),
    ("Biomas do Brasil 1:250.000", "IBGE", "2019", "Bioma de cada hexágono", "https://www.ibge.gov.br/geociencias/informacoes-ambientais/estudos-ambientais/15842-biomas.html", None),
    ("MapBiomas Coleção 11", "Projeto MapBiomas", MU["meta"].get("ano_cobertura", ""), "Cobertura do solo: floresta, pasto, lavoura, cidade; floresta perdida desde 1985", "https://brasil.mapbiomas.org/estatisticas/", "cobertura.csv"),
    ("SIGA: empreendimentos de geração", "ANEEL", "2026", "Usinas em operação e potência instalada", "https://dadosabertos.aneel.gov.br/dataset/siga-sistema-de-informacoes-de-geracao-da-aneel", "pontos/usinas.csv"),
    ("Lista do Patrimônio Mundial", "Unesco / Wikidata", "2026", "Maravilhas: sítios do Patrimônio Mundial", "https://whc.unesco.org/en/statesparties/br", "pontos/patrimonio_unesco.csv"),
    ("Cadastro Nacional de Unidades de Conservação e visitação", "MMA / ICMBio", "", "Parques e áreas protegidas", "https://www.gov.br/icmbio/pt-br", "pontos/areas_protegidas.csv"),
    ("Aeródromos e movimentação", "ANAC", "", "Aeroportos e passageiros", "https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas", "pontos/aeroportos.csv"),
    ("Estatístico Aquaviário", "ANTAQ", "", "Portos e carga movimentada", "https://web3.antaq.gov.br/ea/", "pontos/portos.csv"),
    ("Arrecadação da CFEM", "ANM", MU["meta"].get("ano_cfem", ""), "Royalties da mineração por município", "https://dados.gov.br/dados/conjuntos-dados/sistema-arrecadacao", "pontos/mineracao_municipio.csv"),
    ("Produção de petróleo e gás por campo", "ANP", "", "Campos de petróleo e gás", "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos", "pontos/petroleo.csv"),
    ("Censo da Educação Superior e Avaliação da Pós-Graduação", "INEP / CAPES", "", "Universidades", "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior", "pontos/universidades.csv"),
    ("Atlas Digital de Desastres no Brasil", "MIDR", MU["meta"].get("anos_desastres", ""), "Desastres reconhecidos", "https://atlasdigital.mdr.gov.br/", "desastres.csv"),
    ("Atlas do Desenvolvimento Humano", "PNUD / Ipea / FJP", "2010", "IDHM", "http://www.atlasbrasil.org.br/", "idhm.csv"),
    ("Copernicus DEM GLO-90 via Open-Meteo", "ESA / Open-Meteo", "", "Altitude do centro de cada hexágono", "https://open-meteo.com/en/docs/elevation-api", "elevacao.csv"),
    ("Natural Earth", "Natural Earth (domínio público)", "", "Rios e países vizinhos", "https://www.naturalearthdata.com/", None),
]
fontes = [{"nome": n, "org": o, "ano": a, "uso": u, "url": url} for n, o, a, u, url, arq in F if arq is None or (D / arq).exists()]
pontos = PB["pontos"]
extras = {"pontos": pontos, "regras": PB["regras"], "fontes": fontes, "conselheiros": cons}
json.dump(extras, open(OUT / "extras.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("extras.json", round((OUT / "extras.json").stat().st_size / 1e6, 2), "MB;", len(cons), "conselheiros;", sum(len(c["itens"]) for c in cons), "frases")
for c in cons:
    print("\n##", c["titulo"])
    for x in c["itens"]:
        print("-", x["t"])
