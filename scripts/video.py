"""Grava o vídeo vertical (1080x1920, 30 qps) do Terra Brasilis direto da página, quadro a
quadro: o relógio da página (performance.now e requestAnimationFrame) é controlado pelo script,
então zooms e trocas de lente saem lisos mesmo que cada captura demore.

Uso:
  python3 -m http.server 8768 --directory web &
  .venv/bin/python scripts/video.py pt  /caminho/quadros-pt  divulgacao/terra-brasilis-pt.mp4
  .venv/bin/python scripts/video.py en  /caminho/quadros-en  divulgacao/terra-brasilis-en.mp4
"""
import subprocess, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://localhost:8768/"
QPS = 30
W, H = 540, 960  # pontos CSS; dpr 2 => 1080x1920

TEXTOS = {
    "pt": ["Cópia descarada? 😅<em>Nada disso: homenagem ao mestre dos mestres, Andrej Karpathy, que fez o mapa dos EUA 🙇</em>",
           "Transformei o Brasil num jogo de estratégia 🇧🇷",
           "Cada hexágono é dado real: IBGE, MapBiomas, ANEEL",
           "30 lentes de dados",
           "A floresta que sumiu desde 1985",
           "Procure a sua cidade",
           "O Brasil tem mais boi do que gente 🐄",
           "Terra Brasilis<br><span>letsdata.github.io/terra-brasilis</span>"],
    "en": ["Shameless copy? 😅<em>Nah, a tribute to the master of masters, @karpathy, who did the US one 🙇</em>",
           "I turned Brazil into a strategy game 🇧🇷",
           "Every hex is real data: census, land cover, power plants",
           "30 data lenses",
           "Forest lost since 1985",
           "Find your city",
           "Brazil has more cattle than people 🐄",
           "Terra Brasilis<br><span>letsdata.github.io/terra-brasilis</span>"],
}

RELOGIO = """
(() => {
  let t = 0; let q = [];
  performance.now = () => t;
  window.requestAnimationFrame = cb => { q.push(cb); return q.length; };
  window.cancelAnimationFrame = () => {};
  window.__passo = ms => { t += ms; const cbs = q; q = []; cbs.forEach(cb => cb(t)); };
})();
"""

AJUDA = """
(() => {
  const st = document.createElement('style');
  st.textContent = `*{transition:none!important;animation:none!important}
  #cap{position:fixed;left:50px;right:50px;top:100px;z-index:99999;text-align:center;
    font:700 29px/1.18 'Source Sans 3',sans-serif;color:#fff;letter-spacing:.2px;
    background:rgba(6,18,26,.86);border:1.5px solid rgba(214,172,82,.75);border-radius:14px;
    padding:14px 18px;box-shadow:0 6px 24px rgba(0,0,0,.45);opacity:0}
  #cap em{display:block;margin-top:8px;font:600 22px/1.25 'Source Sans 3',sans-serif;font-style:normal;color:#e9c46a}
  #cap span{display:block;margin-top:6px;font:600 17px/1.2 'IBM Plex Mono',monospace;color:#e9c46a}`;
  document.head.appendChild(st);
  const d = document.createElement('div'); d.id = 'cap'; document.body.appendChild(d);
  window.__cap = (html, a) => { if (d.innerHTML !== html) d.innerHTML = html; d.style.opacity = a; };
  // Caixa do mundo -> câmera que cabe na região [L,T,R,B] da tela.
  window.__cam = (minx, miny, maxx, maxy, L, T, R, B) => {
    const s = Math.min((R - L) / (maxx - minx), (B - T) / (maxy - miny));
    const wx = (minx + maxx) / 2, wy = (miny + maxy) / 2, sx = (L + R) / 2, sy = (T + B) / 2;
    return { cx: wx - (sx - E.W / 2) / s, cy: wy + (sy - E.H / 2) / s, s };
  };
  window.__voar = (c, d) => { E.anim = { t0: performance.now(), d, a: { cx: E.cx, cy: E.cy, s: E.s }, b: c }; sujar(); };
  window.__ja = c => { E.cx = c.cx; E.cy = c.cy; E.s = c.s; E.anim = null; sujar(); };
  window.__mun = (nome, uf) => MU.nome.findIndex((n, i) => n === nome && MU.ufs[MU.uf[i]].sigla === uf);
  window.__caixaMun = (lista, pad) => {
    const xs = lista.map(i => MU.x[i]), ys = lista.map(i => MU.y[i]);
    return [Math.min(...xs) - pad, Math.min(...ys) - pad, Math.max(...xs) + pad, Math.max(...ys) + pad];
  };
})();
"""

# Região livre do mapa (abaixo da legenda do vídeo, acima da legenda da lente).
REG = (10, 205, W - 100, H - 195)  # 100 pt à direita para as faixas das cidades do litoral


