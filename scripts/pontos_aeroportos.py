"""Aeródromos públicos (ANAC) + passageiros (ANAC, Dados Estatísticos do Transporte Aéreo)
-> dados/pontos/aeroportos.csv

passageiros = embarcados + desembarcados (pagos + grátis) no ano, somando todas as etapas
com origem ou destino no aeródromo (voos regulares e não regulares, domésticos e internacionais).
Como a base é por etapa, passageiros em trânsito que não descem do avião também entram.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402

from pontos_comum import BRUTOS, CasadorMunicipio, baixar, dentro_do_brasil, num_br, salvar  # noqa: E402

DIR = BRUTOS / "anac"
DIR.mkdir(exist_ok=True)
B = "https://sistemas.anac.gov.br/dadosabertos"
URL_AD = B + "/Aerodromos/Aer%C3%B3dromos%20P%C3%BAblicos/Lista%20de%20aer%C3%B3dromos%20p%C3%BAblicos/AerodromosPublicos.csv"
URL_EST = B + "/Voos%20e%20opera%C3%A7%C3%B5es%20a%C3%A9reas/Dados%20Estat%C3%ADsticos%20do%20Transporte%20A%C3%A9reo/Dados_Estatisticos.csv"
ANO = 2025

UFS = {"Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
       "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT",
       "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
       "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
       "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP",
       "Sergipe": "SE", "Tocantins": "TO"}


def passageiros(ano: int) -> pd.DataFrame:
    arq = baixar(URL_EST, DIR / "Dados_Estatisticos.csv", timeout=1800)
    cols = ["ANO", "GRUPO_DE_VOO", "NATUREZA", "AEROPORTO_DE_ORIGEM_SIGLA", "AEROPORTO_DE_DESTINO_SIGLA",
            "PASSAGEIROS_PAGOS", "PASSAGEIROS_GRATIS", "DECOLAGENS"]
    s = pd.read_csv(arq, sep=";", skiprows=1, usecols=cols, dtype=str)
    s = s[s.ANO == str(ano)].copy()
    s["pax"] = num_br(s.PASSAGEIROS_PAGOS).fillna(0) + num_br(s.PASSAGEIROS_GRATIS).fillna(0)
    s["dec"] = num_br(s.DECOLAGENS).fillna(0)
    s["reg"] = s.GRUPO_DE_VOO == "REGULAR"
    emb = s.groupby("AEROPORTO_DE_ORIGEM_SIGLA").agg(embarques=("pax", "sum"), decolagens=("dec", "sum"))
    des = s.groupby("AEROPORTO_DE_DESTINO_SIGLA").agg(desembarques=("pax", "sum"))
    reg_o = s[s.reg].groupby("AEROPORTO_DE_ORIGEM_SIGLA").pax.sum()
    reg_d = s[s.reg].groupby("AEROPORTO_DE_DESTINO_SIGLA").pax.sum()
    intl = s[s.NATUREZA == "INTERNACIONAL"]
    int_o = intl.groupby("AEROPORTO_DE_ORIGEM_SIGLA").pax.sum()
    int_d = intl.groupby("AEROPORTO_DE_DESTINO_SIGLA").pax.sum()
    t = emb.join(des, how="outer").fillna(0)
    t["passageiros"] = t.embarques + t.desembarques
    t["passageiros_regulares"] = reg_o.reindex(t.index).fillna(0) + reg_d.reindex(t.index).fillna(0)
    t["passageiros_internacionais"] = int_o.reindex(t.index).fillna(0) + int_d.reindex(t.index).fillna(0)
    t.index.name = "icao"
    return t.reset_index()


def main():
    arq = baixar(URL_AD, DIR / "AerodromosPublicos.csv")
    atualizado = open(arq, encoding="latin1").readline().strip()
    print(atualizado)
    d = pd.read_csv(arq, sep=";", encoding="latin1", skiprows=1, dtype=str)
    d["lat"] = pd.to_numeric(d.LATGEOPOINT, errors="coerce")
    d["lon"] = pd.to_numeric(d.LONGEOPOINT, errors="coerce")
    # alguns registros vêm sem município/UF do sítio: usa o município servido
    d["Município"] = d["Município"].fillna(d["Município Servido"])
    d["UF"] = d.UF.fillna(d["UF Servido"])
    d["uf"] = d.UF.str.strip().map(UFS)
    print("UF sem sigla:", d[d.uf.isna()].UF.unique())
    cm = CasadorMunicipio()
    d["cod"] = [cm.cod(m, u) for m, u in zip(d["Município"], d.uf)]
    ok = dentro_do_brasil(d.lat, d.lon)
    print("descartados sem coordenada válida:", (~ok).sum())
    d = d[ok]

    p = passageiros(ANO)
    d["icao"] = d["Código OACI"].str.strip()
    d = d.merge(p, on="icao", how="left")
    out = pd.DataFrame({
        "nome": d.Nome.str.strip(),
        "lat": d.lat.round(6), "lon": d.lon.round(6),
        "cod": d.cod, "uf": d.uf,
        "municipio": d["Município"].str.strip().str.title().str.replace(r" (De|Da|Do|Dos|Das|E) ", lambda m: " " + m.group(1).lower() + " ", regex=True),
        "icao": d.icao,
        "ciad": d.CIAD,
        "situacao": d["Situação"],
        "altitude_m": num_br(d.Altitude),
        "operacao_noturna": d["Operação Noturna"],
        "passageiros": d.passageiros.round().astype("Int64"),
        "passageiros_regulares": d.passageiros_regulares.round().astype("Int64"),
        "passageiros_internacionais": d.passageiros_internacionais.round().astype("Int64"),
        "decolagens": d.decolagens.round().astype("Int64"),
        "ano_passageiros": ANO,
    })
    out["voos_regulares"] = out.passageiros_regulares.fillna(0) > 0
    # passageiros só para quem teve voo regular no ano (pedido); demais ficam vazios
    for c in ["passageiros", "passageiros_regulares", "passageiros_internacionais", "decolagens"]:
        out.loc[~out.voos_regulares, c] = pd.NA
    out = out.sort_values("passageiros", ascending=False, na_position="last")
    print(out[out.cod == ""][["nome", "municipio", "uf"]])
    print("com voos regulares:", out.voos_regulares.sum(), "| sem cod:", (out.cod == "").sum(), list(cm.falhas)[:10])
    print(out.head(12)[["icao", "nome", "municipio", "passageiros"]].to_string())
    tot = p.passageiros.sum()
    print(f"total passageiros (todas siglas, inclui exterior) {tot:,.0f}; somados nos aeródromos públicos BR {out.passageiros.sum():,.0f}")
    salvar(out, "aeroportos.csv")


if __name__ == "__main__":
    main()
