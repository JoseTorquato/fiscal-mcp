#!/usr/bin/env python3
"""Confere que o pacote instalado trouxe os dados de que o validador depende.

    cd /tmp && python -I /caminho/do/repo/scripts/conferir_pacote.py --instalado

Regras, tabela oficial, procedência, traduções de schema e registro de pacotes
de schema vivem fora de `fiscal_mcp/` no repositório e viajam no wheel por
force-include. Um pacote publicado sem eles é um validador que não valida nada,
e sem volta. Por isso esta conferência roda antes do upload (publicar.yml) e em
todo PR (testes.yml, job instalacao-limpa) — o mesmo script nos dois lugares,
para as duas conferências não divergirem.

A tabela é comparada com o que a PROCEDENCIA embarcada declara (contagem e
sha256), nunca com um número fixo aqui: a 0.3.0 quase saiu com `== 164` depois
de a tabela ter passado a 173.

`--instalado` exige que os dados venham de dentro do pacote instalado, e não do
repositório clonado. Rode com `python -I` e fora do repositório, senão o import
pode pegar o `fiscal_mcp/` do clone.

Sai com código 1 e uma mensagem por problema encontrado.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

PADRAO_CONTEUDO = re.compile(r"\*\*Conteúdo\*\*\s*\|\s*(\d+) CST · (\d+) cClassTrib")
PADRAO_SHA = re.compile(r"\*\*sha256\*\*\s*\|\s*`([0-9a-f]{64})`")


def confere(instalado: bool) -> list[str]:
    import fiscal_mcp
    from fiscal_mcp import schema, tabelas
    from fiscal_mcp.regras import carrega

    problemas: list[str] = []
    pacote = Path(fiscal_mcp.__file__).resolve().parent

    if instalado:
        for nome, raiz in (("tabelas", tabelas.RAIZ_TABELAS), ("schema", schema.RAIZ_SCHEMA)):
            if pacote not in raiz.resolve().parents:
                problemas.append(
                    f"os dados de {nome} vieram de {raiz}, fora do pacote instalado "
                    f"({pacote}): o wheel não os trouxe"
                )

    procedencia = tabelas.RAIZ_TABELAS / "PROCEDENCIA.md"
    tabela = tabelas.RAIZ_TABELAS / "cst-cclasstrib.json"
    registro = schema.RAIZ_SCHEMA / "pacotes.yaml"
    for arquivo in (procedencia, tabela, registro):
        if not arquivo.is_file():
            problemas.append(f"{arquivo.name} não está no pacote (procurado em {arquivo})")
    if problemas:
        return problemas  # sem os arquivos, as conferências abaixo só repetiriam isto

    try:
        n_regras = len(carrega())
    except FileNotFoundError as erro:
        return problemas + [f"as regras não vieram no pacote: {erro}"]
    except ValueError as erro:
        # o carregamento confere as regras contra a tabela (códigos de recorte,
        # indicadores): tabela com código trocado ou regra inconsistente cai aqui
        return problemas + [f"as regras não carregam contra a tabela embarcada: {erro}"]
    if n_regras < 25:
        problemas.append(f"só {n_regras} regras de NF-e no pacote; esperado ao menos 25")

    texto = procedencia.read_text(encoding="utf-8")
    conteudo, sha = PADRAO_CONTEUDO.search(texto), PADRAO_SHA.search(texto)
    if not conteudo or not sha:
        problemas.append("a PROCEDENCIA.md não declara 'Conteúdo' e 'sha256' no formato esperado")
    else:
        try:
            r = tabelas.resumo()
        except (ValueError, KeyError) as erro:
            return problemas + [f"a tabela embarcada não pôde ser lida: {erro!r}"]
        esperado = (int(conteudo[1]), int(conteudo[2]))
        if not r["disponivel"] or (r["cst"], r["cclasstrib"]) != esperado:
            problemas.append(f"tabela incompleta: {r} != PROCEDENCIA {esperado}")
        real = hashlib.sha256(tabela.read_bytes()).hexdigest()
        if real != sha[1]:
            problemas.append(f"sha256 da tabela ({real}) != PROCEDENCIA ({sha[1]})")

    if not schema._traducoes():
        problemas.append("as traduções de schema não vieram no pacote")
    if not schema.pacotes_conhecidos().get("pacotes"):
        problemas.append("o registro de pacotes de schema veio vazio")
    return problemas


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    analisador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analisador.add_argument("--instalado", action="store_true",
                            help="exige que os dados venham do pacote instalado")
    problemas = confere(analisador.parse_args(argv).instalado)
    for problema in problemas:
        print(f"::error::{problema}")
    if problemas:
        return 1
    print("regras, tabela, procedência, traduções e registro de schema conferidos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
