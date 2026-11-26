'use strict';
/* Terra Brasilis: o Brasil como tabuleiro de estratégia, com dados públicos.
   Dados em dados/mapa.json (grade), dados/municipios.json (colunas por município)
   e dados/extras.json (pontos, fontes, conselheiros, resumo). */

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const NF = new Intl.NumberFormat('pt-BR');
const NF1 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
const NF2 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ok = v => v !== null && v !== undefined && Number.isFinite(v);
const sem = s => String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

function compacto(v) {
  if (!ok(v)) return '–';
  const a = Math.abs(v);
  if (a >= 1e12) return NF1.format(v / 1e12) + ' tri';
  if (a >= 1e9) return NF1.format(v / 1e9) + ' bi';
  if (a >= 1e6) return NF1.format(v / 1e6) + ' mi';
  if (a >= 1e4) return NF1.format(v / 1e3) + ' mil';
  if (a >= 100) return NF.format(Math.round(v));
  return NF1.format(v);
}
function fmt(v, f) {
  if (!ok(v)) return '–';
  switch (f) {
    case 'int': return NF.format(Math.round(v));
    case 'pct': return NF1.format(v) + '%';
    case 'brl': return 'R$ ' + compacto(v);
    case 'brl0': return 'R$ ' + NF.format(Math.round(v));
    case 'mw': return v >= 1000 ? NF1.format(v / 1000) + ' GW' : NF.format(Math.round(v)) + ' MW';
    case 'km2': return NF.format(Math.round(v)) + ' km²';
    case 'dens': return NF1.format(v) + '/km²';
    case 'dec3': return v.toFixed(3).replace('.', ',');
    case 'anos': return NF1.format(v) + ' anos';
    case 'ha': return compacto(v) + ' ha';
    case 'c': return compacto(v);
    default: return compacto(v);
  }
}

/* ---------- paletas ---------- */
const PAL = {
  verde: ['#f3ecc2', '#cfe08a', '#8cc461', '#3f9a4f', '#1d6b48', '#0c4337'],
  ouro: ['#2b2116', '#5b3f17', '#9a6a1c', '#d4a845', '#f0d48a', '#fff6d8'],
  azul: ['#eef5f2', '#bcdbe0', '#79b4cf', '#4f86c6', '#2f58a0', '#1d2f6b'],
  rosa: ['#f6eee8', '#eac7c4', '#d99aa8', '#b8698f', '#874482', '#4d2b66'],
  fogo: ['#fff1c9', '#fdc777', '#f58f4c', '#d9533b', '#a3283a', '#5c1534'],
  terra: ['#f1e6cf', '#dcc08f', '#bf9259', '#93683a', '#64472a', '#3a2b1d'],
  teal: ['#e9f3ea', '#b5ddd1', '#73bfb4', '#3a9a98', '#1f6f7c', '#14475a'],
  violeta: ['#f1ecf7', '#d3c7ea', '#a99bd6', '#8170bd', '#5b4c9c', '#38306b'],
};
function hex2rgb(h) { const n = parseInt(h.slice(1), 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; }
const PAL_RGB = Object.fromEntries(Object.entries(PAL).map(([k, v]) => [k, v.map(hex2rgb)]));
function rampa(nome, t) {
  const p = PAL_RGB[nome] || PAL_RGB.verde;
  t = Math.max(0, Math.min(1, t)) * (p.length - 1);
  const i = Math.min(p.length - 2, Math.floor(t)), f = t - i;
  const a = p[i], b = p[i + 1];
  return `rgb(${Math.round(a[0] + (b[0] - a[0]) * f)},${Math.round(a[1] + (b[1] - a[1]) * f)},${Math.round(a[2] + (b[2] - a[2]) * f)})`;
}

/* ---------- lentes ---------- */
const LENTES = [
  { id: 'terreno', nome: 'Terreno', ic: '🗺', grupo: 'Terra', modo: 'terreno', sub: 'Cobertura do solo (MapBiomas) sobre o bioma, com relevo' },
  { id: 'altitude', nome: 'Altitude', ic: '⛰', grupo: 'Terra', modo: 'altitude', paleta: 'terra', escala: 'lin', fmt: 'int', un: 'm', sub: 'Altitude do centro do hexágono, em metros' },
  { id: 'populacao', nome: 'População', ic: '👥', grupo: 'Gente', modo: 'densidade', num: 'pop', paleta: 'violeta', escala: 'log', fmt: 'dens', sub: 'Habitantes por km² (Censo 2022)' },
  { id: 'renda', nome: 'Renda', ic: '💵', grupo: 'Economia', modo: 'media', col: 'renda', paleta: 'verde', escala: 'quantil', fmt: 'brl0', sub: 'Rendimento domiciliar por pessoa (Censo 2022)' },
  { id: 'pibpc', nome: 'Ouro por habitante', ic: '🪙', grupo: 'Economia', modo: 'razao', num: 'pib', den: 'pop', paleta: 'ouro', escala: 'log', fmt: 'brl', sub: 'PIB municipal dividido pela população' },
  { id: 'ouro', nome: 'Ouro (PIB)', ic: '💰', grupo: 'Economia', modo: 'densidade', num: 'pib', paleta: 'ouro', escala: 'log', fmt: 'brl', sub: 'PIB por km²' },
  { id: 'comida', nome: 'Comida', ic: '🌾', grupo: 'Economia', modo: 'densidade', num: 'va_agro', paleta: 'verde', escala: 'log', fmt: 'brl', sub: 'Valor adicionado da agropecuária por km²' },
  { id: 'producao', nome: 'Produção', ic: '⚙', grupo: 'Economia', modo: 'densidade', num: 'va_ind', paleta: 'fogo', escala: 'log', fmt: 'brl', sub: 'Valor adicionado da indústria por km²' },
  { id: 'governo', nome: 'Peso do governo', ic: '🏛', grupo: 'Economia', modo: 'razao', num: 'va_adm', den: 'pib_va', mult: 100, paleta: 'azul', escala: 'lin', fmt: 'pct', sub: 'Administração pública no PIB do município' },
  { id: 'energia', nome: 'Energia', ic: '⚡', grupo: 'Recursos', modo: 'pontos', tipos: ['usina'], paleta: 'fogo', escala: 'log', fmt: 'mw', sub: 'Potência das usinas em operação no hexágono (ANEEL)' },
  { id: 'mineracao', nome: 'Mineração', ic: '⛏', grupo: 'Recursos', modo: 'densidade', num: 'cfem', paleta: 'terra', escala: 'log', fmt: 'brl', sub: 'Royalties da mineração (CFEM) por km²' },
  { id: 'floresta', nome: 'Floresta', ic: '🌳', grupo: 'Terra', modo: 'media', col: 'flor_pct', peso: 'area', paleta: 'verde', escala: 'lin', fmt: 'pct', sub: 'Parte do município coberta por floresta natural (MapBiomas)' },
  { id: 'perda', nome: 'Floresta perdida', ic: '🪓', grupo: 'Terra', modo: 'media', col: 'perda_flor', peso: 'area', paleta: 'fogo', escala: 'lin', fmt: 'pct', sub: 'Floresta natural de 1985 que não existe mais (MapBiomas)' },
  { id: 'pasto', nome: 'Pasto', ic: '🐄', grupo: 'Terra', modo: 'media', col: 'past_pct', peso: 'area', paleta: 'terra', escala: 'lin', fmt: 'pct', sub: 'Parte do município ocupada por pastagem (MapBiomas)' },
  { id: 'lavoura', nome: 'Lavoura', ic: '🌱', grupo: 'Terra', modo: 'media', col: 'agri_pct', peso: 'area', paleta: 'verde', escala: 'lin', fmt: 'pct', sub: 'Parte do município com agricultura (MapBiomas)' },
  { id: 'ciencia', nome: 'Ciência', ic: '🔬', grupo: 'Economia', modo: 'densidade', num: 'ciencia', paleta: 'azul', escala: 'log', fmt: 'c', sub: 'Empregos em tecnologia, comunicação e ciência por km² (CEMPRE)' },
  { id: 'cultura', nome: 'Cultura', ic: '🎭', grupo: 'Economia', modo: 'densidade', num: 'cultura', paleta: 'rosa', escala: 'log', fmt: 'c', sub: 'Empregos em artes, cultura, esporte e recreação por km² (CEMPRE)' },
  { id: 'diplomas', nome: 'Diplomas', ic: '🎓', grupo: 'Gente', modo: 'media', col: 'superior', paleta: 'azul', escala: 'lin', fmt: 'pct', sub: 'Pessoas de 25 anos ou mais com curso superior (Censo 2022)' },
  { id: 'alfab', nome: 'Alfabetização', ic: '✍', grupo: 'Gente', modo: 'media', col: 'alfab', paleta: 'azul', escala: 'quantil', fmt: 'pct', sub: 'Pessoas de 15 anos ou mais que sabem ler e escrever (Censo 2022)' },
  { id: 'fe', nome: 'Fé evangélica', ic: '✝', grupo: 'Fé', modo: 'media', col: 'rel_evan', paleta: 'rosa', escala: 'lin', fmt: 'pct', sub: 'Evangélicos na população' },
  { id: 'catolica', nome: 'Fé católica', ic: '⛪', grupo: 'Fé', modo: 'media', col: 'rel_cat', paleta: 'violeta', escala: 'lin', fmt: 'pct', sub: 'Católicos na população' },
  { id: 'semrel', nome: 'Sem religião', ic: '○', grupo: 'Fé', modo: 'media', col: 'rel_sem', paleta: 'teal', escala: 'lin', fmt: 'pct', sub: 'Pessoas sem religião' },
  { id: 'afro', nome: 'Umbanda e candomblé', ic: '🌊', grupo: 'Fé', modo: 'media', col: 'rel_afro', paleta: 'azul', escala: 'quantil', fmt: 'pct', sub: 'Religiões de matriz africana' },
  { id: 'esgoto', nome: 'Esgoto', ic: '🚰', grupo: 'Gente', modo: 'media', col: 'esgoto', paleta: 'teal', escala: 'lin', fmt: 'pct', sub: 'Moradores com esgoto em rede ou fossa ligada à rede (Censo 2022)' },
  { id: 'idade', nome: 'Idade', ic: '⌛', grupo: 'Gente', modo: 'media', col: 'idade', paleta: 'violeta', escala: 'lin', fmt: 'anos', sub: 'Idade mediana (Censo 2022)' },
  { id: 'indigena', nome: 'Povos indígenas', ic: '🪶', grupo: 'Gente', modo: 'media', col: 'pct_indig', paleta: 'terra', escala: 'log', fmt: 'pct', sub: 'Pessoas indígenas na população (Censo 2022)' },
  { id: 'quilombola', nome: 'Quilombolas', ic: '✊', grupo: 'Gente', modo: 'media', col: 'pct_quil', paleta: 'ouro', escala: 'log', fmt: 'pct', sub: 'Pessoas quilombolas na população (Censo 2022)' },
  { id: 'idh', nome: 'IDH', ic: '⭐', grupo: 'Gente', modo: 'media', col: 'idhm', paleta: 'verde', escala: 'lin', fmt: 'dec3', sub: 'Índice de Desenvolvimento Humano Municipal (2010)' },
  { id: 'desastres', nome: 'Desastres', ic: '🌪', grupo: 'Terra', modo: 'media', col: 'desastres', peso: 'area', paleta: 'fogo', escala: 'log', fmt: 'int', sub: 'Desastres reconhecidos pelo governo federal no município' },
  { id: 'inundacao', nome: 'Inundações', ic: '🌧', grupo: 'Terra', modo: 'media', col: 'des_chuva', peso: 'area', paleta: 'azul', escala: 'lin', fmt: 'int', sub: 'Inundações, enxurradas e alagamentos reconhecidos no município' },
  { id: 'seca', nome: 'Secas', ic: '☀', grupo: 'Terra', modo: 'media', col: 'des_seca', peso: 'area', paleta: 'fogo', escala: 'lin', fmt: 'int', sub: 'Secas e estiagens reconhecidas no município' },
];
const RAPIDAS = ['terreno', 'populacao', 'renda', 'comida', 'floresta', 'diplomas', 'fe'];

/* ---------- distritos (seções da CNAE) ---------- */
const DISTRITO = {
  A: ['Fazendas', '🚜'], B: ['Mina', '⛏'], C: ['Polo Industrial', '🏭'], D: ['Usina', '⚡'], E: ['Águas e Resíduos', '💧'],
  F: ['Canteiro de Obras', '🏗'], G: ['Mercado', '🛒'], H: ['Entreposto', '🚚'], I: ['Bairro Turístico', '🏨'], J: ['Tecnopolo', '💻'],
  K: ['Centro Financeiro', '🏦'], L: ['Imobiliário', '🏢'], M: ['Escritórios Técnicos', '📐'], N: ['Serviços de Apoio', '🧾'],
  O: ['Sede do Governo', '🏛'], P: ['Campus', '🎓'], Q: ['Polo de Saúde', '🏥'], R: ['Arena Cultural', '🎭'], S: ['Associações', '🤝'],
  T: ['Serviço Doméstico', '🏠'], U: ['Organismos Internacionais', '🌐'],
};
const COR_REGIAO = { 'Norte': '#3f9a4f', 'Nordeste': '#d9813b', 'Sudeste': '#4f86c6', 'Sul': '#8170bd', 'Centro-Oeste': '#c9a23a' };

/* ---------- estado ---------- */
const E = { W: 0, H: 0, dpr: 1, cx: 0, cy: 0, s: 0.2, sFit: 0, lente: 'terreno', recursos: true, sel: null, faixa: null, hover: -1, hoverPt: null, sujo: true, anim: null };
let M, MU, X;           // dados
let N = 0, HX, HY, IDX, NB, TERRA, UFH, MH, AREA_H;
let corTerreno = [], valHex = null, tHex = null, infoLente = null;
let banners = [], pontosVis = [];
const DIRS = [[1, 0], [0, 1], [-1, 1], [-1, 0], [0, -1], [1, -1]];
const SQ3 = Math.sqrt(3);
const cv = $('#mapa'), ctx = cv.getContext('2d');
const mini = $('#mini'), mctx = mini.getContext('2d');
let miniBase = null;

const chave = (q, r) => (q + 2000) * 8192 + (r + 2000);

/* ---------- carga ---------- */
async function carregar() {
  const [a, b, c] = await Promise.all(['dados/mapa.json', 'dados/municipios.json', 'dados/extras.json'].map(u => fetch(u).then(r => { if (!r.ok) throw new Error(u); return r.json(); })));
  M = a; MU = b; X = c;
  X.pontos.sort((p, q) => (q.mar - p.mar) || ((p.z ?? 3) - (q.z ?? 3)) || ((q.v || 0) - (p.v || 0)));
  preparar();
  montarUI();
  redimensionar();
  enquadrarBrasil(false);
  const h = location.hash.slice(1);
  usarLente(LENTES.some(l => l.id === h && lenteDisponivel(l)) ? h : 'terreno');
  $('#carregando').hidden = true;
}

function preparar() {
  N = M.q.length;
  HX = new Float32Array(N); HY = new Float32Array(N);
  IDX = new Map();
  const R = M.R;
  for (let i = 0; i < N; i++) {
    HX[i] = R * SQ3 * (M.q[i] + M.r[i] / 2);
    HY[i] = R * 1.5 * M.r[i];
    IDX.set(chave(M.q[i], M.r[i]), i);
  }
  NB = new Int32Array(N * 6).fill(-1);
  for (let i = 0; i < N; i++) for (let k = 0; k < 6; k++) {
    const j = IDX.get(chave(M.q[i] + DIRS[k][0], M.r[i] + DIRS[k][1]));
    if (j !== undefined) NB[i * 6 + k] = j;
  }
  TERRA = M.terra; UFH = M.uf; MH = M.m;
  const areaHex = 1.5 * SQ3 * R * R;
  AREA_H = new Float32Array(N);
  for (let i = 0; i < N; i++) AREA_H[i] = areaHex * Math.max(0.2, TERRA[i] / 100);
  // índice reverso hexágono -> pesos
  MU.n = MU.cod.length;
  MU.idx = new Map(MU.cod.map((c, i) => [c, i]));
  // agregados por UF
  calcularUFs();
  // cores do terreno com relevo sombreado
  calcularTerreno();
  // bannner candidatos
  const ord = [...Array(MU.n).keys()].filter(i => ok(MU.col.pop[i])).sort((a, b) => MU.col.pop[b] - MU.col.pop[a]);
  E.cidades = ord.slice(0, 900);
}

function calcularUFs() {
  const nu = MU.ufs.length;
  const cols = MU.colunas;
  MU.ufAgg = MU.ufs.map(() => ({}));
  for (const c of cols) {
    const v = MU.col[c.k]; if (!v) continue;
    const s = new Float64Array(nu), w = new Float64Array(nu), cnt = new Int32Array(nu);
    for (let i = 0; i < MU.n; i++) {
      const x = v[i]; if (!ok(x)) continue;
      const u = MU.uf[i];
      if (c.tipo === 'soma') { s[u] += x; cnt[u]++; }
      else { const p = c.peso === 'area' ? (MU.col.area[i] || 0) : (MU.col.pop[i] || 0); s[u] += x * p; w[u] += p; cnt[u]++; }
    }
    for (let u = 0; u < nu; u++) MU.ufAgg[u][c.k] = cnt[u] ? (c.tipo === 'soma' ? s[u] : (w[u] ? s[u] / w[u] : NaN)) : NaN;
  }
  // Brasil
  MU.br = {};
  for (const c of cols) {
    const v = MU.col[c.k]; if (!v) continue;
    let s = 0, w = 0, cnt = 0;
    for (let i = 0; i < MU.n; i++) {
      const x = v[i]; if (!ok(x)) continue; cnt++;
      if (c.tipo === 'soma') s += x; else { const p = c.peso === 'area' ? (MU.col.area[i] || 0) : (MU.col.pop[i] || 0); s += x * p; w += p; }
    }
    MU.br[c.k] = cnt ? (c.tipo === 'soma' ? s : s / w) : NaN;
  }
}

function hash01(i, k = 0) { let h = (i * 374761393 + k * 668265263) | 0; h = (h ^ (h >>> 13)) * 1274126177 | 0; return ((h ^ (h >>> 16)) >>> 0) / 4294967296; }

function calcularTerreno() {
  const R = M.R, el = M.elev;
  const cores = M.terrenos.map(t => hex2rgb(t.cor));
  corTerreno = new Array(N);
  E.sombra = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    if (!M.terra[i]) { corTerreno[i] = null; continue; }
    const e0 = el[i] ?? 0;
    const g = k => { const j = NB[i * 6 + k]; return j >= 0 && M.terra[j] && el[j] != null ? el[j] : e0; };
    const gx = (g(0) - g(3)) / (2 * R * SQ3);
    const gy = ((g(1) + g(2)) / 2 - (g(4) + g(5)) / 2) / (3 * R);
    let b = 1 + Math.max(-0.32, Math.min(0.32, (gx - gy) / SQ3 * 0.012));
    b *= 1 + Math.min(0.12, e0 / 12000);
    b *= 0.97 + hash01(i) * 0.06;
    b = Math.round(b * 24) / 24;
    E.sombra[i] = b;
    const c = cores[M.terreno[i]] || [128, 128, 128];
    corTerreno[i] = `rgb(${Math.min(255, Math.round(c[0] * b))},${Math.min(255, Math.round(c[1] * b))},${Math.min(255, Math.round(c[2] * b))})`;
  }
}

