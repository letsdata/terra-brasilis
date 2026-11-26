"""MapBiomas Brasil Coleção 11: cobertura e uso da terra por município -> dados/cobertura.csv

Entrada: dados/brutos/mapbiomas/MAPBIOMAS_BRAZIL-COL.11-BIOME_STATE_MUNICIPALITY.xlsx
  (zip baixado de https://drive.google.com/uc?id=1otOqymHuixvkRGVl65zTTNyfaHo46Gqk&export=download,
   link da página https://brasil.mapbiomas.org/estatisticas/)
Aba COVERAGE_11: uma linha por bioma x município x classe, colunas y1985..y2025 em hectares.
Municípios que cruzam dois biomas aparecem em mais de uma linha; aqui somamos.

Uso: .venv/bin/python -I scripts/mapbiomas_cobertura.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
XLSX = RAIZ / "dados/brutos/mapbiomas/MAPBIOMAS_BRAZIL-COL.11-BIOME_STATE_MUNICIPALITY.xlsx"
AREAS_IBGE = RAIZ / "dados/brutos/ibge/areas/AR_BR_RG_UF_RGINT_RGI_MUN_2025.xls"  # só para conferência
SAIDA = RAIZ / "dados/cobertura.csv"

# Código de classe MapBiomas (Coleção 11) -> grupo do mapa. Toda classe presente no arquivo
# precisa estar aqui; o script falha se aparecer uma classe não mapeada.
MAPA = {
    # floresta: formações florestais naturais
    3: "floresta",   # Formação Florestal
    5: "floresta",   # Mangue
    6: "floresta",   # Floresta Alagável
    49: "floresta",  # Restinga Arbórea
    # savana_campo: savana, campo e demais formações naturais não florestais, áreas úmidas
    4: "savana_campo",   # Formação Savânica
    7: "savana_campo",   # Savana Alagada
    11: "savana_campo",  # Campo Alagado e Área Pantanosa
    12: "savana_campo",  # Formação Campestre
    13: "savana_campo",  # Outras formações não florestais / Mosaico Herbáceo-Arbustivo
    32: "savana_campo",  # Apicum
    50: "savana_campo",  # Restinga Herbácea/Arbustiva
    77: "savana_campo",  # Formação Herbáceo Arbustiva (não aparece no arquivo; legenda)
    84: "savana_campo",  # Marisma
    # pastagem
    15: "pastagem",
    # agricultura: lavouras temporárias e perenes
    19: "agricultura",  # Lavoura Temporária (agregado; não aparece no arquivo)
    20: "agricultura",  # Cana
    39: "agricultura",  # Soja
    40: "agricultura",  # Arroz
    41: "agricultura",  # Outras Lavouras Temporárias
    62: "agricultura",  # Algodão
    36: "agricultura",  # Lavoura Perene (agregado; não aparece no arquivo)
    35: "agricultura",  # Dendê
    46: "agricultura",  # Café
    47: "agricultura",  # Citrus
    48: "agricultura",  # Outras Lavouras Perenes
    # silvicultura
    9: "silvicultura",
    # mosaico de usos
    21: "mosaico",
    # urbano
    24: "urbano",
    # mineração
    30: "mineracao",
    # água
    33: "agua",  # Rio, Lago e Oceano
    31: "agua",  # Aquicultura
    # outros
    23: "outros",  # Praia, Duna e Areal
    29: "outros",  # Afloramento Rochoso
    25: "outros",  # Outras Áreas não Vegetadas
    75: "outros",  # Usina Fotovoltaica
    91: "outros",  # Parque Eólico
    0: "outros",   # Não observado
}
GRUPOS = ["floresta", "savana_campo", "pastagem", "agricultura", "silvicultura",
          "mosaico", "urbano", "mineracao", "agua", "outros"]


def main():
    df = pd.read_excel(XLSX, sheet_name="COVERAGE_11")
    anos = sorted(int(c[1:]) for c in df.columns if c.startswith("y") and c[1:].isdigit())
    ano, ano0 = anos[-1], anos[0]
    faltando = set(df["class"].unique()) - set(MAPA)
    if faltando:
        raise SystemExit(f"classes sem mapeamento: {sorted(faltando)}")
    df["grupo"] = df["class"].map(MAPA)
    df["cod"] = df["geocode"].astype(int)

    largo = (df.pivot_table(index="cod", columns="grupo", values=f"y{ano}",
                            aggfunc="sum", fill_value=0.0)
             .reindex(columns=GRUPOS, fill_value=0.0))
    f85 = df[df.grupo == "floresta"].groupby("cod")[f"y{ano0}"].sum()
    largo[f"floresta_{ano0}"] = f85.reindex(largo.index).fillna(0.0)
    largo = largo.round(2).reset_index()
    largo.insert(1, "ano", ano)
    largo.to_csv(SAIDA, index=False)
    print(f"{SAIDA}: {len(largo)} linhas, ano {ano}, floresta_{ano0}")

    # Conferência: soma das classes x área territorial IBGE 2025 (km² -> ha)
    if AREAS_IBGE.exists():
        ib = pd.read_excel(AREAS_IBGE, sheet_name="AR_BR_MUN_2025").dropna(subset=["CD_MUN"])
        ib = ib.assign(cod=ib.CD_MUN.astype(int), area_ha=ib.AR_MUN_2025.astype(float) * 100)
        m = largo.merge(ib[["cod", "area_ha"]], on="cod", how="left")
        m["razao"] = m[GRUPOS].sum(axis=1) / m["area_ha"]
        print("sem área IBGE:", m.loc[m.area_ha.isna(), "cod"].tolist())
        print("IBGE sem MapBiomas:", sorted(set(ib.cod) - set(largo.cod)))
        print(m["razao"].describe(percentiles=[.01, .05, .5, .95, .99]).round(4).to_string())
        print("fora de [0,95; 1,05]:", int(((m.razao < .95) | (m.razao > 1.05)).sum()))
        print(m.sort_values("razao").iloc[[0, 1, 2, -3, -2, -1]][["cod", "area_ha", "razao"]].to_string())
        tot = largo[GRUPOS].sum().sum()
        print(f"Brasil: soma {tot/100:.0f} km² vs IBGE {ib.area_ha.sum()/100:.0f} km²")
        print((largo[GRUPOS].sum() / tot * 100).round(2).to_string())


if __name__ == "__main__":
    main()
