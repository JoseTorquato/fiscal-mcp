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
from .nfse import analisa_chave as analisa_chave_nfse
from .validador import explica_nfe, explica_nfse, valida_nfe, valida_nfse

VERM, AMAR, CIANO, CINZA, ZERA = "\033[31m", "\033[33m", "\033[36m", "\033[90m", "\033[0m"


def _cor(texto: str, cor: str) -> str:
    return f"{cor}{texto}{ZERA}" if sys.stdout.isatty() else texto


def _data_br(iso: str) -> str:
    ano, mes, dia = iso.split("-")
    return f"{dia}/{mes}/{ano}"


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
        # regra que ainda não estabilizou diz isso na cara de quem lê, não só no YAML
        reavaliar = a.get("vigencia", {}).get("reavaliar_em")
        if reavaliar:
            print(_cor(f"      regra em reavaliação até {_data_br(reavaliar)}", CINZA))
        print()

    veredito = "sem erros" if r["ok"] else f"{r['erros']} erro(s)"
    cor = CIANO if r["ok"] else VERM
    print(f"  {_cor(veredito, cor)}, {r['avisos']} aviso(s)")

    if doc := r.get("documento"):
        print(_cor(f"  {_uma_linha(doc)}", CINZA))
    print(_cor(f"  {r['nota']}\n", CINZA))


def _uma_linha(doc: dict) -> str:
    """Resumo de uma linha. NF-e e NFS-e têm formatos diferentes."""
    ident = doc.get("identificacao", {})
    if doc.get("documento") == "NFS-e":
        return (
            f"{doc['prestador']['nome']} · NFS-e {ident['numero_nfse']} · "
            f"{doc['servico']['descricao']} · R$ {doc['valores']['liquido']} · "
            f"{ident['ambiente']}"
        )
    return (
        f"{doc['emitente']['nome']} · nota {ident['numero']}/{ident['serie']} · "
        f"{doc['quantidade_itens']} itens · R$ {doc['totais']['nota']} · {ident['ambiente']}"
    )


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

    v = sub.add_parser("validar", help="valida um XML de NF-e ou NFS-e localmente")
    v.add_argument("arquivo", help="caminho do XML")
    v.add_argument("--json", action="store_true", help="saída em JSON")

    e = sub.add_parser("explicar", help="resume um XML de NF-e ou NFS-e")
    e.add_argument("arquivo")

    c = sub.add_parser("chave", help="analisa uma chave de acesso (44 ou 50 dígitos)")
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

        # detecta o documento: pedir ao usuário para escolher seria atrito à toa
        e_nfse = "infNFSe" in xml or "sped.fazenda.gov.br/nfse" in xml

        if args.comando == "explicar":
            explica = explica_nfse if e_nfse else explica_nfe
            print(json.dumps(explica(xml), ensure_ascii=False, indent=2))
            return 0

        resultado = (valida_nfse if e_nfse else valida_nfe)(xml)
        if args.json:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
        else:
            _mostra_validacao(resultado)
        return 0 if resultado["ok"] else 1

    if args.comando == "chave":
        # 50 dígitos é NFS-e; 44 é NF-e. Descobrir sozinho evita atrito.
        digitos = sum(c.isdigit() for c in args.chave)
        resultado = (analisa_chave_nfse if digitos == 50 else analisa_chave)(args.chave)
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