/* ---------- valores das lentes ---------- */
function lenteDisponivel(L) {
  if (L.modo === 'terreno' || L.modo === 'altitude') return true;
  if (L.modo === 'pontos') return X.pontos.some(p => L.tipos.includes(p.t));
  const k = L.col || L.num;
  const v = MU.col[k]; if (!v) return false;
  if (L.den && !MU.col[L.den]) return false;
  return v.some(ok);
}

function valoresLente(L) {
  const v = new Float64Array(N).fill(NaN);
  const { w_h: wh, w_m: wm, w_s: ws } = M;
  if (L.modo === 'altitude') { for (let i = 0; i < N; i++) if (M.terra[i] && M.elev[i] != null) v[i] = M.elev[i]; return v; }
  if (L.modo === 'pontos') {
    for (let i = 0; i < N; i++) if (M.terra[i]) v[i] = 0;
    for (const p of X.pontos) if (L.tipos.includes(p.t) && p.h >= 0 && ok(p.v)) v[p.h] = (v[p.h] || 0) + p.v;
    return v;
  }
  const a = new Float64Array(N), b = new Float64Array(N);
  if (L.modo === 'densidade') {
    const col = MU.col[L.num];
    for (let k = 0; k < wh.length; k++) { const x = col[wm[k]]; if (ok(x)) { a[wh[k]] += x * ws[k]; b[wh[k]] = 1; } }
    for (let i = 0; i < N; i++) if (M.terra[i] && b[i]) v[i] = a[i] / AREA_H[i];
  } else if (L.modo === 'razao') {
    const n = MU.col[L.num], d = MU.col[L.den];
    for (let k = 0; k < wh.length; k++) { const x = n[wm[k]], y = d[wm[k]]; if (ok(x) && ok(y)) { a[wh[k]] += x * ws[k]; b[wh[k]] += y * ws[k]; } }
    for (let i = 0; i < N; i++) if (M.terra[i] && b[i] > 0) v[i] = a[i] / b[i] * (L.mult || 1);
  } else if (L.modo === 'media') {
    const col = MU.col[L.col], pe = L.peso === 'area' ? MU.col.area : MU.col.pop;
    for (let k = 0; k < wh.length; k++) { const x = col[wm[k]]; if (!ok(x)) continue; const p = (pe[wm[k]] || 0) * ws[k] + 1e-9; a[wh[k]] += x * p; b[wh[k]] += p; }
    for (let i = 0; i < N; i++) if (M.terra[i] && b[i] > 0) v[i] = a[i] / b[i];
  }
  return v;
}