def main():
    lang, pasta, saida = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    teste = len(sys.argv) > 4  # só um quadro a cada 2 s, sem montar o vídeo
    pasta.mkdir(parents=True, exist_ok=True)
    txt = TEXTOS[lang]
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome", headless=True)
        pg = nav.new_page(viewport={"width": W, "height": H}, device_scale_factor=2,
                          is_mobile=True, has_touch=True)
        pg.add_init_script(RELOGIO)
        pg.goto(URL)
        for _ in range(400):
            pg.evaluate("__passo(16)")
            if pg.evaluate("typeof E !== 'undefined' && E.sFit > 0 && typeof MU !== 'undefined' && !!MU.nome"):
                break
            time.sleep(0.05)
        pg.evaluate("document.fonts.ready")
        pg.evaluate(AJUDA)
        cam = lambda caixa, reg=REG: pg.evaluate(f"__cam({','.join(map(str, caixa))},{','.join(map(str, reg))})")
        bbox = pg.evaluate("M.bbox")
        brasil = cam(bbox)
        pg.evaluate("c => __ja(c)", {**brasil, "s": brasil["s"] * 0.94})
        sp = pg.evaluate("__mun('São Paulo','SP')")
        sp_cam = pg.evaluate(f"(() => {{ const b = __caixaMun([{sp}], 260); return __cam(b[0],b[1],b[2],b[3],{','.join(map(str, REG))}); }})()")
        arco = pg.evaluate("""(() => { const l = [['Porto Velho','RO'],['Sinop','MT'],['Marabá','PA'],['Altamira','PA'],['Lábrea','AM']].map(([n,u]) => __mun(n,u));
            const b = __caixaMun(l, 120); return __cam(b[0],b[1],b[2],b[3],""" + ",".join(map(str, REG)) + "); })()")
        manaus = pg.evaluate("__mun('Manaus','AM')")

        # Linha do tempo: (início, fim, texto) e ações em instantes.
        ABRE = 4.2  # abertura com a homenagem ao Karpathy
        base = [(0.3, 3.6, 0), (3.9, 8.4, 1), (8.7, 14.6, 2), (14.9, 22.6, 3), (22.9, 30.6, 4), (30.9, 36.6, 5), (36.9, 42.0, 6)]
        legendas = [(0.3, 4.0, 0)] + [(a + ABRE, b + ABRE, i + 1) for a, b, i in base]
        acoes = {
            0.0: lambda: pg.evaluate("c => __voar(c, 7800)", brasil),
            3.7: lambda: pg.evaluate("c => __voar(c, 3800)", sp_cam),
            8.6: lambda: (pg.evaluate("usarLente('renda')"), pg.evaluate("c => __voar(c, 1800)", brasil)),
            10.6: lambda: pg.evaluate("usarLente('fe')"),
            12.6: lambda: pg.evaluate("usarLente('diplomas')"),
            14.8: lambda: pg.evaluate("usarLente('perda')"),
            16.8: lambda: pg.evaluate("c => __voar(c, 4200)", arco),
            22.8: lambda: (pg.evaluate("usarLente('terreno')"), pg.evaluate(f"abrirMun({manaus})"),
                           pg.evaluate(f"""(() => {{ const i = {manaus}, s = E.anim ? E.anim.b.s : E.s;
                             const topo = innerHeight - document.querySelector('#painel').offsetHeight;
                             const y = (205 + topo) / 2;
                             __voar({{ cx: MU.x[i] - 60 / s, cy: MU.y[i] + (y - E.H / 2) / s, s }}, 1400); }})()""")),
            30.8: lambda: (pg.evaluate("(() => { const f = document.querySelector('#fechar'); if (f) f.click(); })()"),
                           pg.evaluate("abrirConselho('campo')"),
                           pg.evaluate("""(() => { const li = [...document.querySelectorAll('#corpo-conselho li')].find(l => /bois e vacas/.test(l.textContent));
                             if (li) { li.style.background = 'rgba(233,196,106,.22)'; li.style.borderRadius = '8px'; li.style.padding = '6px 8px';
                               li.style.outline = '1.5px solid rgba(233,196,106,.8)'; li.scrollIntoView({ block: 'center' }); } })()""")),
            36.8: lambda: (pg.evaluate("document.querySelector('#m-conselho').hidden = true"),
                           pg.evaluate("c => __voar(c, 1600)", brasil)),
        }
        acoes = {0.0: acoes[0.0], **{t + ABRE: f for t, f in acoes.items() if t > 0}}
        total = 42.0 + ABRE
        n = int(total * QPS)
        feitas = set()
        for k in range(n):
            t = k / QPS
            for ta, f in acoes.items():
                if ta <= t and ta not in feitas:
                    feitas.add(ta); f()
            a, h = 0.0, ""
            for t0, t1, i in legendas:
                if t0 <= t <= t1:
                    h = txt[i]; a = min(1, (t - t0) / 0.25, (t1 - t) / 0.25)
            pg.evaluate("([h, a]) => __cap(h, a)", [h, max(0, a)])
            pg.evaluate(f"__passo({1000 / QPS})")
            if not teste or k % 60 == 0:
                pg.screenshot(path=str(pasta / f"{k:05d}.png"))
            if k % 150 == 0:
                print(f"{k}/{n}", flush=True)
        nav.close()
    if teste:
        return
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(QPS), "-i", str(pasta / "%05d.png"),
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(saida)], check=True)
    print("ok", saida)


if __name__ == "__main__":
    main()
