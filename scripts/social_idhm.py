"""IDHM 2010 por município (Atlas do Desenvolvimento Humano, PNUD/Ipea/FJP),
lido da redistribuição oficial no Ipeadata (séries ADH_IDHM, ADH_IDHM_R, ADH_IDHM_E, ADH_IDHM_L).

Uso: .venv/bin/python scripts/social_idhm.py  ->  dados/idhm.csv
"""
import json
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
BRUTOS = RAIZ / "dados" / "brutos" / "social"
SERIES = {"ADH_IDHM": "idhm", "ADH_IDHM_R": "idhm_renda",
          "ADH_IDHM_E": "idhm_educacao", "ADH_IDHM_L": "idhm_longevidade"}


def serie(cod):
    arq = BRUTOS / f"ipeadata_{cod}.json"
    if not arq.exists():
        r = requests.get(f"http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{cod}')",
                         timeout=300)
        r.raise_for_status()
        arq.write_text(r.text, encoding="utf-8")
    d = pd.DataFrame(json.loads(arq.read_text(encoding="utf-8"))["value"])
    d = d[(d.NIVNOME == "Municípios") & d.VALDATA.str.startswith("2010")]
    return d.assign(cod=d.TERCODIGO.astype(int)).set_index("cod")["VALVALOR"].rename(SERIES[cod])


out = pd.concat([serie(c) for c in SERIES], axis=1).reset_index().sort_values("cod")
out["ano"] = 2010
out.to_csv(RAIZ / "dados" / "idhm.csv", index=False)
print(out.shape)
print(out.describe().T[["count", "mean", "min", "max"]])
print(out[out.cod.isin([3550308, 3304557, 1302603])])
