"""Fragmentos de changelog em changelog.d/ — o formato de quatro campos do projeto.

Todo item do CHANGELOG diz quatro coisas (ver o cabeçalho do CHANGELOG.md):

    o que mudou · documento oficial · o que mudou no código · desde quando vale

Com o scriv, cada PR deixa um fragmento e o PR de release junta tudo. Este
teste é o que impede um fragmento de entrar sem os quatro campos — porque no
`scriv collect` ninguém vai reescrever entrada por entrada.

Regras, por categoria:

- **Toda categoria:** os quatro campos escritos, nenhum vazio.
- **"Absorvido da legislação"** (a única fiscal): "Documento oficial" não pode
  ser "não se aplica", e "Desde quando vale" precisa de uma data DD/MM/AAAA.
- **Demais categorias** (mudança não fiscal): "Documento oficial" e "Desde
  quando vale" podem dizer "não se aplica", mas precisam estar lá — a ausência
  vira dúvida, "não se aplica" é uma resposta.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
FRAGMENTOS = RAIZ / "changelog.d"
CONFIG = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["scriv"]

FISCAL = "Absorvido da legislação"
CAMPOS = ("O que mudou", "Documento oficial", "O que mudou no código", "Desde quando vale")
NAO_SE_APLICA = re.compile(r"^\s*não se aplica", re.IGNORECASE)
DATA = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")


def problemas(texto: str, categorias: list[str]) -> list[str]:
    """Lista o que está errado num fragmento. Vazia quando o fragmento serve."""
    achados: list[str] = []
    for marcador in (CONFIG.get("start_marker", "scriv-insert-here"),
                     CONFIG.get("end_marker", "scriv-end-here")):
        if marcador in texto:
            # o scriv começa a ler o fragmento depois da linha que contém o
            # marcador: tudo antes some do CHANGELOG em silêncio
            achados.append(f"o fragmento cita '{marcador}', e o scriv descartaria o texto anterior")
    sem_comentario = re.sub(r"<!--.*?-->", "", texto, flags=re.S)
    categoria: str | None = None
    itens: list[tuple[str | None, list[str]]] = []

    for linha in sem_comentario.splitlines():
        if linha.startswith("#"):
            titulo = re.match(r"^###\s+(.+?)\s*$", linha)
            if not titulo:
                achados.append(f"título fora do formato (use '### Categoria'): {linha!r}")
                continue
            categoria = titulo.group(1)
            if categoria not in categorias:
                achados.append(f"categoria desconhecida {categoria!r} — há {categorias}")
        elif linha.startswith("- "):
            itens.append((categoria, [linha]))
        elif itens and (linha.startswith(" ") or not linha.strip()):
            itens[-1][1].append(linha)
        elif linha.strip():
            achados.append(f"texto fora de item: {linha!r}")

    if not itens:
        achados.append("nenhum item: tire do comentário a categoria e escreva o item")

    for categoria_do_item, linhas in itens:
        corpo = "\n".join(linhas)
        nome = linhas[0][2:60]
        if categoria_do_item is None:
            achados.append(f"item sem categoria acima dele: {nome!r}")
        valores = {}
        for campo in CAMPOS:
            casou = re.search(
                rf"\*\*{re.escape(campo)}:\*\*(.*?)(?=\n\s*- \*\*|\Z)", corpo, flags=re.S
            )
            if not casou or not casou.group(1).strip():
                achados.append(f"{nome!r}: falta o campo '{campo}'")
            else:
                valores[campo] = " ".join(casou.group(1).split())
        if categoria_do_item == FISCAL:
            doc = valores.get("Documento oficial", "")
            if doc and NAO_SE_APLICA.match(doc):
                achados.append(f"{nome!r}: mudança fiscal precisa citar o documento oficial")
            desde = valores.get("Desde quando vale", "")
            if desde and not DATA.search(desde):
                achados.append(f"{nome!r}: mudança fiscal precisa de data DD/MM/AAAA em 'Desde quando vale'")
    return achados


def _fragmentos() -> list[Path]:
    return sorted(
        p for p in FRAGMENTOS.glob(f"*.{CONFIG['format']}") if not p.name.startswith("README")
    )


# ---- os fragmentos de verdade ----------------------------------------------

@pytest.mark.parametrize("fragmento", _fragmentos(), ids=lambda p: p.name)
def test_fragmento_tem_os_quatro_campos(fragmento):
    texto = fragmento.read_bytes().decode("utf-8")  # estrito: pega o acento quebrado
    assert problemas(texto, CONFIG["categories"]) == []


def test_fragmento_e_utf8_valido():
    """O scriv grava com a codificação do sistema; no Windows, sem PYTHONUTF8=1,
    o título da categoria sai em cp1252. Ver CONTRIBUTING.md."""
    for fragmento in _fragmentos():
        fragmento.read_bytes().decode("utf-8")


# ---- a configuração ----------------------------------------------------------

def test_categorias_incluem_a_fiscal():
    assert FISCAL in CONFIG["categories"]


def test_changelog_tem_o_marcador_de_insercao():
    texto = (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
    assert texto.count("<!-- scriv-insert-here -->") == 1
    assert texto.index("<!-- scriv-insert-here -->") < texto.index("\n## "), (
        "o marcador precisa vir antes da primeira versão, para a nova entrar no topo"
    )


def test_versoes_separadas_por_regua():
    """O `scriv collect` não põe o `---` entre versões, que o arquivo sempre usou.

    O PR de release acrescenta a linha à mão depois do collect; este teste
    falha se ela faltar.
    """
    texto = (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
    versoes = [m.start() for m in re.finditer(r"^## ", texto, flags=re.M)]
    for inicio in versoes[1:]:
        antes = texto[:inicio].rstrip()
        assert antes.endswith("---"), (
            f"falta a régua `---` antes de: {texto[inicio:inicio + 30]!r}"
        )


def test_o_modelo_descomentado_passa():
    """O exemplo do modelo e este teste precisam concordar."""
    modelo = (FRAGMENTOS / "_modelo.md.j2").read_text(encoding="utf-8")
    exemplo = re.search(r"<!--\n(### \{\{ cat \}\}.*?)\n-->", modelo, flags=re.S).group(1)
    nao_fiscal = exemplo.replace("{{ cat }}", "Alterado")
    assert problemas(nao_fiscal, CONFIG["categories"]) == []


def test_o_modelo_nao_e_coletado_como_fragmento():
    assert not (FRAGMENTOS / "_modelo.md.j2").match(f"*.{CONFIG['format']}")


# ---- o que o teste reprova ----------------------------------------------------

CATEGORIAS = CONFIG["categories"]

BOM_NAO_FISCAL = """### Alterado