function prepararEscala(L, v) {
  const xs = [];
  for (let i = 0; i < N; i++) if (M.terra[i] && ok(v[i])) xs.push(v[i]);
  const info = { L, escala: L.escala };
  const t = new Float32Array(N).fill(NaN);
  if (!xs.length) { infoLente = info; return t; }
  if (L.escala === 'quantil') {
    const s = xs.slice().sort((a, b) => a - b);
    info.qs = s;
    const rank = x => { let lo = 0, hi = s.length; while (lo < hi) { const m = (lo + hi) >> 1; if (s[m] < x) lo = m + 1; else hi = m; } return lo / (s.length - 1 || 1); };
    for (let i = 0; i < N; i++) if (ok(v[i])) t[i] = rank(v[i]);
    info.inv = q => s[Math.round(Math.max(0, Math.min(1, q)) * (s.length - 1))];
  } else {
    const log = L.escala === 'log';
    const tr = x => log ? Math.log10(Math.max(x, 1e-9)) : x;
    const pos = log ? xs.filter(x => x > 0) : xs;
    const s = pos.map(tr).sort((a, b) => a - b);
    const lo = s[Math.floor(s.length * 0.02)] ?? 0, hi = s[Math.floor(s.length * 0.985)] ?? 1;
    const den = hi - lo || 1;
    for (let i = 0; i < N; i++) if (ok(v[i])) t[i] = log && v[i] <= 0 ? -1 : Math.max(0, Math.min(1, (tr(v[i]) - lo) / den));
    info.inv = q => { const x = lo + q * den; return log ? Math.pow(10, x) : x; };
  }
  infoLente = info;
  return t;
}

function usarLente(id) {
  const L = LENTES.find(l => l.id === id) || E.lenteCustom;
  if (!L) return;
  E.lente = L.id; E.faixa = null;
  if (L.modo === 'terreno') { valHex = null; tHex = null; infoLente = { L }; }
  else { valHex = valoresLente(L); tHex = prepararEscala(L, valHex); }
  try { history.replaceState(null, '', '#' + L.id); } catch (e) { /* sem hash */ }
  desenharLegenda();
  $$('#lentes .ln').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.id === L.id)));
  $$('#todas-lentes button').forEach(b => b.classList.toggle('ativo', b.dataset.id === L.id));
  sujar();
}

function corHex(i) {
  if (!tHex) return corTerreno[i];
  const t = tHex[i];
  if (!ok(t)) return '#3a4146';
  if (t < 0) return '#262f33';
  if (E.faixa && (t < E.faixa[0] || t > E.faixa[1])) return '#2a3337';
  const L = infoLente.L;
  // sombreado leve do relevo também nas lentes
  const base = rampa(L.paleta, t);
  return base;
}

/* ---------- legenda ---------- */
function desenharLegenda() {
  const L = infoLente.L;
  const el = $('#legenda');
  if (L.modo === 'terreno') {
    el.innerHTML = `<div class="tit">${L.ic} Terreno</div><div class="sub">${esc(L.sub)}</div><div id="leg-cats">${M.terrenos.filter(t => t.usado).map(t => `<span><i style="background:${t.cor}"></i>${esc(t.nome)}</span>`).join('')}</div>`;
    return;
  }
  el.innerHTML = `<div class="tit">${L.ic} ${esc(L.nome)}</div><div class="sub">${esc(L.sub)}</div><canvas id="leg-escala" width="400" height="14" aria-label="Escala da lente"></canvas><div id="leg-ticks"></div>`;
  const c = $('#leg-escala'), g = c.getContext('2d');
  for (let x = 0; x < 400; x++) {
    const t = x / 399;
    g.fillStyle = E.faixa && (t < E.faixa[0] || t > E.faixa[1]) ? '#2a3337' : rampa(L.paleta, t);
    g.fillRect(x, 0, 1, 14);
  }
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(q => `<span>${fmt(infoLente.inv(q), L.fmt)}</span>`);
  $('#leg-ticks').innerHTML = ticks.join('');
  let arr = null;
  const tAt = ev => { const r = c.getBoundingClientRect(); return Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)); };
  c.onpointerdown = ev => { arr = tAt(ev); c.setPointerCapture(ev.pointerId); };
  c.onpointermove = ev => {
    const t = tAt(ev);
    E.faixa = arr !== null ? [Math.min(arr, t), Math.max(arr, t) + 0.001] : [Math.max(0, t - 0.06), Math.min(1, t + 0.06)];
    redesenharEscala(); sujar();
  };
  c.onpointerup = () => { arr = null; };
  c.onpointerleave = () => { if (arr === null) { E.faixa = null; redesenharEscala(); sujar(); } };
  c.ondblclick = () => { E.faixa = null; redesenharEscala(); sujar(); };
}
function redesenharEscala() {
  const c = $('#leg-escala'); if (!c) return;
  const g = c.getContext('2d'), L = infoLente.L;
  for (let x = 0; x < 400; x++) { const t = x / 399; g.fillStyle = E.faixa && (t < E.faixa[0] || t > E.faixa[1]) ? '#2a3337' : rampa(L.paleta, t); g.fillRect(x, 0, 1, 14); }
}

/* ---------- vista ---------- */
function redimensionar() {
  E.dpr = Math.min(2, window.devicePixelRatio || 1);
  E.W = cv.clientWidth; E.H = cv.clientHeight;
  cv.width = Math.round(E.W * E.dpr); cv.height = Math.round(E.H * E.dpr);
  sujar();
}
function enquadrar(minx, miny, maxx, maxy, anim = true, margem = 0.08) {
  const movel = window.innerWidth < 760, aberto = !$('#painel').hidden;
  const topo = 56, base = movel ? (aberto ? $('#painel').offsetHeight + 10 : 120) : 150;
  const painel = aberto && !movel ? 400 : 0;
  const w = E.W - painel, h = E.H - topo - base;
  const s = Math.min(w / ((maxx - minx) * (1 + margem)), h / ((maxy - miny) * (1 + margem)));
  const cx = (minx + maxx) / 2 + painel / 2 / s, cy = (miny + maxy) / 2 - (base - topo) / 2 / s;
  irPara(cx, cy, s, anim);
}
function enquadrarBrasil(anim = true) {
  const b = M.bbox;
  enquadrar(b[0], b[1], b[2], b[3], anim, 0.02);
  if (!anim) E.sFit = E.s;
}
function irPara(cx, cy, s, anim = true) {
  s = Math.max(E.sFit * 0.6 || 0.05, Math.min(40, s));
  if (!anim || matchMedia('(prefers-reduced-motion: reduce)').matches) { E.cx = cx; E.cy = cy; E.s = s; E.anim = null; sujar(); return; }
  E.anim = { t0: performance.now(), d: 650, a: { cx: E.cx, cy: E.cy, s: E.s }, b: { cx, cy, s } };
  sujar();
}
const paraTela = (x, y) => [(x - E.cx) * E.s + E.W / 2, -(y - E.cy) * E.s + E.H / 2];
const paraMundo = (sx, sy) => [(sx - E.W / 2) / E.s + E.cx, -(sy - E.H / 2) / E.s + E.cy];
function hexEm(x, y) {
  const R = M.R;
  let q = (SQ3 / 3 * x - y / 3) / R, r = (2 / 3 * y) / R, s = -q - r;
  let rq = Math.round(q), rr = Math.round(r), rs = Math.round(s);
  const dq = Math.abs(rq - q), dr = Math.abs(rr - r), ds = Math.abs(rs - s);
  if (dq > dr && dq > ds) rq = -rr - rs; else if (dr > ds) rr = -rq - rs;
  const i = IDX.get(chave(rq, rr));
  return i === undefined ? -1 : i;
}

/* ---------- desenho ---------- */
function sujar() { if (!E.sujo) { E.sujo = true; requestAnimationFrame(quadro); } else if (!E.raf) { E.raf = requestAnimationFrame(quadro); } }
function quadro(now) {
  E.raf = null;
  if (E.anim) {
    const { t0, d, a, b } = E.anim;
    let t = Math.min(1, (now - t0) / d); const k = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    const la = Math.log(a.s), lb = Math.log(b.s);
    E.s = Math.exp(la + (lb - la) * k); E.cx = a.cx + (b.cx - a.cx) * k; E.cy = a.cy + (b.cy - a.cy) * k;
    if (t >= 1) E.anim = null;
  }
  E.sujo = false;
  desenhar();
  desenharMini();
  if (E.anim) { E.sujo = true; E.raf = requestAnimationFrame(quadro); }
}

