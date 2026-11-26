# Fontes: pontos (infraestrutura, natureza, patrimônio) e mineração

Baixado em 26/11/2026. Scripts em `scripts/pontos_*.py` (helpers em `scripts/pontos_comum.py`); brutos em `dados/brutos/pontos/`; saídas em `dados/pontos/`. Rodar com `.venv/bin/python -I scripts/pontos_<nome>.py`.

Regras comuns:
- `cod` é o código IBGE de 7 dígitos. Para casar nome + UF, a tabela vem da API de localidades do IBGE (https://servicodados.ibge.gov.br/api/v1/localidades/municipios). Para ponto no polígono, a malha municipal é `dados/brutos/ibge/api_malhas_BR_municipio_intermediaria.geojson`, baixada por `scripts/ibge_base.py`. A coluna `cod_metodo` diz qual dos dois foi usado.
- As coordenadas estão em WGS84/SIRGAS 2000, em graus decimais. Fora da caixa lat -34..6 / lon -74..-28 ficou só uma linha: a APA de Trindade e Martim Vaz, que é oceânica.

| Arquivo | Fonte (órgão, conjunto, URL) | Ano/versão | Licença |
|---|---|---|---|
| `usinas.csv` | ANEEL, SIGA (Sistema de Informações de Geração), `siga-empreendimentos-geracao.csv`. https://dadosabertos.aneel.gov.br/dataset/siga-sistema-de-informacoes-de-geracao-da-aneel | conjunto gerado em 01/11/2026 | ODbL |
| `patrimonio_unesco.csv` | Wikidata SPARQL (P1435 = Q9259, P17 = Q155, P757 ID UNESCO, P2614 critérios, P131/P1585 município). https://query.wikidata.org | consulta de 26/11/2026 | CC0 |
| `areas_protegidas.csv` | MMA, CNUC: atributos em `cnuc_2026_07.csv` e polígonos em `shp_cnuc_2025_08.zip`. https://dados.mma.gov.br/dataset/unidadesdeconservacao | CNUC jul/2026; polígonos ago/2025 | CC-BY |
| (visitação) | ICMBio, "Visitação em Unidades de Conservação Federais" (2000–2024), `visitacao_em_ucs_federais__2000___2024____atualizado30_10.xlsx`. https://www.gov.br/icmbio/pt-br/acesso-a-informacao/dados-abertos/arquivos/atualizacao-novembro-2025/visitacao-em-unidades/ (listado em dados.gov.br) | 2024, versão de out/2025 | ODbL |
| `aeroportos.csv` | ANAC, Lista de Aeródromos Públicos (`AerodromosPublicos.csv`). https://sistemas.anac.gov.br/dadosabertos/Aerodromos/ | atualizado em 15/11/2026 | CC-BY |
| (passageiros) | ANAC, Dados Estatísticos do Transporte Aéreo (`Dados_Estatisticos.csv`). https://sistemas.anac.gov.br/dadosabertos/Voos%20e%20opera%C3%A7%C3%B5es%20a%C3%A9reas/Dados%20Estat%C3%ADsticos%20do%20Transporte%20A%C3%A9reo/ | ano de 2025 | CC-BY |
| `mineracao_municipio.csv` | ANM, Arrecadação da CFEM (`CFEM_Arrecadacao_2022_2026.csv`). https://dadosabertos.anm.gov.br/CFEM/ | ano de 2025 | CC-BY |
| `petroleo.csv` | ANP, produção por poço em 2025: mar em `producao-mar-2025.csv`, terra em 4 arquivos trimestrais. https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/fase-de-desenvolvimento-e-producao. Polígonos dos campos: ANP, Dados Georreferenciados das Bacias Sedimentares, `campos-producao.zip` (CAMPOS_DE_PRODUCAO_08082023) | produção de 2025; polígonos de 08/08/2023 | CC-BY |
| `universidades.csv` | INEP, Microdados do Censo da Educação Superior 2024 (arquivos IES e cursos). https://download.inep.gov.br/microdados/microdados_censo_da_educacao_superior_2024.zip | 2024 | CC-BY |
| (programas nota 7) | CAPES, Programas da Pós-Graduação Stricto Sensu 2021–2024 (`br-capes-colsucup-prog-2024-2025-12-01.csv`). https://dadosabertos.capes.gov.br/dataset/2021-a-2024-programas-da-pos-graduacao-stricto-sensu-no-brasil | ano-base 2024, arquivo de 01/12/2025 | CC-BY |

## Notas por arquivo

**usinas.csv**
- Inclui só usinas com fase "Operação" e potência de pelo menos 1 MW. A potência é a fiscalizada; quando ela é 0, entra a outorgada.
- Foram descartadas 91 usinas com coordenada 0/0.
- `cod` é o município que contém o ponto da ANEEL. `cod_declarado` é o primeiro município listado pela ANEEL, casado pelo nome. Os dois diferem em 562 casos, sobretudo hidrelétricas na divisa e coordenadas imprecisas da própria ANEEL.

**patrimonio_unesco.csv**
- Os 26 sítios foram escolhidos à mão, um item do Wikidata por ID base da UNESCO. A lista bruta do Wikidata mistura sítios e componentes (ver `SITIOS` no script).
- O tipo vem dos critérios: (i)–(vi) é cultural, (vii)–(x) é natural, os dois juntos é misto.
- O site whc.unesco.org bloqueia acesso automatizado (Cloudflare), então não houve conferência com a lista oficial.
- "Teatros da Amazônia" (2026) aparece só com base no Wikidata.
- O Peruaçu (2025) usa o item da APA, que é o que carrega o ID 1747.
- Pantanal: o item do sítio não tem coordenada, então foi usada a do item Q157603.
- As Missões são um sítio transfronteiriço; foi usado o ponto de São Miguel das Missões (RS).

**areas_protegidas.csv**
- Inclui as 347 UCs federais do CNUC, sem as 826 RPPNs.
- Ficaram 4 sem polígono e foram descartadas: APA e Parque Nacional do Albardão, PN Povos Indígenas do Rio Tanaru e RDS Córregos dos Vales do Norte de Minas.
- `lat`/`lon` é um `representative_point` (sempre dentro do polígono); também há `lat_centroide`/`lon_centroide`.
- `area_km2` vem de "Área soma biomas" do CNUC (em ha, dividido por 100).
- `visitantes` é o último ano com valor maior que 0 na planilha do ICMBio; o ano está em `ano_visitacao`. 161 UCs têm dado de 2024 e 49 têm dados mais antigos.

**aeroportos.csv**
- Inclui os 496 aeródromos públicos cadastrados ou interditados.
- `passageiros` soma embarques e desembarques de 2025 (pagos e grátis, todas as naturezas e grupos de voo), sempre por etapa. Por isso também conta passageiro em trânsito que não desce, e o total de Guarulhos fica um pouco acima do número oficial do aeroporto.
- Os campos de passageiros só aparecem para os 150 aeródromos que tiveram voo regular em 2025.

**mineracao_municipio.csv**
- CFEM recolhida em 2025, por `CodigoMunicipio`. O total é de R$ 7,91 bilhões em 2.851 municípios.
- `substancia_principal` usa nomes harmonizados: "MINÉRIO DE X" vira X, "CARVÃO MINERAL" vira CARVÃO, "MINÉRIO DE ALUMÍNIO" vira BAUXITA, e as variantes de ÁGUA MINERAL viram uma só.
- O valor é o arrecadado (`ValorRecolhido`), não o valor da produção.

**petroleo.csv**
- Inclui 294 campos com produção em 2025. Óleo inclui condensado.
- Unidades: "Mm³" da ANP significa mil m³. A conversão usada é 1 m³ = 6,2898 bbl, e para `boe_dia`, 1 mil m³ de gás equivale a 1 m³ de óleo.
- As áreas "AnC_*" (áreas não contratadas, como AnC_MERO) foram somadas ao ponto do campo-mãe e aparecem como linhas próprias.
- 11 campos sem polígono no shapefile de 2023 ficaram de fora; juntos somam 0,01% do óleo.
- `uf` é o estado informado pela ANP (para campos no mar, é o estado confrontante). `cod` foi preenchido só para campos em terra.

**universidades.csv**
- **lat/lon é a sede do município da IES** (vem de `dados/municipios.csv`), não o campus.
- `matriculas` é a soma de QT_MAT dos cursos de graduação de 2024 (presencial e EaD). EaD entra no município-sede da IES.
- O arquivo de cursos (453 MB) foi agregado em `dados/brutos/pontos/inep/matriculas_por_ies_2024.csv` e apagado junto com o zip.
- `programas_nota7` conta programas CAPES em funcionamento com conceito 7, ligados por CD_ENTIDADE_EMEC = CO_IES. Ficaram 22 entidades CAPES sem correspondente no INEP, que são institutos de pesquisa e somam 7 programas nota 7.

## O que falhou ou ficou de fora

- **portos.csv: não produzido.** Os dados abertos da ANTAQ (web3.antaq.gov.br) não resolvem no DNS, nem em 8.8.8.8 nem em 1.1.1.1. O Estatístico Aquaviário (ea.antaq.gov.br) devolve um desafio Cloudflare.
- O Anuário ANTAQ 2025 (PDF) traz o ranking por instalação só como gráfico em imagem.
- O MPor/DNIT publica listas sem coordenadas, ou só de pequenas IP4 fluviais.
