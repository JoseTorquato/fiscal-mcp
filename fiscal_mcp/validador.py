"""Ponto de entrada da validação: junta documento, regras e chave.

É esta a função que as ferramentas MCP e a CLI chamam. Mantida separada do
servidor de propósito — o núcleo precisa ser testável sem o SDK de MCP.
"""

from __future__ import annotations

from . import chave as mod_chave
from .documento import Documento, XmlInvalido
from .regras import aplica, carrega


def valida_nfe(xml: str, incluir_resumo: bool = True) -> dict:
    """Valida um XML de NF-e localmente. Não assina, não transmite, não emite."""
    try:
        doc = Documento.de_texto(xml)
    except XmlInvalido as exc:
        return {
            "ok": False,
            "erro": str(exc),
            "acao": "Confira se o conteúdo é o XML da NF-e, e não o DANFE em PDF.",
        }

    achados = [a.para_dict() for a in aplica(doc, carrega())]

    # a chave vem no atributo Id e tem verificação própria
    problemas_chave = []
    if doc.chave:
        analise = mod_chave.analisa(doc.chave)
        problemas_chave = analise.get("problemas", [])
        for p in problemas_chave:
            achados.append({
                "id": f"chave-{p['campo']}",
                "severidade": "erro",
                "grupo": "chave-de-acesso",
                "problema": p["problema"],
                "acao": p["acao"],
            })
    else:
        achados.append({
            "id": "chave-ausente",
            "severidade": "erro",
            "grupo": "chave-de-acesso",
            "problema": "o atributo Id do infNFe não traz a chave de acesso",
            "acao": "O Id deve ser 'NFe' seguido dos 44 dígitos da chave.",
        })

    erros = [a for a in achados if a["severidade"] == "erro"]
    avisos = [a for a in achados if a["severidade"] == "aviso"]

    saida = {
        "ok": not erros,
        "erros": len(erros),
        "avisos": len(avisos),
        "achados": achados,
        "verificado_localmente": True,
        "nota": (
            "Validação local: schema mínimo, coerência de totais e chave de acesso. "
            "Não substitui a validação da SEFAZ nem o XSD oficial, e não garante "
            "autorização."
        ),
    }
    if incluir_resumo:
        saida["documento"] = doc.resumo()
    return saida


def explica_nfe(xml: str) -> dict:
    """Interpreta o XML e devolve estrutura resumida, sem julgar."""
    try:
        doc = Documento.de_texto(xml)
    except XmlInvalido as exc:
        return {"ok": False, "erro": str(exc)}
    return {"ok": True, **doc.resumo()}
