# Fontes — indicadores sociais, emprego, desastres e IDHM

Chave em todos os arquivos: `cod` = código IBGE do município com 7 dígitos (inteiro).
Scripts: `scripts/social_sidra.py` (empregos + social), `scripts/social_desastres.py`, `scripts/social_idhm.py`.
Brutos: `dados/brutos/social/` (respostas JSON da API SIDRA `sidra_*.json`, metadados `meta_*.json`, CSV do Atlas de Desastres, JSON do Ipeadata).
Nenhum valor foi estimado ou interpolado. Coletado em 26/11/2026.

Licença: dados do IBGE são públicos e de livre reutilização com citação da fonte (Termos de uso do IBGE; Política de Dados Abertos do Executivo Federal, Decreto 8.777/2016). Atlas Digital de Desastres (MIDR) e Ipeadata/Atlas Brasil: dados públicos de órgãos federais/PNUD, livre uso com citação da fonte.

## dados/empregos.csv (formato longo)

- Fonte: IBGE, Cadastro Central de Empresas (CEMPRE), **SIDRA tabela 9528** — "Unidades locais, pessoal ocupado total e assalariado, salários e outras remunerações, por seção, divisão, grupo e classe da CNAE 2.0". Sucessora da tabela 6450 (série encerrada em 2021).
- Ano: **2024** (último publicado, liberado em 25/06/2026). Recorte por município da **unidade local** (onde as pessoas trabalham, não a sede da empresa).
- Variáveis: 707 Pessoal ocupado total → `pessoal_ocupado`; 708 Pessoal ocupado assalariado → `assalariados`. Classificação 12762 (CNAE 2.0), nível seção (A–U) + linha `secao = Total`.
- URL (por UF): `https://apisidra.ibge.gov.br/values/t/9528/n6/in n3 {UF}/v/707,708/p/2024/c12762/{categorias}`
- Colunas: cod, secao, descricao, pessoal_ocupado, assalariados, ano. 5.570 municípios × 22 linhas = 122.540 linhas.
- Valores vazios = "X" no SIDRA (dado omitido por sigilo estatístico, poucas empresas). "-" do SIDRA = 0.
- Atenção: por causa do sigilo, a soma das seções nem sempre bate com a linha Total (bate em 937 municípios); use a linha Total para o total do município. A seção T (serviços domésticos) é sempre 0 (o CEMPRE cobre só CNPJ). O CEMPRE não inclui trabalhadores informais nem agricultores sem CNPJ, então a seção A subestima a agropecuária.

## dados/social.csv (formato largo, Censo Demográfico 2022, `ano = 2022`)

| coluna | definição | tabela SIDRA |
|---|---|---|
| alfabetizacao_15mais | taxa de alfabetização das pessoas de 15 anos ou mais (%), publicada pelo IBGE | 9543, v2513 (totais de sexo, cor/raça, idade) |
| superior_25mais | % de pessoas de 25+ com superior completo = superior completo / total 25+ | 10141, v1643, c1568 (99713 / 120704) |
| renda_pc | rendimento nominal **médio** mensal domiciliar per capita (R$ de 2022), moradores em domicílios particulares permanentes ocupados | 10295, v13431 |
| renda_pc_mediana | idem, **mediano** (R$) | 10295, v13534 |
| religiao_catolica, religiao_evangelica, religiao_sem, religiao_espirita, religiao_afro | % das **pessoas de 10 anos ou mais** declaradas católicas apostólicas romanas, evangélicas, sem religião, espíritas, e de umbanda e candomblé (o Censo 2022 só investigou religião para 10+) | 9537, v140, c133 (95263, 95277, 2836, 2826, 2827 / total 95278) |
| esgoto_rede | % de moradores em domicílios particulares permanentes ocupados com esgotamento por rede geral, rede pluvial ou fossa ligada à rede | 7555, v382, c11558 (46290 / 46292) |
| agua_rede | % de moradores com ligação à rede geral de água usada como forma principal de abastecimento | 6894, v382, c1821 (72144 / 72129) |
| idade_mediana | idade mediana da população (anos) | 9515, v10613 |
| pct_indigena | % de pessoas indígenas (cor ou raça indígena + "se considera indígena") na população residente | 9718, v350 / v93 (c1714 = total, c2661 = total) |
| pct_quilombola | % de pessoas quilombolas na população residente | 9578, v4709 / v93 |

Cobertura: todas as colunas têm os 5.570 municípios. Percentuais calculados arredondados a 2 casas.
Exemplo de URL: `https://apisidra.ibge.gov.br/values/t/9543/n6/all/v/2513/p/2022/c2/6794/c86/95251/c287/100362`

## dados/desastres.csv

- Fonte: Ministério da Integração e do Desenvolvimento Regional (MIDR), Secretaria Nacional de Defesa Civil — **Atlas Digital de Desastres no Brasil**, base consolidada 1991–2025, versão 1.1 de 06/08/2026, registros oriundos do S2iD.
  Arquivo: https://atlasdigital.mdr.gov.br/arquivos/2026/BD_Atlas_1991_2025_v1.1_2026.08.06_Consolidado.csv (página de downloads: https://atlasdigital.mdr.gov.br/paginas/downloads.xhtml)
- Período: ano da data do evento entre **2016 e 2025** (`ano_inicio`, `ano_fim`).
- Contagem: número de registros (protocolos S2iD, um por município e evento) com `Status = Reconhecido` (reconhecimento federal de situação de emergência ou estado de calamidade pública).
- Grupos pela tipologia do Atlas (COBRADE): `seca_estiagem` = Estiagem e Seca; `inundacao_enxurrada_alagamento` = Inundações + Enxurradas + Alagamentos; `deslizamento` = Movimento de Massa (deslizamentos, quedas, corridas, subsidências); `chuvas_intensas` = Chuvas Intensas (COBRADE 13214, meteorológico, mantido separado por ser muito frequente); `outros` = demais (vendavais, granizo, incêndio florestal, erosão, ondas de frio/calor, doenças infecciosas, barragens etc.). `total` = soma dos cinco.
- `registros_todos` = todos os registros do município no período, reconhecidos ou não.
- Municípios sem nenhum registro aparecem com 0 (ausência de registro na base, não necessariamente ausência de evento).

## dados/idhm.csv

- Fonte: Atlas do Desenvolvimento Humano no Brasil (PNUD, Ipea, Fundação João Pinheiro), IDHM calculado com o **Censo 2010** (último IDHM municipal). Obtido pela redistribuição oficial no **Ipeadata** (Ipea), séries `ADH_IDHM`, `ADH_IDHM_R`, `ADH_IDHM_E`, `ADH_IDHM_L`, data 2010, nível Municípios.
  API: `http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='ADH_IDHM')`
- O download direto do Atlas Brasil (atlasbrasil.org.br) não está disponível como arquivo público estável (o link antigo `atlas2013_dadosbrutos_pt.xlsx` devolve 404).
- Cobertura: 5.564 municípios. Sem valor (6): 1504752 Mojuí dos Campos/PA, 2206720 Nazária/PI, 4212650 Pescaria Brava/SC, 4220000 Balneário Rincão/SC, 4314548 Pinto Bandeira/RS, 5006275 Paraíso das Águas/MS (instalados depois de 2010 ou ausentes da série do Ipeadata).
- Colunas: cod, idhm, idhm_renda, idhm_educacao, idhm_longevidade, ano (= 2010).
