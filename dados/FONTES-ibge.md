# Fontes — dados do IBGE (base municipal e agropecuária)

Coleta em 26/11/2026. Todos os dados são do Instituto Brasileiro de Geografia e Estatística (IBGE),
de livre uso com citação da fonte (política de dados abertos do IBGE; citar "Fonte: IBGE").
Scripts: `scripts/ibge_base.py`, `scripts/ibge_agro.py`, `scripts/ibge_biomas.py` (auxiliar `scripts/ibge_comum.py`).
Respostas brutas em `dados/brutos/ibge/`. Nenhum valor foi estimado ou interpolado; ausência = célula vazia.

## dados/municipios.csv (5.571 municípios)

| Coluna | Fonte |
|---|---|
| cod, nome, uf, regiao | API de Localidades v1 — https://servicodados.ibge.gov.br/api/v1/localidades/municipios (5.571, já inclui Boa Esperança do Norte/MT, 5101837, instalado em 2025) |
| capital | Base de Localidades do Brasil 2022 (categorias "Capital Estadual" e "Capital Federal") |
| lat, lon | **Sede municipal** da Base de Localidades do Brasil 2022 — https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/Localidades_do_Brasil/2022/Localidades_Brasil_shp.zip (SIRGAS 2000, graus decimais). Brasília: ponto "Capital Federal"; Fernando de Noronha: ponto do "Distrito Estadual". `coord_metodo` = "sede" nas 5.571 linhas (o recurso de ponto sobre o polígono não foi necessário). |
| area_km2 | Áreas territoriais 2025 — https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/areas_territoriais/2025/AR_BR_RG_UF_RGINT_RGI_MUN_2025.xls (aba AR_BR_MUN_2025) |
| pop2022 | Censo Demográfico 2022, SIDRA tabela 4714, variável 93 (população residente) — https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022 |
| pib, pib_ano | PIB dos Municípios, SIDRA tabela 5938 (Referência 2010), variável 37, último ano = **2023**, em R$ mil |
| va_agro, va_ind, va_serv, va_adm, impostos, pib_va, va_ano | Mesma tabela 5938, variáveis 513, 517, 6575, 525, 543 e 37, ano **2021**. Para 2022 e 2023 o IBGE divulgou apenas o PIB total (nota técnica 02/2024 do Sistema de Contas Nacionais; o SIDRA mostra "..." nesses anos). Por isso a decomposição é de 2021, e `pib_va` é o PIB de 2021, para calcular participações no mesmo ano (va_agro+va_ind+va_serv+va_adm+impostos = pib_va, ±2 por arredondamento). R$ mil, preços correntes. |
| bioma | Bioma predominante por município 2024 — https://geoftp.ibge.gov.br/informacoes_ambientais/estudos_ambientais/biomas/documentos/Bioma_Predominante_por_Municipio_2024.csv |

Boa Esperança do Norte (5101837) não tem pop2022, PIB nem bioma (não existia nas publicações usadas).

## dados/ufs.csv (27 UFs)
API de Localidades v1 (`/localidades/estados`) + capital da Base de Localidades 2022.

## Malhas (dados/brutos/ibge/)
- `municipios.geojson` — API de Malhas v3, qualidade **intermediária**, malha 2022:
  https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=municipio
  (o código vem em `properties.codarea` no bruto; no arquivo final as propriedades são `cod`, `nome`, `uf`, `fonte_geom`).
  A API traz 5.570 municípios (malha 2022). Boa Esperança do Norte e os municípios da malha 2022 que se sobrepõem a ele (Nova Ubiratã 5106240, Paranatinga 5106307, Sorriso 5107925, Vera 5108501) foram substituídos pela Malha Municipal 2025 do MT
  (https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/UFs/MT/MT_Municipios_2025.zip), simplificada (Douglas-Peucker) com densidade de vértices parecida (`fonte_geom = malha2025_MT`). Sobreposição residual com vizinhos < 0,3% da área.
  Escolhi a intermediária porque, na mínima, 77 sedes caem fora do próprio polígono (até ~6 km); na intermediária são 9, todas a menos de 0,5 km.
- `municipios_minima.geojson`, `ufs_minima.geojson` — mesma API, qualidade mínima (versões leves; mesma correção do MT).
- `ufs.geojson` — API de Malhas v3, qualidade intermediária, `intrarregiao=UF`.
- `biomas.geojson` — Biomas do Brasil 1:250.000 (IBGE, 2019) — https://geoftp.ibge.gov.br/informacoes_ambientais/estudos_ambientais/biomas/vetores/Biomas_250mil.zip — simplificado com tolerância 0,002° e coordenadas com 4 casas (1,7 MB). Propriedades `bioma`, `cod_bioma`.
Sistema de referência: SIRGAS 2000 em graus (praticamente igual a WGS84 para desenho).

## dados/agro.csv (formato longo, só linhas com valor > 0; rebanhos com cabeças > 0)
Todas do ano **2025** (último disponível no SIDRA em 26/11/2026), por município, consultadas por UF (`n6/in n3 XX`).

| fonte | Tabela SIDRA | Variáveis | Recorte |
|---|---|---|---|
| PAM — Produção Agrícola Municipal | 5457 | 214 quantidade, 215 valor | todos os produtos, exceto Total e as aberturas do café (fica "Café (em grão)" = total) |
| PPM — Pesquisa da Pecuária Municipal | 3939 | 105 efetivo (cabeças) | bovino, bubalino, equino, suíno-total, caprino, ovino, galináceos-total, codornas (sem os subtotais "matrizes de suínos" e "galinhas"); `valor_mil_reais` vazio |
| PPM | 74 | 106 quantidade, 215 valor | leite, ovos de galinha, ovos de codorna, mel, casulos, lã |
| PEVS — Produção da Extração Vegetal | 289 | 144 quantidade, 145 valor | só categorias-folha (sem Total e grupos). "Outros" recebe o grupo entre parênteses; fibras recebem "(fibra)" |
| PSILV — Silvicultura | 291 | 142 quantidade, 143 valor | carvão vegetal, lenha, madeira em tora para papel e celulose, madeira em tora para outras finalidades, casca de acácia-negra, folha de eucalipto, resina (sem abertura por espécie) |

API: `https://apisidra.ibge.gov.br/values/t/{tabela}/n6/in%20n3%20{UF}/v/{var}/p/2025/c{classificação}/{categorias}`.
`unidade` é a unidade de medida da quantidade conforme o SIDRA (Toneladas, Cabeças, Mil litros, Mil dúzias, Quilogramas, Metros cúbicos). Valores em R$ mil, preços correntes.
Conferência: soma municipal da soja (R$ 315.194.933 mil) e do rebanho bovino (234.251.041 cabeças) bate com o total Brasil da mesma tabela.