- **Algo.**
  - **O que mudou:** x.
  - **Documento oficial:** não se aplica.
  - **O que mudou no código:** y.
  - **Desde quando vale:** não se aplica.
"""

BOM_FISCAL = """### Absorvido da legislação

- **NT tal.**
  - **O que mudou:** x.
  - **Documento oficial:** NT 2025.002 v1.53, de 30/10/2026.
  - **O que mudou no código:** regra y.
  - **Desde quando vale:** 16/11/2026; detectado em 24/11/2026.
"""


def test_fragmentos_bons_passam():
    assert problemas(BOM_NAO_FISCAL, CATEGORIAS) == []
    assert problemas(BOM_FISCAL, CATEGORIAS) == []


@pytest.mark.parametrize("campo", CAMPOS)
def test_falta_de_qualquer_campo_reprova(campo):
    linhas = [l for l in BOM_NAO_FISCAL.splitlines() if f"**{campo}:**" not in l]
    achados = problemas("\n".join(linhas), CATEGORIAS)
    assert any(f"falta o campo '{campo}'" in a for a in achados), achados


def test_campo_vazio_reprova():
    texto = BOM_NAO_FISCAL.replace("**O que mudou:** x.", "**O que mudou:**")
    assert any("falta o campo 'O que mudou'" in a for a in problemas(texto, CATEGORIAS))


def test_fiscal_sem_documento_reprova():
    texto = BOM_FISCAL.replace("NT 2025.002 v1.53, de 30/10/2026.", "não se aplica.")
    assert any("documento oficial" in a for a in problemas(texto, CATEGORIAS))


def test_fiscal_sem_data_reprova():
    texto = BOM_FISCAL.replace("16/11/2026; detectado em 24/11/2026.", "na próxima versão.")
    assert any("DD/MM/AAAA" in a for a in problemas(texto, CATEGORIAS))


def test_categoria_desconhecida_reprova():
    texto = BOM_NAO_FISCAL.replace("### Alterado", "### Melhorias")
    assert any("categoria desconhecida" in a for a in problemas(texto, CATEGORIAS))


def test_fragmento_so_com_comentario_reprova():
    """O modelo sem nada descomentado não descreve mudança nenhuma."""
    modelo = (FRAGMENTOS / "_modelo.md.j2").read_text(encoding="utf-8")
    texto = re.sub(r"\{%.*?%\}", "", modelo).replace("{{ cat }}", "Alterado")
    assert any("nenhum item" in a for a in problemas(texto, CATEGORIAS))


def test_citar_o_marcador_do_scriv_reprova():
    """Aconteceu neste PR: o fragmento citava o marcador e o collect cortou o item."""
    texto = BOM_NAO_FISCAL.replace("**O que mudou no código:** y.",
                                   "**O que mudou no código:** marcador scriv-insert-here.")
    assert any("descartaria" in a for a in problemas(texto, CATEGORIAS))


def test_item_sem_categoria_reprova():
    texto = BOM_NAO_FISCAL.replace("### Alterado\n", "")
    assert any("sem categoria" in a for a in problemas(texto, CATEGORIAS))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
