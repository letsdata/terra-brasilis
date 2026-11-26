# Fonte: MapBiomas Brasil, cobertura e uso da terra por município

- **Arquivo gerado:** `dados/cobertura.csv` (script `scripts/mapbiomas_cobertura.py`)
- **Produto:** MapBiomas Brasil, Coleção 11 (versão 11, agosto de 2026), estatísticas de cobertura e uso da terra (30 m), recorte "Biomas, Estados e Municípios".
- **Página de origem:** https://brasil.mapbiomas.org/estatisticas/
- **Download (Google Drive, 75 MB):** https://drive.google.com/uc?id=1otOqymHuixvkRGVl65zTTNyfaHo46Gqk&export=download
  - arquivo: `MAPBIOMAS_BRAZIL-COL.11-BIOME_STATE_MUNICIPALITY.zip` -> `.xlsx`, aba `COVERAGE_11`
  - cópia em `dados/brutos/mapbiomas/`; baixado em 26/11/2026
- **Conteúdo:** área em hectares por bioma x município x classe, série anual 1985 a 2025. Usado: **2025** (último ano) e **1985** para `floresta_1985`. Municípios divididos entre biomas foram somados.
- **Licença:** o README do arquivo diz que os dados são "públicos e gratuitos mediante a simples referência da fonte". A página de termos de uso do MapBiomas Brasil indica Creative Commons **CC BY-SA**. Isso foi visto num resultado de busca, sem abrir a página. Citação pedida: "Projeto MapBiomas – Coleção 11 da Série Anual de Mapas de Cobertura e Uso da Terra do Brasil, acessado em 26/11/2026 através do link: https://brasil.mapbiomas.org/estatisticas/".

## Colunas

`cod` (IBGE, 7 dígitos), `ano` (2025), áreas em ha: `floresta`, `savana_campo`, `pastagem`, `agricultura`, `silvicultura`, `mosaico`, `urbano`, `mineracao`, `agua`, `outros`, e `floresta_1985`.

## Mapeamento de classes (código MapBiomas -> grupo)

| grupo | classes (ID) |
|---|---|
| floresta | Formação Florestal (3), Mangue (5), Floresta Alagável (6), Restinga Arbórea (49) |
| savana_campo | Formação Savânica (4), Savana Alagada (7), Campo Alagado e Área Pantanosa (11), Formação Campestre (12), Mosaico Herbáceo-Arbustivo (13), Apicum (32), Restinga Herbácea/Arbustiva (50), Marisma (84) |
| pastagem | Pastagem (15) |
| agricultura | Cana (20), Soja (39), Arroz (40), Outras Lavouras Temporárias (41), Algodão (62), Dendê (35), Café (46), Citrus (47), Outras Lavouras Perenes (48) |
| silvicultura | Silvicultura (9) |
| mosaico | Mosaico de Usos (21) |
| urbano | Área Urbanizada (24) |
| mineracao | Mineração (30) |
| agua | Rio, Lago e Oceano (33), Aquicultura (31) |
| outros | Praia, Duna e Areal (23), Afloramento Rochoso (29), Outras Áreas não Vegetadas (25), Usina Fotovoltaica (75), Parque Eólico (91), Não Observado (0) |

Observação: na Coleção 11, a Formação Savânica (4) fica no nível 1 "Floresta" da legenda. Aqui ela foi para `savana_campo`, como pedido. Na legenda, o Apicum (32) é vegetação herbácea, por isso ficou em `savana_campo`.

## Conferência de área

Comparamos a soma dos 10 grupos de 2025 com a área territorial do IBGE de 2025 (`dados/brutos/ibge/areas/AR_BR_RG_UF_RGINT_RGI_MUN_2025.xls`, km² x 100):

- mediana da razão: **1,0000**; 5% a 95%: 0,997 a 1,001; mínimo 0,65 e máximo 1,10
- 20 municípios fora de ±5%. São casos de limite costeiro ou insular, como Florianópolis (4205407), com razão 0,65.
- total do Brasil: 8.507.049 km² no MapBiomas contra 8.509.361 km² no IBGE

## Cobertura

5.572 linhas: 5.570 municípios, mais Lagoa dos Patos (4300002) e Lagoa Mirim (4300001), que o IBGE também codifica. Fernando de Noronha (2605459) não está no arquivo do MapBiomas.