function desenhar() {
  const { W, H, dpr, s } = E, R = M.R;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = '#081b25'; ctx.fillRect(0, 0, W, H);
  const [x0, y1] = paraMundo(0, 0), [x1, y0] = paraMundo(W, H);
  const vis = i => HX[i] > x0 - R * 2 && HX[i] < x1 + R * 2 && HY[i] > y0 - R * 2 && HY[i] < y1 + R * 2;

  // países vizinhos
  ctx.save();
  ctx.setTransform(dpr * s, 0, 0, -dpr * s, dpr * (W / 2 - E.cx * s), dpr * (H / 2 + E.cy * s));
  ctx.fillStyle = '#1b2a30'; ctx.strokeStyle = '#2c3e46'; ctx.lineWidth = 1.2 / s;
  for (const p of M.paises) { ctx.beginPath(); for (const anel of p.p) { ctx.moveTo(anel[0], anel[1]); for (let k = 2; k < anel.length; k += 2) ctx.lineTo(anel[k], anel[k + 1]); ctx.closePath(); } ctx.fill(); ctx.stroke(); }
  ctx.restore();

  // hexágonos
  const rr = R * s + 0.6;
  const ox = [], oy = [];
  for (let k = 0; k < 6; k++) { const a = (60 * k - 30) * Math.PI / 180; ox.push(rr * Math.cos(a)); oy.push(-rr * Math.sin(a)); }
  const grupos = new Map();
  const mares = ['#0f3140', '#0d2b39', '#0a2330'];
  for (let i = 0; i < N; i++) {
    if (!vis(i)) continue;
    const cor = M.terra[i] ? corHex(i) : mares[(M.anel[i] || 3) - 1];
    if (!cor) continue;
    let p = grupos.get(cor); if (!p) { p = new Path2D(); grupos.set(cor, p); }
    const [sx, sy] = paraTela(HX[i], HY[i]);
    p.moveTo(sx + ox[0], sy + oy[0]); for (let k = 1; k < 6; k++) p.lineTo(sx + ox[k], sy + oy[k]); p.closePath();
  }
  for (const [cor, p] of grupos) { ctx.fillStyle = cor; ctx.fill(p); }

  // glifos do terreno
  const px = R * s;
  if (!tHex && px > 7) desenharGlifos(vis, px);

  // rios
  if (M.rios) {
    ctx.save();
    ctx.setTransform(dpr * s, 0, 0, -dpr * s, dpr * (W / 2 - E.cx * s), dpr * (H / 2 + E.cy * s));
    ctx.strokeStyle = tHex ? 'rgba(120,180,220,.35)' : 'rgba(86,160,214,.9)'; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    for (const rio of M.rios) {
      if (rio.w > 2 && s < E.sFit * 1.6) continue;
      ctx.lineWidth = Math.max(0.6, (4 - rio.w) * 0.9 * Math.min(2.2, Math.sqrt(s / E.sFit))) / s;
      ctx.beginPath(); const p = rio.p; ctx.moveTo(p[0], p[1]); for (let k = 2; k < p.length; k += 2) ctx.lineTo(p[k], p[k + 1]); ctx.stroke();
    }
    ctx.restore();
  }

  // fronteiras estaduais e costa
  const costa = new Path2D(), divisa = new Path2D();
  for (let i = 0; i < N; i++) {
    if (!M.terra[i] || !vis(i)) continue;
    const [sx, sy] = paraTela(HX[i], HY[i]);
    for (let k = 0; k < 6; k++) {
      const j = NB[i * 6 + k];
      const mar = j < 0 || !M.terra[j];
      const div = !mar && UFH[j] !== UFH[i] && j > i;
      if (!mar && !div) continue;
      const p = mar ? costa : divisa;
      const k2 = (k + 1) % 6;
      p.moveTo(sx + ox[k] * 0.98, sy + oy[k] * 0.98); p.lineTo(sx + ox[k2] * 0.98, sy + oy[k2] * 0.98);
    }
  }
  ctx.lineCap = 'round';
  ctx.strokeStyle = 'rgba(233,225,204,.55)'; ctx.lineWidth = Math.max(1, Math.min(2.2, px / 8));
  ctx.setLineDash([Math.max(2, px / 4), Math.max(2, px / 5)]); ctx.stroke(divisa); ctx.setLineDash([]);
  ctx.strokeStyle = 'rgba(214,236,240,.55)'; ctx.lineWidth = Math.max(1, Math.min(2.5, px / 7)); ctx.stroke(costa);

  // seleção
  if (E.sel) desenharSelecao(vis, ox, oy);
  // hover
  if (E.hover >= 0 && M.terra[E.hover]) {
    const [sx, sy] = paraTela(HX[E.hover], HY[E.hover]);
    ctx.beginPath(); ctx.moveTo(sx + ox[0], sy + oy[0]); for (let k = 1; k < 6; k++) ctx.lineTo(sx + ox[k], sy + oy[k]); ctx.closePath();
    ctx.strokeStyle = '#fff6d8'; ctx.lineWidth = 2; ctx.stroke();
  }

  // pontos (recursos e maravilhas)
  desenharPontos();
  // cidades
  desenharCidades();
  desenharRotulos();
}
function desenharRotulos() {
  ctx.save(); ctx.font = '600 11px "Source Sans 3", sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  const ocup = banners.map(b => ({ ...b }));
  for (const r of E.rotulos || []) {
    const nome = r.p.n.length > 42 ? r.p.n.slice(0, 40) + '…' : r.p.n;
    const w = ctx.measureText(nome).width + 10, box = { x: r.sx - w / 2, y: r.sy, w, h: 16 };
    if (ocup.some(b => box.x < b.x + b.w && box.x + box.w > b.x && box.y < b.y + b.h && box.y + box.h > b.y)) continue;
    ocup.push(box);
    ctx.fillStyle = 'rgba(20,35,43,.9)'; ctx.fillRect(box.x, box.y, w, 16);
    ctx.fillStyle = '#f0d48a'; ctx.fillText(nome, r.sx, r.sy + 8.5);
  }
  ctx.restore();
}

