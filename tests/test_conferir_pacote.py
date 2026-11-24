"""Testes de scripts/conferir_pacote.py, a conferência do wheel antes do upload.

O script roda no publicar.yml, depois que o release já foi criado: falhar ali
com `FileNotFoundError` cru, ou passar quando falta dado, é caro. Aqui ele roda
contra o repositório e contra cópias estragadas dos dados.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

import conferir_pacote  # noqa: E402
from fiscal_mcp import schema, tabelas  # noqa: E402


@pytest.fixture
def dados(tmp_path, monkeypatch):
    """Cópia de regras/tabelas e regras/schema que o teste pode estragar."""
    destino_tab = tmp_path / "tabelas"
    destino_sch = tmp_path / "schema"
    shutil.copytree(RAIZ / "regras" / "tabelas", destino_tab)
    shutil.copytree(RAIZ / "regras" / "schema", destino_sch)
    monkeypatch.setattr(tabelas, "RAIZ_TABELAS", destino_tab)
    monkeypatch.setattr(schema, "RAIZ_SCHEMA", destino_sch)
    tabelas.cst_cclasstrib.cache_clear()
    schema._traducoes.cache_clear()
    yield destino_tab, destino_sch
    tabelas.cst_cclasstrib.cache_clear()
    schema._traducoes.cache_clear()


def test_o_repositorio_passa():
    assert conferir_pacote.confere(instalado=False) == []


def test_no_repositorio_clonado_o_modo_instalado_acusa_a_origem():
    """Do clone, os dados vêm de fora de `fiscal_mcp/`: --instalado precisa ver isso."""
    problemas = conferir_pacote.confere(instalado=True)
    assert any("fora do pacote instalado" in p for p in problemas), problemas


@pytest.mark.parametrize("arquivo", ["PROCEDENCIA.md", "cst-cclasstrib.json"])
def test_arquivo_da_tabela_ausente_vira_mensagem_clara(dados, arquivo):
    (dados[0] / arquivo).unlink()
    problemas = conferir_pacote.confere(instalado=False)
    assert any(arquivo in p and "não está no pacote" in p for p in problemas), problemas


def test_registro_de_schema_ausente_vira_mensagem_clara(dados):
    (dados[1] / "pacotes.yaml").unlink()
    problemas = conferir_pacote.confere(instalado=False)
    assert any("pacotes.yaml" in p and "não está no pacote" in p for p in problemas), problemas


def test_tabela_alterada_falha_pelo_sha256(dados):
    tabela = dados[0] / "cst-cclasstrib.json"
    tabela.write_bytes(tabela.read_bytes() + b" ")
    problemas = conferir_pacote.confere(instalado=False)
    assert any("sha256 da tabela" in p for p in problemas), problemas


def test_tabela_com_codigo_trocado_vira_mensagem_clara(dados):
    """O carregamento confere as regras contra a tabela: um código de recorte que
    sumiu dela era ValueError cru do carrega(), sem ::error::."""
    tabela = dados[0] / "cst-cclasstrib.json"
    texto = tabela.read_text(encoding="utf-8")
    assert texto.count('"550002"') == 1, "a tabela mudou: ajuste este teste"
    tabela.write_text(texto.replace('"550002"', '"559999"'), encoding="utf-8")
    problemas = conferir_pacote.confere(instalado=False)
    assert any("não carregam contra a tabela" in p and "550002" in p for p in problemas), problemas


def test_tabela_ilegivel_vira_mensagem_clara(dados):
    (dados[0] / "cst-cclasstrib.json").write_text("{ não é json", encoding="utf-8")
    problemas = conferir_pacote.confere(instalado=False)
    assert problemas and all("Traceback" not in p for p in problemas), problemas


def test_contagem_declarada_diferente_falha(dados):
    """A contagem vem da PROCEDENCIA, não de um número no workflow."""
    procedencia = dados[0] / "PROCEDENCIA.md"
    texto = procedencia.read_text(encoding="utf-8")
    assert "18 CST · 173 cClassTrib" in texto, "a PROCEDENCIA mudou: ajuste este teste"
    procedencia.write_text(texto.replace("18 CST · 173 cClassTrib", "18 CST · 999 cClassTrib"),
                           encoding="utf-8")
    problemas = conferir_pacote.confere(instalado=False)
    assert any("tabela incompleta" in p for p in problemas), problemas


def test_saida_e_codigo_de_retorno(dados, capsys):
    (dados[0] / "PROCEDENCIA.md").unlink()
    assert conferir_pacote.main([]) == 1
    assert "::error::" in capsys.readouterr().out
