"""Biomas do Brasil 1:250.000 (IBGE, 2019) simplificados para GeoJSON leve.

Gera dados/brutos/ibge/biomas.geojson (propriedades: bioma, cod_bioma), abaixo de ~5 MB.

Executar: .venv/bin/python scripts/ibge_biomas.py
"""
from __future__ import annotations

import json
import zipfile

import shapefile  # pyshp
from shapely.geometry import mapping, shape
from shapely.validation import make_valid

from ibge_comum import BRUTOS, baixar

URL = ("https://geoftp.ibge.gov.br/informacoes_ambientais/estudos_ambientais/biomas/"
       "vetores/Biomas_250mil.zip")
LIMITE = 5_000_000


def arredonda(obj, casas=4):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(obj[0], casas), round(obj[1], casas)]
        return [arredonda(o, casas) for o in obj]
    return obj


def main():
    pasta = BRUTOS / "biomas" / "vetores"
    z = baixar(URL, pasta / "Biomas_250mil.zip")
    shp = pasta / "lm_bioma_250.shp"
    if not shp.exists():
        zipfile.ZipFile(z).extractall(pasta)
    r = shapefile.Reader(str(shp), encoding="utf-8")
    print([f[0] for f in r.fields[1:]])
    feicoes = []
    for sr in r.iterShapeRecords():
        d = sr.record.as_dict()
        g = shape(sr.shape.__geo_interface__)
        g = make_valid(g) if not g.is_valid else g
        feicoes.append((d, g))

    for tol in (0.002, 0.005, 0.01, 0.02, 0.03):
        feats = []
        for d, g in feicoes:
            s = g.simplify(tol, preserve_topology=True)
            geo = mapping(s)
            geo = {"type": geo["type"], "coordinates": arredonda(geo["coordinates"])}
            feats.append({"type": "Feature",
                          "properties": {"bioma": d.get("Bioma"), "cod_bioma": d.get("CD_Bioma")},
                          "geometry": geo})
        texto = json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False,
                           separators=(",", ":"))
        if len(texto.encode()) <= LIMITE:
            break
    (BRUTOS / "biomas.geojson").write_text(texto, encoding="utf-8")
    print(f"biomas.geojson: {len(feats)} feições, tolerância {tol} grau, {len(texto.encode())/1e6:.2f} MB")


if __name__ == "__main__":
    main()