function desenharGlifos(vis, px) {
  ctx.save();
  const florestas = M.glifo;
  for (let i = 0; i < N; i++) {
    if (!M.terra[i] || !vis(i)) continue;
    const g = florestas[M.terreno[i]], rel = M.relevo[i];
    const [sx, sy] = paraTela(HX[i], HY[i]);
    if (rel === 2) {
      ctx.fillStyle = 'rgba(70,52,38,.55)'; ctx.strokeStyle = 'rgba(250,240,220,.5)'; ctx.lineWidth = 1;
      const w = px * 0.55, h = px * 0.62, dx = (hash01(i, 3) - 0.5) * px * 0.3;
      ctx.beginPath(); ctx.moveTo(sx + dx - w, sy + h * 0.45); ctx.lineTo(sx + dx, sy - h * 0.6); ctx.lineTo(sx + dx + w, sy + h * 0.45); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(sx + dx - w * 0.28, sy - h * 0.18); ctx.lineTo(sx + dx, sy - h * 0.6); ctx.lineTo(sx + dx + w * 0.22, sy - h * 0.26); ctx.stroke();
    } else if (rel === 1) {
      ctx.strokeStyle = 'rgba(60,45,30,.45)'; ctx.lineWidth = Math.max(1, px / 12);
      ctx.beginPath(); ctx.arc(sx - px * 0.22, sy + px * 0.2, px * 0.3, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke();
      ctx.beginPath(); ctx.arc(sx + px * 0.25, sy + px * 0.05, px * 0.25, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke();
    }
    if (g && rel !== 2 && px > 9) {
      const n = g.n, cor = g.cor;
      ctx.fillStyle = cor;
      for (let k = 0; k < n; k++) {
        const a = hash01(i, k * 2 + 7) * Math.PI * 2, d = Math.sqrt(hash01(i, k * 2 + 8)) * px * 0.55;
        const tx = sx + Math.cos(a) * d, ty = sy + Math.sin(a) * d;
        const r = px * g.r;
        if (g.forma === 'copa') { ctx.beginPath(); ctx.arc(tx, ty, r, 0, Math.PI * 2); ctx.fill(); }
        else if (g.forma === 'tufo') { ctx.fillRect(tx - r * 0.15, ty - r, r * 0.3, r * 1.4); ctx.fillRect(tx - r * 0.7, ty - r * 0.2, r * 1.4, r * 0.25); }
        else if (g.forma === 'risco') { ctx.fillRect(tx - r, ty, r * 2, Math.max(1, r * 0.3)); }
        else if (g.forma === 'ponto') { ctx.fillRect(tx - r / 2, ty - r / 2, r, r); }
      }
    }
  }
  ctx.restore();
}

function desenharSelecao(vis, ox, oy) {
  const sel = E.sel;
  const dentro = i => sel.tipo === 'mun' ? MH[i] === sel.i : UFH[i] === sel.i;
  const p = new Path2D(), fill = new Path2D();
  for (let i = 0; i < N; i++) {
    if (!M.terra[i] || !vis(i) || !dentro(i)) continue;
    const [sx, sy] = paraTela(HX[i], HY[i]);
    fill.moveTo(sx + ox[0], sy + oy[0]); for (let k = 1; k < 6; k++) fill.lineTo(sx + ox[k], sy + oy[k]); fill.closePath();
    for (let k = 0; k < 6; k++) {
      const j = NB[i * 6 + k];
      if (j >= 0 && M.terra[j] && dentro(j)) continue;
      const k2 = (k + 1) % 6;
      p.moveTo(sx + ox[k], sy + oy[k]); p.lineTo(sx + ox[k2], sy + oy[k2]);
    }
  }
  ctx.fillStyle = 'rgba(255,240,200,.12)'; ctx.fill(fill);
  ctx.strokeStyle = '#f0d48a'; ctx.lineWidth = 2.5; ctx.lineCap = 'round'; ctx.stroke(p);
}

const ZT = [0, 1.6, 3.2, 6.5, 99];   // zoom relativo mínimo por nível de ponto
function desenharPontos() {
  pontosVis = []; E.rotulos = [];
  const rel = E.s / E.sFit;
  ctx.save();
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  for (const p of X.pontos) {
    const marav = p.mar;
    if (!E.recursos && !marav) continue;
    if (rel < ZT[p.z ?? 3]) continue;
    const [sx, sy] = paraTela(p.x, p.y);
    if (sx < -20 || sy < -20 || sx > E.W + 20 || sy > E.H + 20) continue;
    const tam = marav ? Math.min(26, 15 + rel * 1.2) : Math.min(20, 11 + rel * 0.8);
    if (!marav && pontosVis.some(o => Math.abs(o.sx - sx) < tam * 0.95 && Math.abs(o.sy - sy) < tam * 0.95)) continue;
    if (marav) {
      ctx.beginPath(); ctx.arc(sx, sy, tam * 0.72, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(20,35,43,.92)'; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = '#d4a845'; ctx.stroke();
    } else {
      ctx.beginPath(); ctx.arc(sx, sy, tam * 0.62, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(15,26,32,.78)'; ctx.fill();
    }
    ctx.font = `${Math.round(tam * 0.78)}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif`;
    ctx.fillStyle = '#fff'; ctx.fillText(p.ic, sx, sy + 1);
    if (marav && rel > 3.5) E.rotulos.push({ p, sx, sy: sy + tam * 0.8 });
    pontosVis.push({ p, sx, sy, r: tam * 0.72 });
  }
  ctx.restore();
}

function desenharCidades() {
  banners = [];
  const rel = E.s / E.sFit;
  const minPop = rel < 1.3 ? 600000 : Math.max(8000, 600000 / Math.pow(rel / 1.1, 1.7));
  const ocup = [];
  const bate = (a) => ocup.some(b => a.x < b.x + b.w + 4 && a.x + a.w + 4 > b.x && a.y < b.y + b.h + 3 && a.y + a.h + 3 > b.y);
  const maxN = Math.round(E.W * E.H / 11000);
  ctx.save();
  ctx.textBaseline = 'middle';
  for (const i of E.cidades) {
    const pop = MU.col.pop[i];
    const cap = MU.capital[i];
    if (pop < minPop && !(cap && rel > 0.9)) continue;
    const [sx, sy] = paraTela(MU.x[i], MU.y[i]);
    if (sx < -60 || sy < -20 || sx > E.W + 60 || sy > E.H + 20) continue;
    ctx.font = '700 11px "Source Sans 3", sans-serif';
    const nome = MU.nome[i].toUpperCase();
    const wn = ctx.measureText(nome).width;
    ctx.font = '600 10px "IBM Plex Mono", monospace';
    const pt = compacto(pop).replace(' mil', 'k').replace(' mi', 'M');
    const wp = ctx.measureText(pt).width;
    const w = wp + wn + 26 + (cap ? 12 : 0), h = 18;
    const box = { x: sx - 6, y: sy - h / 2, w, h };
    if (bate(box)) continue;
    ocup.push(box);
    const reg = MU.ufs[MU.uf[i]].regiao;
    const cor = COR_REGIAO[reg] || '#888';
    // marcador da cidade
    ctx.beginPath(); ctx.arc(sx, sy, 4, 0, Math.PI * 2); ctx.fillStyle = '#fff6d8'; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = '#14232b'; ctx.stroke();
    const bx = sx + 7;
    ctx.fillStyle = 'rgba(14,24,30,.92)'; rrect(bx, sy - h / 2, w - 7, h, 4); ctx.fill();
    ctx.strokeStyle = cor; ctx.lineWidth = 1; ctx.stroke();
    ctx.fillStyle = cor; rrect(bx, sy - h / 2, wp + 10, h, 4); ctx.fill();
    ctx.fillStyle = '#0c151a'; ctx.font = '600 10px "IBM Plex Mono", monospace'; ctx.fillText(pt, bx + 5, sy + 0.5);
    ctx.fillStyle = '#efe7d2'; ctx.font = '700 11px "Source Sans 3", sans-serif';
    ctx.fillText((cap ? '★ ' : '') + nome, bx + wp + 15, sy + 0.5);
    banners.push({ i, x: sx - 6, y: sy - h / 2, w: w + 2, h });
    if (banners.length > maxN) break;
  }
  ctx.restore();
}
function rrect(x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }

/* ---------- minimapa ---------- */
function montarMini() {
  const b = M.bbox, w = mini.width, h = mini.height;
  const s = Math.min(w / (b[2] - b[0]), h / (b[3] - b[1])) * 0.94;
  E.mini = { s, cx: (b[0] + b[2]) / 2, cy: (b[1] + b[3]) / 2 };
  const off = document.createElement('canvas'); off.width = w; off.height = h;
  const g = off.getContext('2d');
  g.fillStyle = '#0c2633'; g.fillRect(0, 0, w, h);
  const r = M.R * s * 1.15;
  for (let i = 0; i < N; i++) {
    if (!M.terra[i]) continue;
    g.fillStyle = corTerreno[i];
    const x = (HX[i] - E.mini.cx) * s + w / 2, y = -(HY[i] - E.mini.cy) * s + h / 2;
    g.fillRect(x - r, y - r, r * 2, r * 2);
  }
  miniBase = off;
}
function desenharMini() {
  if (!miniBase || $('#mini').offsetParent === null) return;
  const w = mini.width, h = mini.height, m = E.mini;
  mctx.drawImage(miniBase, 0, 0);
  const [x0, y1] = paraMundo(0, 0), [x1, y0] = paraMundo(E.W, E.H);
  const a = (x0 - m.cx) * m.s + w / 2, b = -(y1 - m.cy) * m.s + h / 2;
  const c = (x1 - m.cx) * m.s + w / 2, d = -(y0 - m.cy) * m.s + h / 2;
  mctx.strokeStyle = '#f0d48a'; mctx.lineWidth = 1.5; mctx.strokeRect(a, b, c - a, d - b);
}
function miniIr(ev) {
  const r = mini.getBoundingClientRect(), m = E.mini;
  const x = (ev.clientX - r.left) * (mini.width / r.width), y = (ev.clientY - r.top) * (mini.height / r.height);
  E.cx = (x - mini.width / 2) / m.s + m.cx; E.cy = -(y - mini.height / 2) / m.s + m.cy; E.anim = null; sujar();
}

/* ---------- interação ---------- */
function montarInteracao() {
  const ptrs = new Map();
  let arrasto = null, pinca = null, moveu = false;
  cv.addEventListener('pointerdown', ev => {
    cv.setPointerCapture(ev.pointerId);
    ptrs.set(ev.pointerId, [ev.clientX, ev.clientY]);
    moveu = false; E.anim = null;
    if (ptrs.size === 1) arrasto = { x: ev.clientX, y: ev.clientY, cx: E.cx, cy: E.cy };
    else if (ptrs.size === 2) {
      const [a, b] = [...ptrs.values()];
      pinca = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), s: E.s, m: paraMundo((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) };
      arrasto = null;
    }
  });
  cv.addEventListener('pointermove', ev => {
    if (ptrs.has(ev.pointerId)) ptrs.set(ev.pointerId, [ev.clientX, ev.clientY]);
    if (pinca && ptrs.size === 2) {
      const [a, b] = [...ptrs.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      const s = Math.max(E.sFit * 0.6, Math.min(40, pinca.s * d / pinca.d));
      const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
      E.s = s; E.cx = pinca.m[0] - (mx - E.W / 2) / s; E.cy = pinca.m[1] + (my - E.H / 2) / s;
      moveu = true; sujar(); return;
    }
    if (arrasto) {
      const dx = ev.clientX - arrasto.x, dy = ev.clientY - arrasto.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) { moveu = true; cv.classList.add('arrastando'); }
      if (moveu) { E.cx = arrasto.cx - dx / E.s; E.cy = arrasto.cy + dy / E.s; $('#dica').hidden = true; sujar(); }
      return;
    }
    passarMouse(ev);
  });
  const fim = ev => {
    ptrs.delete(ev.pointerId);
    if (ptrs.size < 2) pinca = null;
    if (ptrs.size === 0) {
      if (arrasto && !moveu && ev.type === 'pointerup') clicar(ev);
      arrasto = null; cv.classList.remove('arrastando');
    }
  };
  cv.addEventListener('pointerup', fim);
  cv.addEventListener('pointercancel', fim);
  cv.addEventListener('pointerleave', () => { E.hover = -1; $('#dica').hidden = true; sujar(); });
  cv.addEventListener('wheel', ev => {
    ev.preventDefault();
    const f = Math.exp(-ev.deltaY * (ev.ctrlKey ? 0.01 : 0.0018));
    zoomEm(ev.clientX - cv.getBoundingClientRect().left, ev.clientY - cv.getBoundingClientRect().top, f);
  }, { passive: false });
  cv.addEventListener('dblclick', ev => { const r = cv.getBoundingClientRect(); const [x, y] = paraMundo(ev.clientX - r.left, ev.clientY - r.top); irPara(x, y, E.s * 2.2); });
  let miniArr = false;
  mini.addEventListener('pointerdown', ev => { miniArr = true; mini.setPointerCapture(ev.pointerId); miniIr(ev); });
  mini.addEventListener('pointermove', ev => { if (miniArr) miniIr(ev); });
  mini.addEventListener('pointerup', () => { miniArr = false; });
  window.addEventListener('resize', redimensionar);
  window.addEventListener('hashchange', () => { const h = location.hash.slice(1); if (h !== E.lente && LENTES.some(l => l.id === h && lenteDisponivel(l))) usarLente(h); });
  window.addEventListener('keydown', teclado);
}
function zoomEm(sx, sy, f) {
  const [x, y] = paraMundo(sx, sy);
  const s = Math.max(E.sFit * 0.6, Math.min(40, E.s * f));
  E.s = s; E.cx = x - (sx - E.W / 2) / s; E.cy = y + (sy - E.H / 2) / s; E.anim = null; sujar();
}
function teclado(ev) {
  const alvo = ev.target;
  if (alvo.tagName === 'INPUT' || alvo.tagName === 'SELECT' || alvo.tagName === 'TEXTAREA') {
    if (ev.key === 'Escape') { alvo.blur(); $('#busca-res').hidden = true; }
    return;
  }
  const passo = 120 / E.s;
  const k = ev.key;
  if (k === 'Escape') {
    const aberto = $$('.modal').find(m => !m.hidden);
    if (aberto) { aberto.hidden = true; return; }
    if (!$('#todas-lentes').hidden) { $('#todas-lentes').hidden = true; return; }
    fecharPainel(); return;
  }
  if ($$('.modal').some(m => !m.hidden)) return;
  if (k === '/' || (k === 'k' && (ev.metaKey || ev.ctrlKey))) { ev.preventDefault(); $('#busca').focus(); return; }
  if (k === 'ArrowLeft' || k === 'a') { E.cx -= passo; sujar(); }
  else if (k === 'ArrowRight' || k === 'd') { E.cx += passo; sujar(); }
  else if (k === 'ArrowUp' || k === 'w') { E.cy += passo; sujar(); }
  else if (k === 'ArrowDown' || k === 's') { E.cy -= passo; sujar(); }
  else if (k === '+' || k === '=') zoomEm(E.W / 2, E.H / 2, 1.4);
  else if (k === '-' || k === '_') zoomEm(E.W / 2, E.H / 2, 1 / 1.4);
  else if (k === 'l' || k === 'L') {
    const disp = LENTES.filter(lenteDisponivel);
    const i = disp.findIndex(l => l.id === E.lente);
    usarLente(disp[(i + (ev.shiftKey ? -1 : 1) + disp.length) % disp.length].id);
  } else if (k === 'r' || k === 'R') { E.recursos = !E.recursos; sujar(); }
  else if (k === '?') $('#m-ajuda').hidden = false;
}

function pontoEm(sx, sy) {
  for (let k = pontosVis.length - 1; k >= 0; k--) { const v = pontosVis[k]; if (Math.hypot(sx - v.sx, sy - v.sy) <= v.r + 2) return v.p; }
  return null;
}
function bannerEm(sx, sy) { return banners.find(b => sx >= b.x && sx <= b.x + b.w && sy >= b.y && sy <= b.y + b.h); }

function passarMouse(ev) {
  const r = cv.getBoundingClientRect();
  const sx = ev.clientX - r.left, sy = ev.clientY - r.top;
  const dica = $('#dica');
  const pt = pontoEm(sx, sy);
  const bn = !pt && bannerEm(sx, sy);
  const [x, y] = paraMundo(sx, sy);
  const i = hexEm(x, y);
  if (i !== E.hover) { E.hover = i; sujar(); }
  let html = '';
  if (pt) html = `<b>${esc(pt.n)}</b><br>${esc(pt.d || '')}${ok(pt.v) ? `<br><span class="v">${esc(pt.vt || fmt(pt.v, pt.f || 'c'))}</span>` : ''}${pt.mar ? '<br><span class="v">★ Maravilha</span>' : ''}`;
  else if (bn) html = `<b>${esc(MU.nome[bn.i])}</b> · ${esc(MU.ufs[MU.uf[bn.i]].sigla)}<br><span class="v">${fmt(MU.col.pop[bn.i], 'int')}</span> habitantes`;
  else if (i >= 0 && M.terra[i]) {
    const m = MH[i];
    const nome = m >= 0 ? `${esc(MU.nome[m])} · ${esc(MU.ufs[MU.uf[m]].sigla)}` : esc(MU.ufs[UFH[i]]?.nome || '');
    const ter = M.terrenos[M.terreno[i]]?.nome || '';
    let val = '';
    if (valHex) val = `<br>${esc(infoLente.L.nome)}: <span class="v">${fmt(valHex[i], infoLente.L.fmt)}</span>`;
    html = `<b>${nome}</b><br>${esc(ter)}${M.elev[i] != null ? ` · ${NF.format(M.elev[i])} m` : ''}${val}`;
  }
  if (!html) { dica.hidden = true; return; }
  dica.innerHTML = html; dica.hidden = false;
  const w = dica.offsetWidth, h = dica.offsetHeight;
  dica.style.left = Math.min(E.W - w - 8, sx + 14) + 'px';
  dica.style.top = Math.min(E.H - h - 8, sy + 14) + 'px';
}

function clicar(ev) {
  const r = cv.getBoundingClientRect();
  const sx = ev.clientX - r.left, sy = ev.clientY - r.top;
  const pt = pontoEm(sx, sy);
  if (pt && pt.m >= 0) { abrirMun(pt.m, false, pt); return; }
  const bn = bannerEm(sx, sy);
  if (bn) { abrirMun(bn.i, false); return; }
  const [x, y] = paraMundo(sx, sy);
  const i = hexEm(x, y);
  if (i >= 0 && M.terra[i] && MH[i] >= 0) abrirMun(MH[i], false);
  else fecharPainel();
}

/* ---------- painel ---------- */
const cacheRank = {};
function rank(col, i, base = 'mun') {
  const key = base + ':' + col;
  if (!cacheRank[key]) {
    const v = base === 'mun' ? MU.col[col] : MU.ufAgg.map(a => a[col]);
    if (!v) return null;
    const ids = [...v.keys()].filter(k => ok(v[k])).sort((a, b) => v[b] - v[a]);
    const pos = new Map(ids.map((k, p) => [k, p + 1]));
    cacheRank[key] = { pos, n: ids.length };
  }
  const c = cacheRank[key];
  return c.pos.has(i) ? [c.pos.get(i), c.n] : null;
}

const RENDIMENTOS = [
  { k: 'va_agro', nome: 'Comida', ic: '🌾', fmt: 'brl', lente: 'comida' },
  { k: 'va_ind', nome: 'Produção', ic: '⚙', fmt: 'brl', lente: 'producao' },
  { k: 'pib', nome: 'Ouro', ic: '💰', fmt: 'brl', lente: 'ouro' },
  { k: 'ciencia', nome: 'Ciência', ic: '🔬', fmt: 'c', lente: 'ciencia', dica: 'Empregos formais em informação, comunicação e serviços científicos e técnicos' },
  { k: 'energia_mw', nome: 'Energia', ic: '⚡', fmt: 'mw', lente: 'energia' },
  { k: 'cultura', nome: 'Cultura', ic: '🎭', fmt: 'c', lente: 'cultura', dica: 'Empregos formais em artes, cultura, esporte e recreação' },
];

function caixaRend(get, base, i) {
  return `<div class="ylds">${RENDIMENTOS.filter(r => MU.col[r.k]).map(r => {
    const v = get(r.k); const rk = rank(r.k, i, base);
    return `<div class="yl" title="${esc(r.dica || r.nome)}"><div class="ic">${r.ic}</div><div class="v">${fmt(v, r.fmt)}</div><div class="k">${r.nome}</div>${rk ? `<div class="rk">#${NF.format(rk[0])} de ${NF.format(rk[1])}</div>` : ''}</div>`;
  }).join('')}</div>`;
}

function comparar(v, br, f, maiorMelhor = true) {
  if (!ok(v) || !ok(br)) return '';
  const up = v >= br;
  const cls = (up === maiorMelhor) ? 'up' : 'down';
  return `<span class="cmp ${cls}">${up ? '▲' : '▼'} BR ${fmt(br, f)}</span>`;
}

const INDICADORES = [
  ['renda', 'Renda por pessoa', 'brl0', true], ['superior', 'Curso superior (25+)', 'pct', true], ['alfab', 'Alfabetização (15+)', 'pct', true],
  ['esgoto', 'Esgoto adequado', 'pct', true], ['agua', 'Água da rede geral', 'pct', true], ['idade', 'Idade mediana', 'anos', null],
  ['idhm', 'IDHM (2010)', 'dec3', true], ['pct_indig', 'Indígenas', 'pct', null], ['pct_quil', 'Quilombolas', 'pct', null],
  ['desastres', 'Desastres reconhecidos', 'int', false],
];

function blocoIndicadores(get) {
  const linhas = INDICADORES.filter(([k]) => MU.col[k] && ok(get(k))).map(([k, nome, f, mm]) =>
    `<span>${nome}</span><span>${fmt(get(k), f)}${mm === null ? '' : comparar(get(k), MU.br[k], f, mm)}</span>`).join('');
  return linhas ? `<div class="sec"><h3>Comodidades</h3><div class="kv">${linhas}</div></div>` : '';
}

function blocoFe(get) {
  const rel = [['rel_cat', 'Católicos', '#8170bd'], ['rel_evan', 'Evangélicos', '#b8698f'], ['rel_esp', 'Espíritas', '#4f86c6'], ['rel_afro', 'Matriz africana', '#3a9a98'], ['rel_sem', 'Sem religião', '#a9b3ad']]
    .filter(([k]) => MU.col[k] && ok(get(k)));
  if (!rel.length) return '';
  const tot = rel.reduce((s, [k]) => s + get(k), 0);
  const outros = Math.max(0, 100 - tot);
  return `<div class="sec"><h3>Fé <small>${esc(MU.meta.ano_religiao || '')}</small></h3>
    <div class="empilha">${rel.map(([k, , c]) => `<i style="width:${get(k)}%;background:${c}"></i>`).join('')}<i style="width:${outros}%;background:#3a4146"></i></div>
    <div class="leg-mini">${rel.map(([k, n, c]) => `<span><b style="background:${c}"></b>${n} ${fmt(get(k), 'pct')}</span>`).join('')}<span><b style="background:#3a4146"></b>Outras ${fmt(outros, 'pct')}</span></div></div>`;
}

function blocoSolo(get) {
  const cl = [['flor_pct', 'Floresta', '#1d6b48'], ['sav_pct', 'Cerrado e campos', '#a8b85c'], ['past_pct', 'Pasto', '#d8c27a'], ['agri_pct', 'Lavoura', '#e59a4a'], ['silv_pct', 'Silvicultura', '#7a5a8f'], ['urb_pct', 'Cidade', '#c9504a'], ['agua_pct', 'Água', '#3e7fb3']]
    .filter(([k]) => MU.col[k] && ok(get(k)));
  if (!cl.length) return '';
  const perda = MU.col.perda_flor && ok(get('perda_flor')) && get('perda_flor') > 0.5 ? `<div class="nota">Desde 1985, ${fmt(get('perda_flor'), 'pct')} da floresta natural virou outra coisa.</div>` : '';
  return `<div class="sec"><h3>Cobertura do solo <small>MapBiomas ${esc(MU.meta.ano_cobertura || '')}</small></h3>
    <div class="empilha">${cl.map(([k, , c]) => `<i style="width:${Math.max(0, get(k))}%;background:${c}"></i>`).join('')}</div>
    <div class="leg-mini">${cl.filter(([k]) => get(k) >= 1).map(([k, n, c]) => `<span><b style="background:${c}"></b>${n} ${fmt(get(k), 'pct')}</span>`).join('')}</div>${perda}</div>`;
}

function empregosDe(lista) {
  // soma empregos por seção para uma lista de municípios
  const S = MU.empregos; if (!S) return null;
  const n = S.secoes.length, v = new Float64Array(n);
  for (const i of lista) { const e = S.v[i]; if (e) for (let k = 0; k < n; k++) v[k] += e[k] || 0; }
  return v;
}
function blocoTrabalho(v, nomeLugar) {
  const S = MU.empregos; if (!S || !v) return '';
  const br = S.br; const tot = v.reduce((a, b) => a + b, 0), totBr = br.reduce((a, b) => a + b, 0);
  if (tot < 50) return '';
  const linhas = S.secoes.map((s, k) => ({ s, k, e: v[k], sh: v[k] / tot, lq: (v[k] / tot) / (br[k] / totBr) })).filter(x => x.e > 0);
  const top = linhas.slice().sort((a, b) => b.e - a.e).slice(0, 8);
  const maxSh = top[0]?.sh || 1;
  const dist = linhas.filter(x => x.lq >= 1.5 && x.e >= Math.max(150, tot * 0.03) && DISTRITO[x.s.l]).sort((a, b) => b.lq - a.lq).slice(0, 4);
  const destaque = linhas.filter(x => x.e >= Math.max(100, tot * 0.03)).sort((a, b) => b.lq - a.lq)[0];
  let cid = '';
  if (destaque && destaque.lq >= 1.3) {
    const um = Math.max(1, Math.round(1 / destaque.sh)), umBr = Math.max(1, Math.round(totBr / br[destaque.k]));
    cid = `<div class="cidadaos">1 em cada ${um} trabalhadores com carteira de ${esc(nomeLugar)} está em <b>${esc(destaque.s.d.toLowerCase())}</b>, contra 1 em ${umBr} no Brasil.</div>`;
  }
  return `${dist.length ? `<div class="sec"><h3>Distritos <small>onde ${esc(nomeLugar)} se especializou</small></h3><div class="chips">${dist.map(x => `<span class="chip dist" title="${esc(x.s.d)}: ${NF1.format(x.lq)} vezes a média do país">${DISTRITO[x.s.l][1]} ${DISTRITO[x.s.l][0]}</span>`).join('')}</div></div>` : ''}
  <div class="sec"><h3>Cidadãos <small>${NF.format(Math.round(tot))} empregos formais · ${esc(S.ano)}</small></h3>${cid}
  <div style="margin-top:10px">${top.map(x => `<div class="barra"><span>${esc(x.s.d)}${x.lq >= 1.3 ? `<span class="lq">×${NF1.format(x.lq)}</span>` : ''}</span><span class="val">${compacto(x.e)} · ${NF1.format(x.sh * 100)}%</span><div class="tr"><i style="width:${x.sh / maxSh * 100}%"></i></div></div>`).join('')}</div></div>`;
}

function blocoRecursos(lista, ponto) {
  const set = new Set(lista);
  const pts = X.pontos.filter(p => set.has(p.m)).sort((a, b) => (b.mar - a.mar) || ((b.v || 0) - (a.v || 0)));
  const marav = pts.filter(p => p.mar);
  const outros = pts.filter(p => !p.mar).slice(0, 14);
  const agro = MU.agro ? lista.length === 1 ? (MU.agro.top[lista[0]] || []) : null : null;
  let h = '';
  if (marav.length) h += `<div class="sec"><h3>Maravilhas</h3><div class="chips">${marav.map(p => `<span class="chip marav" title="${esc(p.regra || '')}">${p.ic} ${esc(p.n)}</span>`).join('')}</div></div>`;
  if (agro && agro.length) h += `<div class="sec"><h3>Colheita <small>valor da produção ${esc(MU.agro.ano)}</small></h3><div class="kv">${agro.map(([p, v, ic]) => `<span>${ic || ''} ${esc(p)}</span><span>${fmt(v, 'brl')}</span>`).join('')}</div></div>`;
  const cfem = lista.length === 1 && MU.col.cfem && ok(MU.col.cfem[lista[0]]) && MU.col.cfem[lista[0]] > 0 ? `<span>⛏ Mineração (CFEM)${MU.subst && MU.subst[lista[0]] ? ' · ' + esc(MU.subst[lista[0]]) : ''}</span><span>${fmt(MU.col.cfem[lista[0]], 'brl')}</span>` : '';
  if (outros.length || cfem) h += `<div class="sec"><h3>Recursos</h3><div class="kv">${cfem}${outros.map(p => `<span${ponto && p === ponto ? ' style="color:var(--latao)"' : ''}>${p.ic} ${esc(p.n)}</span><span>${ok(p.v) ? esc(p.vt || fmt(p.v, p.f || 'c')) : ''}</span>`).join('')}</div></div>`;
  return h;
}

function abrirMun(i, voar = true, ponto = null) {
  E.sel = { tipo: 'mun', i };
  const uf = MU.ufs[MU.uf[i]];
  const g = k => MU.col[k] ? MU.col[k][i] : NaN;
  const pop = g('pop'), area = g('area');
  $('#painel-cab').innerHTML = `<div class="eyebrow">${MU.capital[i] ? '★ Capital · ' : ''}Município · <button class="link-uf" data-uf="${MU.uf[i]}" style="background:none;border:0;padding:0;color:#9cc0ea;cursor:pointer;text-decoration:underline;font:inherit;letter-spacing:inherit;text-transform:inherit">${esc(uf.nome)}</button></div>
    <h2>${esc(MU.nome[i])}</h2>
    <div class="linha1"><b>${fmt(pop, 'int')}</b> habitantes · ${fmt(area, 'km2')} · ${fmt(pop / area, 'dens')}</div>
    <button class="bt-ic" id="fechar" title="Fechar">✕</button>`;
  const emp = MU.empregos ? empregosDe([i]) : null;
  $('#painel-corpo').innerHTML = `<div class="sec"><h3>Rendimentos <small>posição entre ${NF.format(MU.n)} municípios</small></h3>${caixaRend(g, 'mun', i)}</div>
    ${blocoRecursos([i], ponto)}
    ${blocoTrabalho(emp, MU.nome[i])}
    ${blocoIndicadores(g)}
    ${blocoFe(g)}
    ${blocoSolo(g)}
    <div class="sec"><h3>Economia <small>PIB ${esc(MU.meta.ano_pib || '')}</small></h3><div class="kv">
      <span>PIB por habitante</span><span>${fmt(g('pib') / pop, 'brl0')}${comparar(g('pib') / pop, MU.br.pib / MU.br.pop, 'brl0')}</span>
      ${['va_agro', 'va_ind', 'va_serv', 'va_adm'].map((k, n) => `<span>${['Agropecuária', 'Indústria', 'Serviços', 'Administração pública'][n]}</span><span>${ok(g(k)) && g('pib') ? NF1.format(g(k) / (g('va_agro') + g('va_ind') + g('va_serv') + g('va_adm')) * 100) + '%' : '–'}</span>`).join('')}
    </div></div>
    <div class="nota">Código IBGE ${MU.cod[i]}. Fontes no Almanaque.</div>`;
  ligarPainel();
  if (voar) {
    const rel = Math.max(E.s, E.sFit * 5), movel = window.innerWidth < 760;
    irPara(MU.x[i] + (movel ? 0 : 200 / rel), MU.y[i] - (movel ? $('#painel').offsetHeight / 2 / rel : 0), rel);
  }
  sujar();
}

function abrirUF(u, voar = true) {
  E.sel = { tipo: 'uf', i: u };
  const uf = MU.ufs[u];
  const a = MU.ufAgg[u];
  const g = k => a[k];
  const muns = [...Array(MU.n).keys()].filter(i => MU.uf[i] === u);
  const maiores = muns.filter(i => ok(MU.col.pop[i])).sort((x, y) => MU.col.pop[y] - MU.col.pop[x]).slice(0, 8);
  $('#painel-cab').innerHTML = `<div class="eyebrow">Estado · ${esc(uf.regiao)} · ${esc(uf.sigla)}</div><h2>${esc(uf.nome)}</h2>
    <div class="linha1"><b>${fmt(g('pop'), 'int')}</b> habitantes · ${NF.format(muns.length)} municípios · ${fmt(g('area'), 'km2')}</div>
    <button class="bt-ic" id="fechar" title="Fechar">✕</button>`;
  $('#painel-corpo').innerHTML = `<div class="sec"><h3>Rendimentos <small>posição entre 27 unidades</small></h3>${caixaRend(g, 'uf', u)}</div>
    ${blocoRecursos(muns)}
    ${blocoTrabalho(MU.empregos ? empregosDe(muns) : null, uf.nome)}
    ${blocoIndicadores(g)}
    ${blocoFe(g)}
    ${blocoSolo(g)}
    <div class="sec"><h3>Maiores cidades</h3><div class="lista-cid">${maiores.map(i => `<button data-mun="${i}"><span>${MU.capital[i] ? '★ ' : ''}${esc(MU.nome[i])}</span><small>${fmt(MU.col.pop[i], 'int')}</small></button>`).join('')}</div></div>`;
  ligarPainel();
  if (voar) {
    let b = [1e9, 1e9, -1e9, -1e9];
    for (let k = 0; k < N; k++) if (M.terra[k] && UFH[k] === u) { b[0] = Math.min(b[0], HX[k]); b[1] = Math.min(b[1], HY[k]); b[2] = Math.max(b[2], HX[k]); b[3] = Math.max(b[3], HY[k]); }
    enquadrar(b[0], b[1], b[2], b[3], true, 0.25);
  }
  sujar();
}

function ligarPainel() {
  const p = $('#painel'); p.hidden = false;
  $('#fechar').onclick = fecharPainel;
  $$('[data-uf]', p).forEach(b => b.onclick = () => abrirUF(+b.dataset.uf));
  $$('[data-mun]', p).forEach(b => b.onclick = () => abrirMun(+b.dataset.mun));
  $('#painel-corpo').scrollTop = 0;
}
function fecharPainel() { $('#painel').hidden = true; E.sel = null; sujar(); }

/* ---------- UI ---------- */
function montarUI() {
  // barra de rendimentos do Brasil
  const br = MU.br;
  const itens = [
    { ic: '👥', v: fmt(br.pop, 'c'), t: 'População (Censo 2022)', l: 'populacao' },
    ...RENDIMENTOS.filter(r => MU.col[r.k]).map(r => ({ ic: r.ic, v: fmt(br[r.k], r.fmt), t: `${r.nome}: ${r.dica || ''}`, l: r.lente })),
  ];
  $('#rend').innerHTML = itens.map(x => `<button class="rd" data-l="${x.l || ''}" title="${esc(x.t)}"><span class="ic">${x.ic}</span>${esc(x.v)}</button>`).join('');
  $$('#rend .rd').forEach(b => b.onclick = () => { if (b.dataset.l) usarLente(b.dataset.l); });
  // lentes rápidas
  const disp = LENTES.filter(lenteDisponivel);
  const rap = RAPIDAS.map(id => disp.find(l => l.id === id)).filter(Boolean);
  $('#lentes').innerHTML = `<button class="ln" id="bt-rec" aria-pressed="true" title="Recursos (R)">💎<span class="tx">Recursos</span></button>` +
    rap.map(l => `<button class="ln" data-id="${l.id}" aria-pressed="false" title="${esc(l.sub)}">${l.ic}<span class="tx">${esc(l.nome)}</span></button>`).join('') +
    `<button class="ln" id="bt-todas" aria-expanded="false">☰<span class="tx">Lentes</span></button>`;
  $$('#lentes .ln[data-id]').forEach(b => b.onclick = () => usarLente(b.dataset.id));
  $('#bt-rec').onclick = () => { E.recursos = !E.recursos; $('#bt-rec').setAttribute('aria-pressed', String(E.recursos)); sujar(); };
  const grupos = [...new Set(disp.map(l => l.grupo))];
  $('#todas-lentes').innerHTML = grupos.map(g => `<h4>${esc(g)}</h4><div class="grade">${disp.filter(l => l.grupo === g).map(l => `<button data-id="${l.id}">${l.ic} ${esc(l.nome)}</button>`).join('')}</div>`).join('');
  $$('#todas-lentes button').forEach(b => b.onclick = () => { usarLente(b.dataset.id); $('#todas-lentes').hidden = true; });
  $('#bt-todas').onclick = () => { const t = $('#todas-lentes'); t.hidden = !t.hidden; $('#bt-todas').setAttribute('aria-expanded', String(!t.hidden)); };
  $('#marca').onclick = () => { fecharPainel(); enquadrarBrasil(true); };
  // modais
  $$('.modal').forEach(m => { m.addEventListener('click', ev => { if (ev.target === m || ev.target.closest('.fecha')) m.hidden = true; }); });
  $('#bt-ajuda').onclick = () => { $('#m-ajuda').hidden = false; };
  $('#bt-almanaque').onclick = abrirAlmanaque;
  $('#bt-conselho').onclick = () => abrirConselho();
  montarBusca();
  montarInteracao();
  montarMini();
}

/* ---------- busca ---------- */
function montarBusca() {
  const inp = $('#busca'), res = $('#busca-res');
  const base = [
    ...MU.ufs.map((u, i) => ({ t: 'uf', i, n: u.nome, s: sem(u.nome + ' ' + u.sigla), sub: 'Estado', peso: 1e9 })),
    ...MU.nome.map((n, i) => ({ t: 'mun', i, n, s: sem(n), sub: MU.ufs[MU.uf[i]].sigla, peso: MU.col.pop[i] || 0 })),
  ];
  let ativos = [], sel = 0;
  const abrir = x => { res.hidden = true; inp.value = ''; inp.blur(); x.t === 'uf' ? abrirUF(x.i) : abrirMun(x.i); };
  const mostra = () => {
    const q = sem(inp.value.trim());
    if (!q) { res.hidden = true; return; }
    ativos = base.filter(x => x.s.includes(q)).sort((a, b) => (b.s.startsWith(q) - a.s.startsWith(q)) || (b.peso - a.peso)).slice(0, 8);
    sel = 0;
    res.innerHTML = ativos.length ? ativos.map((x, k) => `<button data-k="${k}" class="${k === sel ? 'ativo' : ''}"><span>${esc(x.n)}</span><small>${esc(x.sub)}${x.t === 'mun' ? ' · ' + compacto(x.peso) : ''}</small></button>`).join('') : '<div style="padding:10px;color:var(--texto-2)">Nada encontrado</div>';
    res.hidden = false;
    $$('button', res).forEach(b => b.onclick = () => abrir(ativos[+b.dataset.k]));
  };
  inp.addEventListener('input', mostra);
  inp.addEventListener('keydown', ev => {
    if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') { ev.preventDefault(); sel = (sel + (ev.key === 'ArrowDown' ? 1 : -1) + ativos.length) % Math.max(1, ativos.length); $$('button', res).forEach((b, k) => b.classList.toggle('ativo', k === sel)); }
    if (ev.key === 'Enter' && ativos[sel]) abrir(ativos[sel]);
  });
  inp.addEventListener('blur', () => setTimeout(() => { res.hidden = true; }, 180));
}

/* ---------- conselho e explorador ---------- */
function abrirConselho(aba) {
  const m = $('#m-conselho'); m.hidden = false;
  const cons = X.conselheiros || [];
  const abas = [...cons.map(c => ({ id: c.id, nome: c.nome, ic: c.ic })), { id: 'explorador', nome: 'Explorador', ic: '🧭' }];
  const atual = aba || E.abaConselho || abas[0].id;
  E.abaConselho = atual;
  $('#abas-conselho').innerHTML = abas.map(a => `<button class="aba" role="tab" aria-selected="${a.id === atual}" data-a="${a.id}">${a.ic} ${esc(a.nome)}</button>`).join('');
  $$('#abas-conselho .aba').forEach(b => b.onclick = () => abrirConselho(b.dataset.a));
  const corpo = $('#corpo-conselho');
  if (atual === 'explorador') { montarExplorador(corpo); return; }
  const c = cons.find(x => x.id === atual);
  corpo.innerHTML = `<div class="conselho"><h3>${c.ic} ${esc(c.titulo || c.nome)}</h3><div class="papel">${esc(c.papel)}</div><ul>${c.itens.map((it, k) => `<li>${esc(it.t)}${it.m != null || it.uf != null || it.lente ? ` <button class="ir" data-k="${k}">ver no mapa</button>` : ''}</li>`).join('')}</ul></div>`;
  $$('.ir', corpo).forEach(b => b.onclick = () => {
    const it = c.itens[+b.dataset.k]; m.hidden = true;
    if (it.lente) usarLente(it.lente);
    if (it.m != null) abrirMun(it.m); else if (it.uf != null) abrirUF(it.uf);
  });
}

function montarExplorador(corpo) {
  const cols = MU.colunas.filter(c => MU.col[c.k] && MU.col[c.k].some(ok));
  const opt = sel => cols.map(c => `<option value="${c.k}" ${c.k === sel ? 'selected' : ''}>${esc(c.nome)}</option>`).join('');
  const ex = E.exp || (E.exp = { x: cols.find(c => c.k === 'superior') ? 'superior' : cols[0].k, y: cols.find(c => c.k === 'renda') ? 'renda' : cols[1].k, ord: 'y', desc: true, uf: -1 });
  corpo.innerHTML = `<div id="exp-ctrl">
      <label>Eixo X <select id="exp-x">${opt(ex.x)}</select></label>
      <label>Eixo Y <select id="exp-y">${opt(ex.y)}</select></label>
      <label>Estado <select id="exp-uf"><option value="-1">Brasil</option>${MU.ufs.map((u, i) => `<option value="${i}" ${i === ex.uf ? 'selected' : ''}>${esc(u.sigla)}</option>`).join('')}</select></label>
      <button class="aba" id="exp-lente">Pintar o mapa com Y</button>
    </div>
    <canvas id="exp-grafico"></canvas>
    <div class="nota" id="exp-nota"></div>
    <div class="tabela-wrap"><table><thead><tr><th data-o="nome">Município</th><th>UF</th><th data-o="pop">População</th><th data-o="x" id="th-x"></th><th data-o="y" id="th-y"></th></tr></thead><tbody id="exp-corpo"></tbody></table></div>`;
  const atualizar = () => {
    ex.x = $('#exp-x').value; ex.y = $('#exp-y').value; ex.uf = +$('#exp-uf').value;
    desenharExplorador();
  };
  ['#exp-x', '#exp-y', '#exp-uf'].forEach(s => $(s).onchange = atualizar);
  $('#exp-lente').onclick = () => {
    const c = MU.colunas.find(k => k.k === ex.y);
    const L = { id: 'col-' + c.k, nome: c.nome, ic: '🧭', grupo: 'Explorador', modo: c.tipo === 'soma' ? 'densidade' : 'media', num: c.k, col: c.k, peso: c.peso, paleta: 'azul', escala: c.tipo === 'soma' ? 'log' : 'quantil', fmt: c.tipo === 'soma' ? 'c' : c.fmt, sub: (c.tipo === 'soma' ? 'Por km²: ' : '') + (c.desc || c.nome) };
    E.lenteCustom = L; $('#m-conselho').hidden = true; usarLente(L.id);
  };
  $$('th[data-o]', corpo).forEach(th => th.onclick = () => { const o = th.dataset.o; ex.desc = ex.ord === o ? !ex.desc : true; ex.ord = o; desenharExplorador(); });
  desenharExplorador();
}

function desenharExplorador() {
  const ex = E.exp;
  const cx = MU.colunas.find(c => c.k === ex.x), cy = MU.colunas.find(c => c.k === ex.y);
  const vx = MU.col[ex.x], vy = MU.col[ex.y], pop = MU.col.pop;
  const ids = [...Array(MU.n).keys()].filter(i => ok(vx[i]) && ok(vy[i]) && (ex.uf < 0 || MU.uf[i] === ex.uf));
  $('#th-x').textContent = cx.nome; $('#th-y').textContent = cy.nome;
  const c = $('#exp-grafico'); const dpr = Math.min(2, devicePixelRatio || 1);
  const W = c.clientWidth, H = c.clientHeight; c.width = W * dpr; c.height = H * dpr;
  const g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
  const logx = cx.tipo === 'soma', logy = cy.tipo === 'soma';
  const tx = v => logx ? Math.log10(Math.max(v, 1e-3)) : v, ty = v => logy ? Math.log10(Math.max(v, 1e-3)) : v;
  const xs = ids.map(i => tx(vx[i])).sort((a, b) => a - b), ys = ids.map(i => ty(vy[i])).sort((a, b) => a - b);
  const q = (a, p) => a[Math.max(0, Math.min(a.length - 1, Math.floor(a.length * p)))];
  const x0 = q(xs, 0.005), x1 = q(xs, 0.995), y0 = q(ys, 0.005), y1 = q(ys, 0.995);
  const ml = 64, mr = 16, mt = 12, mb = 36;
  const px = v => ml + (tx(v) - x0) / ((x1 - x0) || 1) * (W - ml - mr);
  const py = v => H - mb - (ty(v) - y0) / ((y1 - y0) || 1) * (H - mt - mb);
  g.strokeStyle = '#2c4552'; g.fillStyle = '#a9b3ad'; g.font = '11px "IBM Plex Mono", monospace'; g.lineWidth = 1;
  for (let k = 0; k <= 4; k++) {
    const fx = x0 + (x1 - x0) * k / 4, fy = y0 + (y1 - y0) * k / 4;
    const X_ = ml + (W - ml - mr) * k / 4, Y_ = H - mb - (H - mt - mb) * k / 4;
    g.beginPath(); g.moveTo(X_, mt); g.lineTo(X_, H - mb); g.stroke();
    g.beginPath(); g.moveTo(ml, Y_); g.lineTo(W - mr, Y_); g.stroke();
    g.textAlign = 'center'; g.fillText(fmt(logx ? Math.pow(10, fx) : fx, cx.fmt), X_, H - mb + 16);
    g.textAlign = 'right'; g.fillText(fmt(logy ? Math.pow(10, fy) : fy, cy.fmt), ml - 6, Y_ + 4);
  }
  g.textAlign = 'center'; g.fillStyle = '#e9e1cc'; g.fillText(cx.nome + (logx ? ' (log)' : ''), ml + (W - ml - mr) / 2, H - 6);
  const pts = [];
  const ord = ids.slice().sort((a, b) => (pop[b] || 0) - (pop[a] || 0));
  for (const i of ord.reverse()) {
    const X_ = px(vx[i]), Y_ = py(vy[i]);
    if (X_ < ml - 4 || X_ > W - mr + 4 || Y_ < mt - 4 || Y_ > H - mb + 4) continue;
    const r = Math.max(1.5, Math.min(9, Math.sqrt((pop[i] || 0) / 9000)));
    g.beginPath(); g.arc(X_, Y_, r, 0, Math.PI * 2);
    g.fillStyle = (COR_REGIAO[MU.ufs[MU.uf[i]].regiao] || '#888') + 'aa'; g.fill();
    pts.push([X_, Y_, r, i]);
  }
  // correlação de postos
  const corr = spearman(ids.map(i => vx[i]), ids.map(i => vy[i]));
  $('#exp-nota').innerHTML = `${NF.format(ids.length)} municípios. Correlação de postos (Spearman): <b>${NF2.format(corr)}</b>. Tamanho do ponto = população; cor = região (${Object.entries(COR_REGIAO).map(([r, c]) => `<span style="color:${c}">${r}</span>`).join(', ')}). Clique num ponto para abrir o município.`;
  c.onmousemove = ev => {
    const r = c.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
    let best = null, bd = 1e9;
    for (const p of pts) { const d = Math.hypot(p[0] - mx, p[1] - my) - p[2]; if (d < bd) { bd = d; best = p; } }
    c.title = best && bd < 6 ? `${MU.nome[best[3]]} (${MU.ufs[MU.uf[best[3]]].sigla}): ${fmt(vx[best[3]], cx.fmt)} · ${fmt(vy[best[3]], cy.fmt)}` : '';
    c.style.cursor = best && bd < 6 ? 'pointer' : 'default';
    c._best = best && bd < 6 ? best[3] : null;
  };
  c.onclick = () => { if (c._best != null) { $('#m-conselho').hidden = true; abrirMun(c._best); } };
  // tabela
  const chaveOrd = { nome: i => MU.nome[i], pop: i => pop[i] || 0, x: i => vx[i], y: i => vy[i] }[ex.ord] || (i => vy[i]);
  const tab = ids.slice().sort((a, b) => { const A = chaveOrd(a), B = chaveOrd(b); return (A < B ? -1 : A > B ? 1 : 0) * (ex.desc ? -1 : 1); }).slice(0, 60);
  $('#exp-corpo').innerHTML = tab.map(i => `<tr data-mun="${i}"><td>${esc(MU.nome[i])}</td><td>${esc(MU.ufs[MU.uf[i]].sigla)}</td><td class="n">${fmt(pop[i], 'int')}</td><td class="n">${fmt(vx[i], cx.fmt)}</td><td class="n">${fmt(vy[i], cy.fmt)}</td></tr>`).join('');
  $$('#exp-corpo tr').forEach(tr => tr.onclick = () => { $('#m-conselho').hidden = true; abrirMun(+tr.dataset.mun); });
}
function spearman(a, b) {
  const rk = v => { const o = v.map((x, i) => [x, i]).sort((p, q) => p[0] - q[0]); const r = new Array(v.length); o.forEach((p, k) => { r[p[1]] = k; }); return r; };
  const ra = rk(a), rb = rk(b), n = a.length; if (n < 3) return NaN;
  const m = (n - 1) / 2; let sab = 0, saa = 0, sbb = 0;
  for (let i = 0; i < n; i++) { const x = ra[i] - m, y = rb[i] - m; sab += x * y; saa += x * x; sbb += y * y; }
  return sab / Math.sqrt(saa * sbb);
}

/* ---------- almanaque ---------- */
function abrirAlmanaque() {
  $('#m-almanaque').hidden = false;
  const f = X.fontes || [];
  $('#corpo-almanaque').innerHTML = `<div class="conselho" style="max-width:none">
    <p>Cada hexágono tem 25 km entre lados opostos, numa projeção de áreas iguais. Os valores de cada município são repartidos entre os hexágonos pela área que ele ocupa em cada um; taxas (como alfabetização) viram médias ponderadas pela população. Pontos (usinas, portos, parques) ficam no hexágono onde estão.</p>
    <h3 style="font-size:18px;margin-top:16px">Regras das Maravilhas</h3>
    <ul class="regras">${(X.regras || []).map(r => `<li>${esc(r)}</li>`).join('')}</ul>
    <h3 style="font-size:18px;margin-top:16px">Fontes</h3>
    <div class="fontes">${f.map(x => `<div class="fonte"><b>${esc(x.nome)}</b>${esc(x.org)}${x.ano ? ' · ' + esc(x.ano) : ''}<br><small>${esc(x.uso || '')}</small>${x.url ? `<br><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.url.replace(/^https?:\/\//, '').slice(0, 70))}</a>` : ''}</div>`).join('')}</div>
    <p class="nota">Ideia inspirada no mapa dos Estados Unidos que Andrej Karpathy montou com dados públicos. Este é outro projeto, feito do zero para o Brasil.</p>
  </div>`;
}

carregar().catch(err => { $('#carregando .s').textContent = 'Não consegui carregar os dados: ' + err.message; console.error(err); });
