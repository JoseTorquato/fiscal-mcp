#!/usr/bin/env python3
"""Baixa a tabela oficial de CST e cClassTrib do Portal da Conformidade Fácil.

Este script NÃO roda em CI, e isso é deliberado: indisponibilidade da SVRS não
pode quebrar o build de quem depende do pacote. A tabela vive versionada no
repositório e a atualização é ato consciente — rodar isto, conferir o diff,
atualizar a PROCEDENCIA e abrir PR.

    python scripts/baixar_tabelas.py

O portal serve a tabela inteira embutida na página, na variável JavaScript
`dadosOriginais`. É a mesma estrutura que alimenta a exportação em CSV/Excel do
próprio portal — dado da fonte, não raspagem de HTML renderizado.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from datetime import date, timezone, datetime
from pathlib import Path

URL = "https://dfe-portal.svrs.rs.gov.br/CFF/ClassificacaoTributaria"
DESTINO = Path(__file__).resolve().parent.parent / "regras" / "tabelas"
ARQUIVO = DESTINO / "cst-cclasstrib.json"

# Campos descartados, e por quê. Sai aqui e é registrado na PROCEDENCIA:
#   CstNavigation  duplicata integral do CST pai, já presente um nível acima
#   Anexos,        listas de produtos por anexo (NCM de monofasia). São o grosso
#   AnexoNew,      dos 4 MB da página e não participam de nenhuma regra da
#   NroAnexo       Camada A — entram quando houver regra que os use
#   CtrDthInc      carimbo de controle interno do portal, sem uso fiscal
DESCARTADOS = {"CstNavigation", "Anexos", "AnexoNew", "NroAnexo", "CtrDthInc"}


def extrai_json(pagina: str) -> list[dict]:
    """Recorta o array de `var dadosOriginais = [...]` por balanceamento."""
    marca = "var dadosOriginais = "
    inicio = pagina.find(marca)
    if inicio < 0:
        raise SystemExit(
            "não encontrei 'var dadosOriginais' na página — o portal mudou de "
            "formato. Confira a estrutura antes de atualizar a tabela."
        )
    inicio += len(marca)
    profundidade = 0
    for posicao in range(inicio, len(pagina)):
        if pagina[posicao] == "[":
            profundidade += 1
        elif pagina[posicao] == "]":
            profundidade -= 1
            if profundidade == 0:
                return json.loads(pagina[inicio:posicao + 1])
    raise SystemExit("array de dados não fecha — página truncada?")


def _data(bruto: str | None) -> str | None:
    """'2025-05-01T00:00:00' -> '2025-05-01'. Hora não significa nada aqui."""
    return bruto[:10] if bruto else None


def _limpa(registro: dict) -> dict:
    saida = {}
    for chave, valor in sorted(registro.items()):
        if chave in DESCARTADOS or chave == "ClassificacoesTributarias":
            continue
        if chave.startswith("Dth") and isinstance(valor, str):
            valor = _data(valor)
        saida[chave] = valor
    return saida


def normaliza(dados: list[dict]) -> dict:
    """Estrutura estável: mesma entrada gera byte a byte o mesmo arquivo.

    Sem isso o sha256 da procedência viraria ruído — qualquer reordenação do
    portal apareceria como "a tabela mudou".
    """
    cst = []
    for bruto in sorted(dados, key=lambda d: d["Cst"]):
        classificacoes = [
            _limpa(c)
            for c in sorted(bruto["ClassificacoesTributarias"], key=lambda c: c["CodClassTrib"])
        ]
        cst.append({**_limpa(bruto), "ClassificacoesTributarias": classificacoes})

    publicacoes = sorted({
        c["DthPublicacao"] for grupo in cst
        for c in grupo["ClassificacoesTributarias"] if c.get("DthPublicacao")
    })
    return {
        "tabela": "cst-cclasstrib",
        "fonte": URL,
        "publicacao_declarada_pela_fonte": publicacoes[-1] if publicacoes else None,
        "campos_descartados": sorted(DESCARTADOS),
        "cst": cst,
    }


def main() -> int:
    print(f"baixando {URL}")
    with urllib.request.urlopen(URL, timeout=60) as resposta:
        pagina = resposta.read().decode("utf-8")

    tabela = normaliza(extrai_json(pagina))
    quantos = sum(len(g["ClassificacoesTributarias"]) for g in tabela["cst"])
    texto = json.dumps(tabela, ensure_ascii=False, indent=2, sort_keys=False) + "\n"

    DESTINO.mkdir(parents=True, exist_ok=True)
    anterior = ARQUIVO.read_text(encoding="utf-8") if ARQUIVO.exists() else None
    ARQUIVO.write_text(texto, encoding="utf-8", newline="\n")

    sha = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    print(f"{len(tabela['cst'])} CST · {quantos} cClassTrib · {len(texto):,} bytes")
    print(f"publicação declarada pela fonte: {tabela['publicacao_declarada_pela_fonte']}")
    print(f"sha256: {sha}")
    if anterior == texto:
        print("sem mudança em relação ao que já estava versionado.")
    else:
        print(
            "\nA TABELA MUDOU. Antes de commitar:\n"
            "  1. confira o diff — dado oficial mudando é notícia, não rotina\n"
            f"  2. atualize o sha256 em {DESTINO / 'PROCEDENCIA.md'}\n"
            f"  3. registre a data de detecção no CHANGELOG"
        )
    print(f"\nbaixado em {date.today().isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
