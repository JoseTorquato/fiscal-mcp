"""Linha de comando — para usar sem agente nenhum.

Existe porque a primeira pergunta de quem chega é "isso funciona?", e a resposta
mais rápida é rodar num XML de verdade sem configurar cliente MCP.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, rejeicoes
from .chave import analisa as analisa_chave
from .validador import explica_nfe, valida_nfe

VERM, AMAR, CIANO, CINZA, ZERA = "\033[31m", "\033[33m", "\033[36m", "\033[90m", "\033[0m"


def _cor(texto: str, cor: str) -> str:
    return f"{cor}{texto}{ZERA}" if sys.stdout.isatty() else texto


def _mostra_validacao(r: dict) -> None:
    if "erro" in r and not r.get("achados"):
        print(_cor(f"\n  não consegui ler o arquivo: {r['erro']}", VERM))
        if r.get("acao"):
            print(_cor(f"  {r['acao']}\n", CINZA))
        return

    print()
    for a in r["achados"]:
        cor = VERM if a["severidade"] == "erro" else AMAR
        print(f"  {_cor('[' + a['severidade'] + ']', cor)} {a['id']}")
        print(f"      {a['problema']}")
        if a.get("detalhe"):
            print(_cor(f"      {a['detalhe']}", CINZA))
        if a.get("acao"):
            print(_cor(f"      → {a['acao'].strip()}", CINZA))
        print()

    veredito = "sem erros" if r["ok"] else f"{r['erros']} erro(s)"
    cor = CIANO if r["ok"] else VERM
    print(f"  {_cor(veredito, cor)}, {r['avisos']} aviso(s)")

    if doc := r.get("documento"):
        ident = doc["identificacao"]
        print(_cor(
            f"  {doc['emitente']['nome']} · nota {ident['numero']}/{ident['serie']} · "
            f"{doc['quantidade_itens']} itens · R$ {doc['totais']['nota']} · {ident['ambiente']}",
            CINZA,
        ))
    print(_cor(f"  {r['nota']}\n", CINZA))


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(
        prog="fiscal-mcp",
        description="Validação e leitura de documento fiscal — offline, sem certificado.",
    )
    p.add_argument("--version", action="version", version=f"fiscal-mcp {__version__}")
    sub = p.add_subparsers(dest="comando", required=True)

    v = sub.add_parser("validar", help="valida um XML de NF-e localmente")
    v.add_argument("arquivo", help="caminho do XML")
    v.add_argument("--json", action="store_true", help="saída em JSON")

    e = sub.add_parser("explicar", help="resume um XML de NF-e")
    e.add_argument("arquivo")

    c = sub.add_parser("chave", help="analisa uma chave de acesso")
    c.add_argument("chave")

    r = sub.add_parser("rejeicao", help="traduz um código de rejeição da SEFAZ")
    r.add_argument("codigo", nargs="?", help="código ou mensagem; sem argumento, lista o catálogo")

    args = p.parse_args(argv)

    if args.comando in ("validar", "explicar"):
        caminho = Path(args.arquivo)
        if not caminho.is_file():
            print(f"arquivo não encontrado: {caminho}", file=sys.stderr)
            return 2
        xml = caminho.read_text(encoding="utf-8", errors="replace")

        if args.comando == "explicar":
            print(json.dumps(explica_nfe(xml), ensure_ascii=False, indent=2))
            return 0

        resultado = valida_nfe(xml)
        if args.json:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
        else:
            _mostra_validacao(resultado)
        return 0 if resultado["ok"] else 1

    if args.comando == "chave":
        resultado = analisa_chave(args.chave)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0 if resultado.get("ok") else 1

    if args.comando == "rejeicao":
        if not args.codigo:
            for item in rejeicoes.listar():
                print(f"  {item['codigo']}  {item['significa']}")
            return 0
        resultado = rejeicoes.explica(args.codigo)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0 if resultado.get("ok") else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
