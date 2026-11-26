"""Grade hexagonal do Brasil (hexágonos de 25 km entre lados opostos).

Projeção Albers de áreas iguais centrada no Brasil, em km. Hexágonos "pointy-top"
em coordenadas axiais (q, r). Saída: dados/grade.csv com a fração de terra de cada
hexágono e os hexágonos de mar até 3 anéis da costa.

Uso: .venv/bin/python scripts/grade.py
"""
import csv, json, math
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape, Polygon, Point
from shapely.ops import transform
from shapely.strtree import STRtree
from shapely.prepared import prep

RAIZ = Path(__file__).resolve().parent.parent
PROJ = "+proj=aea +lat_1=-2 +lat_2=-22 +lat_0=-12 +lon_0=-54 +datum=WGS84 +units=km +no_defs"
LADO = 25.0                      # distância entre lados opostos, km
R = LADO / math.sqrt(3)          # centro ao vértice
fwd = Transformer.from_crs("EPSG:4326", PROJ, always_xy=True)
inv = Transformer.from_crs(PROJ, "EPSG:4326", always_xy=True)


def centro(q, r):
    return R * math.sqrt(3) * (q + r / 2), R * 1.5 * r


def poligono(q, r):
    cx, cy = centro(q, r)
    return Polygon([(cx + R * math.cos(math.radians(60 * i - 30)),
                     cy + R * math.sin(math.radians(60 * i - 30))) for i in range(6)])


def axial(x, y):
    q = (math.sqrt(3) / 3 * x - y / 3) / R
    r = (2 / 3 * y) / R
    # arredondamento cúbico
    s = -q - r
    rq, rr, rs = round(q), round(r), round(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return rq, rr


VIZ = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


def main():
    g = json.load(open(RAIZ / "dados/brutos/grade/brasil.geojson"))
    br = shape(g["features"][0]["geometry"])
    brp = transform(fwd.transform, br).buffer(0)
    pp = prep(brp)
    minx, miny, maxx, maxy = brp.bounds
    q0, r0 = axial(minx, miny)
    q1, r1 = axial(maxx, maxy)
    terra = {}
    for r in range(min(r0, r1) - 2, max(r0, r1) + 3):
        for q in range(min(q0, q1) - abs(r1 - r0) - 4, max(q0, q1) + abs(r1 - r0) + 4):
            cx, cy = centro(q, r)
            if not (minx - 2 * R <= cx <= maxx + 2 * R and miny - 2 * R <= cy <= maxy + 2 * R):
                continue
            h = poligono(q, r)
            if not pp.intersects(h):
                continue
            frac = brp.intersection(h).area / h.area
            if frac > 0:
                terra[(q, r)] = frac
    # terra: >= 35% ou ilha pequena (nenhum vizinho com terra)
    celulas = {}
    for (q, r), f in terra.items():
        if f >= 0.35:
            celulas[(q, r)] = f
    for (q, r), f in terra.items():
        if (q, r) not in celulas and not any((q + a, r + b) in celulas for a, b in VIZ):
            celulas[(q, r)] = max(f, 0.35)  # ilha isolada (Noronha, Trindade...)
    # mar: até 3 anéis da costa
    mar = {}
    frente = set(celulas)
    for anel in (1, 2, 3):
        nova = set()
        for (q, r) in frente:
            for a, b in VIZ:
                k = (q + a, r + b)
                if k not in celulas and k not in mar:
                    mar[k] = anel
                    nova.add(k)
        frente = nova
    linhas = []
    for (q, r), f in celulas.items():
        x, y = centro(q, r)
        lon, lat = inv.transform(x, y)
        linhas.append((q, r, round(x, 2), round(y, 2), round(lon, 5), round(lat, 5), round(f, 3), 0))
    for (q, r), anel in mar.items():
        x, y = centro(q, r)
        lon, lat = inv.transform(x, y)
        linhas.append((q, r, round(x, 2), round(y, 2), round(lon, 5), round(lat, 5), 0, anel))
    linhas.sort(key=lambda t: (t[1], t[0]))
    with open(RAIZ / "dados/grade.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["q", "r", "x", "y", "lon", "lat", "terra", "anel_mar"])
        w.writerows(linhas)
    print(f"terra {len(celulas)}  mar {len(mar)}  R={R:.3f} km")


if __name__ == "__main__":
    main()
