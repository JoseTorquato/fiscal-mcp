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


def _nfelib_instalada() -> Path:
    import nfelib

    return Path(nfelib.__file__).parent


@precisa_do_extra
def test_declaracao_bate_com_os_xsd_que_a_nfelib_entrega():
    """O nome declarado no laudo tem de ser o do conteúdo, não de um texto solto.

    A versão anterior lia `PL_` no comentário do leiauteNFe e declarava
    `PL_005d` para a nfelib 3.3.0, que embarca o PL 010f v1.04. Este teste falha
    se o pacote declarado e os sha256 dos XSD instalados divergirem.
    """
    raiz = _nfelib_instalada()
    declarado = schema.declarado_pela_nfelib(raiz)
    registro = schema.pacotes_conhecidos()
    por_nome = {p["nome"]: p for p in registro["pacotes"]}
    if declarado not in por_nome:
        pytest.skip(
            f"a nfelib instalada declara {declarado!r}, que não está em "
            "regras/schema/pacotes.yaml: registre o pacote a partir do ZIP oficial"
        )
    instalados = schema.sha256_dos_xsd(raiz / "nfe" / "schemas" / "v4_0", registro["arquivos"])
    assert instalados == por_nome[declarado]["sha256"], (
        f"a nfelib declara {declarado}, mas os XSD instalados não são os do ZIP oficial"
    )
    assert schema.pacote().split(" ")[0] == declarado
    assert "não identificado" not in schema.pacote()


def _xsd_falsos(base: Path, conteudo: dict[str, bytes]) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    for nome, dados in conteudo.items():
        (base / nome).write_bytes(dados)
    return base


def _registro_falso(monkeypatch, pacotes: list[dict]) -> None:
    monkeypatch.setattr(schema, "pacotes_conhecidos", lambda: {
        "arquivos": ["a.xsd", "b.xsd"], "pacotes": pacotes,
    })


def test_identifica_pelo_conteudo_e_nao_pelo_texto(tmp_path, monkeypatch):
    import hashlib

    # o texto cita outro PL de propósito: é o engano que a versão antiga cometia
    base = _xsd_falsos(tmp_path, {"a.xsd": b"<!-- PL_005d -->", "b.xsd": b"b"})
    sha = {n: hashlib.sha256((base / n).read_bytes()).hexdigest() for n in ("a.xsd", "b.xsd")}
    _registro_falso(monkeypatch, [{"nome": "PL_TESTE_v1.00", "sha256": sha}])
    assert schema.identifica(base) == "PL_TESTE_v1.00"


def test_conteudo_fora_do_registro_nao_ganha_nome_adivinhado(tmp_path, monkeypatch):
    base = _xsd_falsos(tmp_path, {"a.xsd": b"x", "b.xsd": b"y"})
    _registro_falso(monkeypatch, [{"nome": "PL_TESTE_v1.00", "sha256": {"a.xsd": "0", "b.xsd": "0"}}])
    saida = schema.identifica(base, declarado="PL_999z_v9.99")
    assert saida.startswith("pacote não identificado")
    assert "PL_999z_v9.99" in saida, "o que a nfelib declara precisa aparecer"


def test_declaracao_que_diverge_do_conteudo_fica_a_vista(tmp_path, monkeypatch):
    import hashlib

    base = _xsd_falsos(tmp_path, {"a.xsd": b"a", "b.xsd": b"b"})
    sha = {n: hashlib.sha256((base / n).read_bytes()).hexdigest() for n in ("a.xsd", "b.xsd")}
    _registro_falso(monkeypatch, [{"nome": "PL_TESTE_v1.00", "sha256": sha}])
    saida = schema.identifica(base, declarado="PL_OUTRO_v2.00")
    assert saida.startswith("PL_TESTE_v1.00")
    assert "PL_OUTRO_v2.00" in saida


def test_le_a_declaracao_da_nfelib_sem_importar(tmp_path):
    init = tmp_path / "nfe" / "bindings" / "v4_0" / "__init__.py"
    init.parent.mkdir(parents=True)
    init.write_text(
        "SCHEMA_VERSION: str = 'PL_010f'\n"
        "SCHEMA_PACKAGE: str = 'Pacote de Liberação 010f (zip PL_010f_v1.04)'\n"
        "raise RuntimeError('não pode ser importado')\n",
        encoding="utf-8",
    )
    assert schema.declarado_pela_nfelib(tmp_path) == "PL_010f_v1.04"
    assert schema.declarado_pela_nfelib(tmp_path / "nada") is None


def test_registro_de_pacotes_tem_procedencia():
    """Cada pacote registrado diz de onde veio; sha256 é dado, não enfeite."""
    import re

    registro = schema.pacotes_conhecidos()
    assert registro["arquivos"], "o registro precisa dizer quais XSD identificam o pacote"
    nomes, conteudos = set(), set()
    for p in registro["pacotes"]:
        assert re.fullmatch(r"PL_\d{3}[a-z]_v\d\.\d{2}", p["nome"]), p["nome"]
        for chave in ("publicacao", "cobre", "zip", "zip_sha256", "baixado_em"):
            assert p.get(chave), f"{p['nome']} sem {chave}"
        assert re.fullmatch(r"[0-9a-f]{64}", p["zip_sha256"])
        assert set(p["sha256"]) == set(registro["arquivos"]), p["nome"]
        assert all(re.fullmatch(r"[0-9a-f]{64}", v) for v in p["sha256"].values())
        nomes.add(p["nome"])
        conteudos.add(tuple(sorted(p["sha256"].items())))
    assert len(nomes) == len(registro["pacotes"]), "nome repetido no registro"
    assert len(conteudos) == len(registro["pacotes"]), "dois pacotes com o mesmo conteúdo"


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
