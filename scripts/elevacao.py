"""Altitude do centro de cada hexágono de terra (Open-Meteo Elevation API, modelo
Copernicus DEM GLO-90). Quando a Open-Meteo bloqueia por limite de uso (5 mil
pontos por hora), passa para a OpenTopoData (SRTM 90 m, 100 pontos por pedido, 1 por segundo). Guarda em dados/elevacao.csv; retoma de onde parou.

Uso: .venv/bin/python scripts/elevacao.py
"""
import csv, time
from pathlib import Path
import requests

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados/elevacao.csv"
URL = "https://api.open-meteo.com/v1/elevation"
URL2 = "https://api.opentopodata.org/v1/srtm90m"


def opentopo(lote):
    for tent in range(6):
        resp = requests.get(URL2, params={"locations": "|".join(f"{p[2]:.4f},{p[3]:.4f}" for p in lote)}, timeout=60)
        if resp.status_code == 429:
            time.sleep(5 * (tent + 1)); continue
        resp.raise_for_status()
        return [r["elevation"] if r["elevation"] is not None else 0 for r in resp.json()["results"]]
    raise SystemExit("OpenTopoData falhou")


def main():
    pontos = []
    with open(RAIZ / "dados/grade.csv") as fh:
        for l in csv.DictReader(fh):
            if float(l["terra"]) > 0:
                pontos.append((int(l["q"]), int(l["r"]), float(l["lat"]), float(l["lon"])))
    feitos = {}
    if SAIDA.exists():
        with open(SAIDA) as fh:
            for l in csv.DictReader(fh):
                feitos[(int(l["q"]), int(l["r"]))] = l["elev"]
    falta = [p for p in pontos if (p[0], p[1]) not in feitos]
    novo = not SAIDA.exists()
    with open(SAIDA, "a", newline="") as fh:
        w = csv.writer(fh)
        if novo:
            w.writerow(["q", "r", "elev"])
        for i in range(0, len(falta), 100):
            lote = falta[i:i + 100]
            for tent in range(6):
                try:
                    resp = requests.get(URL, params={
                        "latitude": ",".join(f"{p[2]:.4f}" for p in lote),
                        "longitude": ",".join(f"{p[3]:.4f}" for p in lote)}, timeout=60)
                    if resp.status_code == 429:
                        el = opentopo(lote); time.sleep(1.1); break
                    resp.raise_for_status()
                    el = resp.json()["elevation"]
                    break
                except requests.RequestException as e:
                    print("erro", e); time.sleep(5 * (tent + 1))
            else:
                raise SystemExit("falhou; rode de novo para retomar")
            for p, e in zip(lote, el):
                w.writerow([p[0], p[1], round(e)])
            fh.flush()
            if (i // 100) % 20 == 0:
                print(f"{i + len(lote)}/{len(falta)}", flush=True)
            time.sleep(0.4)
    print("ok")


if __name__ == "__main__":
    main()
