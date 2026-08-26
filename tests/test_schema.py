"""Testes da camada de validação por schema XSD (spec 06).

O que esta camada promete: reprovar antes o que a SEFAZ reprovaria, com mensagem
em português e ação — não com o erro cru do lxml.

Os testes de tradução são o coração daqui. Rodar o XSD é uma tarde; traduzir é o
produto. Sem tradução esta camada não vale mais que o `xmllint` que o dev já tem.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_mcp import schema  # noqa: E402
from fiscal_mcp.validador import valida_nfe  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
VALIDA = (RAIZ / "exemplos" / "nfe-valida.xml").read_text(encoding="utf-8")
COM_IBS = (RAIZ / "exemplos" / "nfe-ibs-cbs.xml").read_text(encoding="utf-8")

precisa_do_extra = pytest.mark.skipif(
    not schema.disponivel(), reason="extra [xsd] não instalado"
)


# ---- o que sustenta a camada ---------------------------------------------

@precisa_do_extra
def test_nota_com_ibs_cbs_passa_no_schema_sem_erro():
    """Se falhar aqui, o problema é a versão do pacote e a camada não sobe.

    É o critério de saída da spec 06 §6: um XML válido de NF-e com IBS/CBS não
    pode gerar achado de schema de severidade erro. Sem exceção.
    """
    erros = [a for a in schema.valida(COM_IBS) if a["severidade"] == "erro"]
    assert not erros, erros


@precisa_do_extra
def test_nota_classica_passa_no_schema_sem_erro():
    erros = [a for a in schema.valida(VALIDA) if a["severidade"] == "erro"]
    assert not erros, erros


@precisa_do_extra
def test_documento_nao_assinado_e_informacao_e_nao_erro():
    """O caso normal de uso é justamente o XML ainda não assinado.

    O schema oficial exige Signature dentro de NFe, e esta ferramenta não assina
    nada por decisão. Reprovar aqui seria reprovar todo mundo que usa a
    ferramenta para o que ela existe.
    """
    achado = [a for a in schema.valida(COM_IBS) if a["id"] == "schema-sem-assinatura"]
    assert achado, "a ausência de assinatura precisa ser dita, não escondida"
    assert achado[0]["severidade"] == "informacao"
    assert "não assina" in achado[0]["acao"]


# ---- tradução: o produto desta camada ------------------------------------

@precisa_do_extra
def test_elemento_obrigatorio_ausente_vira_portugues_com_acao():
    # vNF fecha o ICMSTot: tirar o último da sequência produz "falta um filho",
    # enquanto tirar um do meio produz "elemento fora de ordem"
    sem_vnf = VALIDA.replace("<vNF>250.00</vNF>", "", 1)
    achado = [a for a in schema.valida(sem_vnf) if a["severidade"] == "erro"][0]
    assert "obrigatório" in achado["problema"]
    assert "vNF" in achado["problema"]
    assert achado["acao"], "achado de schema sem ação é inútil para um agente"
    assert "portalfiscal.inf.br" not in achado["problema"], "namespace não vaza"


@precisa_do_extra
def test_elemento_fora_de_ordem_explica_que_a_ordem_conta():
    trocado = VALIDA.replace(
        "<cEAN>SEM GTIN</cEAN>\n        <xProd>Produto de exemplo A</xProd>",
        "<xProd>Produto de exemplo A</xProd>\n        <cEAN>SEM GTIN</cEAN>",
        1,
    )
    achado = [a for a in schema.valida(trocado) if a["severidade"] == "erro"][0]
    assert "ordem" in achado["acao"]


@precisa_do_extra
def test_valor_fora_do_tipo_e_traduzido():
    """Escala decimal errada: o XSD carrega o padrão real do leiaute."""
    dentro = "<gIBSCBS>\n            <vBC>"
    quebrado = COM_IBS.replace(dentro + "200.00</vBC>", dentro + "200.0000</vBC>", 1)
    achado = [a for a in schema.valida(quebrado) if a["severidade"] == "erro"][0]
    assert "200.0000" in achado["problema"]
    assert achado["acao"]


@precisa_do_extra
def test_o_achado_aponta_o_item_pelo_nItem():
    """Como no motor de regras: o número que a nota usa, não a posição."""
    sem_ncm = COM_IBS.replace("<NCM>84713012</NCM>", "", 1)
    achado = [a for a in schema.valida(sem_ncm) if a.get("item")][0]
    assert achado["item"] == "1"
    assert achado["detalhe"].startswith("item 1, linha ")


@precisa_do_extra
def test_mensagem_desconhecida_sai_crua_e_marcada(monkeypatch):
    """Adivinhar produziria achado bonito e errado. Cru e honesto é melhor."""
    monkeypatch.setattr(schema, "_traducoes", lambda: ())
    sem_ncm = VALIDA.replace("<NCM>84713012</NCM>", "", 1)
    achado = [a for a in schema.valida(sem_ncm) if a["severidade"] == "erro"][0]
    assert achado["id"] == "schema-nao-traduzido"
    assert achado["traduzido"] is False
    assert achado["problema"].startswith("Element '"), "a mensagem original é preservada"
    assert "portalfiscal.inf.br" not in achado["problema"], "só o namespace sai"


@precisa_do_extra
def test_toda_traducao_tem_acao():
    for t in schema._traducoes():
        assert t.acao, f"tradução {t.id} sem ação"


@precisa_do_extra
def test_traducoes_de_ibs_cbs_existem():
    """Traduzir primeiro os erros que aparecem: a dor de 2026 é aqui."""
    ids = {t.id for t in schema._traducoes()}
    assert {"schema-cclasstrib-ausente", "schema-cst-ausente", "schema-ibscbstot-ausente"} <= ids


# ---- versão do pacote ----------------------------------------------------

@precisa_do_extra
def test_pacote_declara_o_leiaute_em_uso():
    """"Passou no schema" é frase sem sujeito se não disser contra o quê."""
    assert schema.pacote().startswith("PL_")
    assert "nfelib" in schema.pacote()


@precisa_do_extra
def test_elemento_desconhecido_pelo_pacote_e_rebaixado_para_aviso():
    """Documento com leiaute posterior ao pacote não pode ser reprovado.

    Falso positivo em schema é pior que em regra: parece autoritativo.
    """
    posterior = COM_IBS.replace(
        "</gIBSCBS>", "</gIBSCBS><gInventadoPorNotaTecnicaFutura/>", 1
    )
    achados = [a for a in schema.valida(posterior) if "nao_coberto_pelo_pacote" in a]
    assert achados, "elemento desconhecido pelo pacote precisa ser detectado"
    assert achados[0]["severidade"] == "aviso"
    assert "gInventadoPorNotaTecnicaFutura" in achados[0]["nao_coberto_pelo_pacote"]
    assert "não conhece" in achados[0]["acao"]


# ---- integração com o laudo ----------------------------------------------

@precisa_do_extra
def test_laudo_declara_contra_o_que_validou():
    r = valida_nfe(COM_IBS)
    assert r["schema_disponivel"] is True
    assert r["leiaute_validado_contra"].startswith("PL_")
    assert "schema XSD oficial" in r["nota"]


def test_sem_o_extra_nada_quebra_e_a_saida_avisa(monkeypatch):
    """Sem o extra a validação de schema não roda — e nunca finge que rodou."""
    monkeypatch.setattr(schema, "disponivel", lambda: False)
    r = valida_nfe(COM_IBS)
    assert r["schema_disponivel"] is False
    assert r["leiaute_validado_contra"] is None
    assert "fiscal-mcp[xsd]" in r["nota"]
    assert not [a for a in r["achados"] if a["grupo"] == "schema"]


@precisa_do_extra
def test_schema_pode_ser_desligado():
    r = valida_nfe(COM_IBS, schema=False)
    assert r["schema_disponivel"] is False
    assert not [a for a in r["achados"] if a["grupo"] == "schema"]


@precisa_do_extra
def test_achado_de_schema_entra_no_mesmo_laudo():
    """Uma lista só. Quem chama recebe um laudo, não dois."""
    sem_ncm = VALIDA.replace("<NCM>84713012</NCM>", "", 1)
    r = valida_nfe(sem_ncm)
    grupos = {a["grupo"] for a in r["achados"]}
    assert "schema" in grupos
    assert not r["ok"]


# ---- zero rede -----------------------------------------------------------

@precisa_do_extra
def test_a_camada_de_schema_nao_abre_socket(monkeypatch):
    """`XMLSchema` do lxml resolve xs:include e poderia buscar import remoto."""
    import socket

    def proibido(*_a, **_k):
        raise AssertionError("a camada de schema tentou abrir socket")

    monkeypatch.setattr(socket.socket, "connect", proibido)
    monkeypatch.setattr(socket, "create_connection", proibido)
    schema._esquema.cache_clear()
    schema._nomes_conhecidos.cache_clear()
    assert schema.valida(COM_IBS) is not None
