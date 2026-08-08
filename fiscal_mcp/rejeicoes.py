"""Tradução dos códigos de rejeição da SEFAZ.

"Rejeicao 539" não diz a ninguém o que fazer — e quem lê aqui é um agente, que
vai tentar de novo. Sem o campo `acao`, ele reemite e duplica nota fiscal.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from .regras import RAIZ_REGRAS

ARQUIVO = RAIZ_REGRAS / "rejeicoes.yaml"


@lru_cache(maxsize=1)
def catalogo() -> dict[str, dict]:
    dados = yaml.safe_load(ARQUIVO.read_text(encoding="utf-8")) or {}
    return {str(k): v for k, v in (dados.get("rejeicoes") or {}).items()}


def extrai_codigo(texto: str) -> str | None:
    """Acha o código na mensagem da SEFAZ.

    Aceita '539', 'Rejeicao: 539', '539 - Duplicidade...' e afins — a mensagem
    chega em formatos diferentes conforme a UF e o cliente.
    """
    if not texto:
        return None
    limpo = texto.strip()
    if limpo.isdigit():
        return limpo
    achado = re.search(r"\b(\d{3})\b", limpo)
    return achado.group(1) if achado else None


def explica(codigo_ou_mensagem: str) -> dict:
    """Traduz um código ou mensagem de rejeição. Nunca levanta exceção."""
    codigo = extrai_codigo(codigo_ou_mensagem)
    if codigo is None:
        return {
            "ok": False,
            "erro": "não identifiquei um código de rejeição no texto informado",
            "acao": "Informe o código de três dígitos, ex.: 539.",
        }

    entrada = catalogo().get(codigo)
    if entrada is None:
        return {
            "ok": False,
            "codigo": codigo,
            "erro": f"o código {codigo} não está no catálogo",
            "acao": (
                "Consulte o Manual de Orientação do Contribuinte no Portal da NF-e "
                "para o significado. Se este código aparecer com frequência, vale "
                "abrir uma issue para ele entrar no catálogo."
            ),
            "catalogo_cobre": len(catalogo()),
        }

    return {
        "ok": True,
        "codigo": codigo,
        "significa": entrada["significa"].strip(),
        "acao": entrada["acao"].strip(),
        "reversivel": entrada.get("reversivel", True),
    }


def listar() -> list[dict]:
    return [
        {"codigo": c, "significa": e["significa"].strip(), "reversivel": e.get("reversivel", True)}
        for c, e in sorted(catalogo().items())
    ]
