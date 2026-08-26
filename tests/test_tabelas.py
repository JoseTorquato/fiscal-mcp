"""Testes das tabelas oficiais embarcadas.

O teste que sustenta esta camada é o de sha256: se o arquivo mudou sem passar
pela PROCEDENCIA, alguém editou dado oficial à mão. Isso precisa quebrar o
build, não passar despercebido.

O CI nunca baixa nada aqui — indisponibilidade da SVRS não pode quebrar o build
de terceiro. Ver regras/tabelas/PROCEDENCIA.md.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_mcp import tabelas  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
TABELA = RAIZ / "regras" / "tabelas" / "cst-cclasstrib.json"
PROCEDENCIA = RAIZ / "regras" / "tabelas" / "PROCEDENCIA.md"

# Os 18 CST, conforme duas fontes secundárias independentes citadas na spec 05 §7.
# A tabela baixada precisa concordar; se divergir, a tabela vence e esta lista
# muda junto com a PROCEDENCIA — nunca em silêncio.
CST_ESPERADOS = {
    "000", "010", "011", "200", "220", "221", "222", "400", "410",
    "510", "515", "550", "620", "800", "810", "811", "820", "830",
}


def test_tabela_esta_no_repositorio():
    assert TABELA.is_file(), "a tabela oficial precisa estar versionada, não baixada em build"


def test_sha256_confere_com_a_procedencia():
    """Divergência aqui = dado oficial editado à mão. É para quebrar mesmo."""
    declarado = re.search(r"\*\*sha256\*\*\s*\|\s*`([0-9a-f]{64})`", PROCEDENCIA.read_text(encoding="utf-8"))
    assert declarado, "PROCEDENCIA.md precisa declarar o sha256 da tabela"
    real = hashlib.sha256(TABELA.read_bytes()).hexdigest()
    assert real == declarado.group(1), (
        f"sha256 da tabela ({real}) não bate com o declarado ({declarado.group(1)}). "
        "Se a atualização foi deliberada, rode scripts/baixar_tabelas.py e atualize a PROCEDENCIA."
    )


def test_os_18_cst_estao_presentes():
    tabela = tabelas.cst_cclasstrib()
    assert set(tabela.cst) == CST_ESPERADOS


def test_cclasstrib_tem_seis_digitos_e_prefixo_do_cst():
    """A regra estrutural da L-02, conferida contra a própria fonte oficial.

    Se a fonte publicasse um cClassTrib que não começa pelo CST, a L-02 estaria
    errada — e é melhor descobrir aqui do que reprovando nota de cliente.
    """
    for codigo, linha in tabelas.cst_cclasstrib().classificacoes.items():
        assert re.fullmatch(r"\d{6}", codigo), f"{codigo} não tem 6 dígitos"
        assert codigo.startswith(linha.cst), f"{codigo} não começa pelo CST {linha.cst}"


def test_toda_classificacao_aponta_para_um_cst_existente():
    tabela = tabelas.cst_cclasstrib()
    for linha in tabela.classificacoes.values():
        assert linha.cst in tabela.cst


def test_indicadores_de_documento_existem():
    """Sem IndNfe/IndNfce não dá para escrever a L-04 (cClassTrib por modelo)."""
    linha = tabelas.cst_cclasstrib().classificacoes["000001"]
    assert linha.vale_para_modelo("55") is True
    assert linha.vale_para_modelo("65") is True
    assert linha.vale_para_modelo("57") is None, "não opinamos sobre documento que não validamos"


def test_resumo_diz_contra_o_que_se_valida():
    r = tabelas.resumo()
    assert r["disponivel"] and r["cst"] == 18 and r["cclasstrib"] == 164
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["publicacao_declarada_pela_fonte"])


def test_tabela_ausente_nao_e_erro_fatal(tmp_path):
    """Instalação sem tabela precisa dizer isso, não explodir com KeyError."""
    tabelas.cst_cclasstrib.cache_clear()
    with pytest.raises(tabelas.TabelaAusente):
        tabelas.cst_cclasstrib(tmp_path)
    tabelas.cst_cclasstrib.cache_clear()


def test_o_carregador_nao_toca_a_rede(monkeypatch):
    """Garantia de zero-rede estendida à camada de tabelas (spec 05 §9.7)."""
    import socket

    def proibido(*_a, **_k):
        raise AssertionError("a camada de tabelas tentou abrir socket")

    monkeypatch.setattr(socket.socket, "connect", proibido)
    monkeypatch.setattr(socket, "create_connection", proibido)
    tabelas.cst_cclasstrib.cache_clear()
    assert len(tabelas.cst_cclasstrib()) == 164


def test_indicadores_vem_dos_dois_niveis():
    """A tabela reparte a informação entre CST e cClassTrib.

    Os indicadores de estrutura do grupo (redução de alíquota, diferimento,
    monofasia) ficam no CST; os da classificação ficam nela. Uma regra que
    consultasse só um nível deixaria metade das exigências invisível — foi o
    que a spec 05 §6 supunha ao descrever a L-05 como "colunas ind_g*".
    """
    tabela = tabelas.cst_cclasstrib()

    do_cst = {"IndReducaoAliq", "IndDiferimento", "IndMonofasica",
              "IndTransferenciaCred", "IndAjusteCompet", "IndCredPresIbsZfm"}
    da_classificacao = {"IndTribRegular", "IndPermiteCredPres", "IndEstornoCred"}
    assert do_cst | da_classificacao <= tabela.indicadores_conhecidos

    # 200008 é do CST 200, que tem redução de alíquota
    juntos = tabela.indicadores_de("200008")
    assert "IndReducaoAliq" in juntos, "indicador do CST precisa alcançar o cClassTrib"
    assert "IndTribRegular" in juntos, "indicador da própria classificação precisa estar lá"


def test_indicadores_de_codigo_inexistente_devolve_none():
    assert tabelas.cst_cclasstrib().indicadores_de("999999") is None
