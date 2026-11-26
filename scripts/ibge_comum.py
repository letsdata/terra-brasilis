"""Funções comuns aos scripts ibge_*.py: download com cache e novas tentativas.

Tudo o que é baixado fica em dados/brutos/ibge/ para a execução ser reproduzível
(apague o arquivo bruto para forçar novo download).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
BRUTOS = DADOS / "brutos" / "ibge"
BRUTOS.mkdir(parents=True, exist_ok=True)

SESSAO = requests.Session()
SESSAO.headers["User-Agent"] = "terra-brasilis-dados/1.0"


def baixar(url: str, destino: Path, tentativas: int = 4, timeout: int = 300) -> Path:
    """Baixa url para destino (se ainda não existir). Levanta erro após as tentativas."""
    destino = Path(destino)
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    erro = None
    for i in range(tentativas):
        try:
            r = SESSAO.get(url, timeout=timeout)
            r.raise_for_status()
            tmp = destino.with_suffix(destino.suffix + ".part")
            tmp.write_bytes(r.content)
            tmp.rename(destino)
            return destino
        except Exception as e:  # noqa: BLE001
            erro = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"falha ao baixar {url}: {erro}")


def sidra(caminho: str, destino: Path) -> list[dict]:
    """Consulta a API SIDRA (apisidra.ibge.gov.br/values/...) e devolve as linhas
    (sem a linha de cabeçalho). A resposta bruta é guardada em destino."""
    url = f"https://apisidra.ibge.gov.br/values/{caminho.strip('/')}?formato=json"
    baixar(url, destino)
    dados = json.loads(Path(destino).read_text(encoding="utf-8"))
    if not isinstance(dados, list) or not dados:
        raise RuntimeError(f"resposta inesperada da SIDRA para {url}")
    return dados[1:]


def numero(v: str):
    """Converte o campo V da SIDRA. '-' (zero absoluto), '..', '...', 'X' -> None."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
