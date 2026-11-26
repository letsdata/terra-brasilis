"""Usinas em operação (ANEEL SIGA) -> dados/pontos/usinas.csv

Fonte: ANEEL, Dados Abertos, conjunto "SIGA - Sistema de Informações de Geração da ANEEL",
recurso siga-empreendimentos-geracao.csv.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402

from pontos_comum import BRUTOS, CasadorMunicipio, baixar, dentro_do_brasil, num_br, salvar, cod_pelo_ponto  # noqa: E402

URL = ("https://dadosabertos.aneel.gov.br/dataset/6d90b77c-c5f5-4d81-bdec-7bc619494bb9/resource/"
       "11ec447d-698d-4ab8-977f-b424d5deee6a/download/siga-empreendimentos-geracao.csv")


def main():
    arq = baixar(URL, BRUTOS / "siga-empreendimentos-geracao.csv")
    d = pd.read_csv(arq, sep=";", dtype=str, encoding="utf-8")
    print("data do conjunto:", d.DatGeracaoConjuntoDados.unique())
    d = d[d.DscFaseUsina.str.strip() == "Operação"].copy()

    d["lat"] = num_br(d.NumCoordNEmpreendimento)
    d["lon"] = num_br(d.NumCoordEEmpreendimento)
    kw = num_br(d.MdaPotenciaFiscalizadaKw)
    kw = kw.where(kw > 0, num_br(d.MdaPotenciaOutorgadaKw))
    d["potencia_mw"] = (kw / 1000).round(3)
    d = d[d.potencia_mw >= 1]

    # municípios: "Bento Gonçalves - RS, Cotiporã - RS" -> primeiro é o principal
    cm = CasadorMunicipio()
    mun = d.DscMuninicpios.fillna("").str.split(",").str[0].str.strip()
    partes = mun.str.rsplit(" - ", n=1)
    d["municipio"] = partes.str[0].str.strip()
    d["uf_mun"] = partes.str[1].str.strip()
    d["cod"] = [cm.cod(m, u) for m, u in zip(d.municipio, d.uf_mun)]
    d["uf"] = d.uf_mun.where(d.uf_mun.str.len() == 2, d.SigUFPrincipal)
    d["municipios"] = d.DscMuninicpios.str.strip()

    ok = dentro_do_brasil(d.lat, d.lon)
    print("fora do Brasil/sem coordenada, descartadas:", (~ok).sum())
    print(d[~ok][["NomEmpreendimento", "SigTipoGeracao", "lat", "lon"]].head(20).to_string())
    d = d[ok]

    out = pd.DataFrame({
        "nome": d.NomEmpreendimento.str.strip(),
        "lat": d.lat.round(6),
        "lon": d.lon.round(6),
        "cod": d.cod,
        "uf": d.uf,
        "municipio": d.municipio,
        "tipo": d.SigTipoGeracao.str.strip(),
        "origem": d.DscOrigemCombustivel.str.strip(),
        "fonte": d.DscFonteCombustivel.str.strip(),
        "combustivel": d.NomFonteCombustivel.str.strip(),
        "potencia_mw": d.potencia_mw,
        "entrada_operacao": d.DatEntradaOperacao,
        "ceg": d.CodCEG.str.strip(),
        "municipios": d.municipios,
    }).sort_values("potencia_mw", ascending=False)
    out = out.drop_duplicates("ceg")
    print("sem cod:", (out.cod == "").sum(), "| exemplos:", list(cm.falhas)[:15])
    print(out.tipo.value_counts())
    print(out.groupby("tipo").potencia_mw.sum().round(0))
    out = cod_pelo_ponto(out, "nome_municipio")
    print("sem cod após ponto no polígono:", (out.cod == "").sum())
    salvar(out, "usinas.csv")


if __name__ == "__main__":
    main()
