"""Testes do motor de regras: escopo e vigência.

Duas capacidades que a Camada A de IBS/CBS exige antes de qualquer regra fiscal
nova (docs/spec/05-camada-a-ibs-cbs.md §5):

  escopo: item   a regra roda uma vez por `det`, com caminhos relativos ao item
  vigencia       a regra diz quando será reavaliada, e o CI cobra a data

O teste que mais importa aqui é o de data vencida: é ele que transforma
manutenção de promessa em obrigação com quem usa.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_mcp.documento import Documento  # noqa: E402
from fiscal_mcp.regras import Alvo, Regra, aplica, carrega  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def nota(*numeros_de_item: str, com_ibs: tuple[str, ...] = ()) -> Documento:
    """NF-e mínima com os itens pedidos. `com_ibs` diz quais deles têm o grupo."""
    dets = []
    for n in numeros_de_item:
        grupo = "<IBSCBS><CST>000</CST></IBSCBS>" if n in com_ibs else ""
        dets.append(
            f'<det nItem="{n}">'
            f"<prod><cProd>{n}</cProd><vProd>10.00</vProd></prod>"
            f"<imposto>{grupo}</imposto>"
            f"</det>"
        )
    return Documento.de_texto(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">'
        '<infNFe versao="4.00" Id="NFe43260812345678000195550010000012341123456786">'
        + "".join(dets)
        + "</infNFe></NFe>"
    )


def regra_de_item(**extra) -> Regra:
    base = dict(
        id="teste-item",
        tipo="existe",
        severidade="erro",
        mensagem="grupo ausente",
        grupo="teste",
        escopo="item",
        campo="imposto/IBSCBS",
    )
    return Regra(**{**base, **extra})


# ---- escopo por item ------------------------------------------------------

def test_regra_de_item_roda_uma_vez_por_det():
    """Nota de 3 itens, nenhum com o grupo: 3 achados da mesma regra."""
    achados = aplica(nota("1", "2", "3"), [regra_de_item()])
    assert len(achados) == 3
    assert {a.item for a in achados} == {"1", "2", "3"}


def test_achado_de_item_usa_nItem_e_nao_o_indice():
    """Nota com numeração não sequencial existe. Apontar a posição manda procurar errado."""
    achados = aplica(nota("1", "5", "7"), [regra_de_item()])
    assert [a.item for a in achados] == ["1", "5", "7"]
    assert [a.para_dict()["detalhe"].split(":")[0] for a in achados] == [
        "item 1", "item 5", "item 7",
    ]


def test_so_o_item_que_viola_gera_achado():
    achados = aplica(nota("1", "2", "3", com_ibs=("1", "3")), [regra_de_item()])
    assert [a.item for a in achados] == ["2"]


def test_caminho_de_regra_de_item_e_relativo_ao_det():
    """`imposto/IBSCBS` no escopo item não pode casar com nada fora do `det`."""
    achados = aplica(nota("1", "2", com_ibs=("1",)), [regra_de_item()])
    assert len(achados) == 1 and achados[0].item == "2"


def test_regra_sem_escopo_continua_rodando_uma_vez():
    """Compatibilidade: regra que não declara escopo se comporta como antes."""
    doc = nota("1", "2", "3")
    regra = Regra(
        id="teste-doc", tipo="existe", severidade="erro",
        mensagem="ausente", grupo="teste", campo="ide/nNF",
    )
    achados = aplica(doc, [regra])
    assert len(achados) == 1
    assert achados[0].item is None
    assert "item" not in achados[0].para_dict()


def test_documento_sem_itens_nao_quebra_regra_de_item():
    """NFS-e não tem `det`. Regra de item simplesmente não roda."""
    doc = nota()
    assert aplica(doc, [regra_de_item()]) == []


def test_achado_de_item_expoe_o_numero_no_dict():
    d = aplica(nota("2"), [regra_de_item()])[0].para_dict()
    assert d["item"] == "2"
    assert d["detalhe"].startswith("item 2: ")


# ---- vigência -------------------------------------------------------------

def test_nenhuma_regra_com_reavaliacao_vencida():
    """O gatilho que garante que a manutenção acontece — e prova que aconteceu.

    Quando este teste falha em CI, não é bug: é uma nota técnica esperando
    leitura. Ver docs/spec/04-manutencao.md.
    """
    hoje = date.today()
    vencidas = [
        (r.id, r.vigencia.reavaliar_em)
        for documento in ("nfe", "nfse")
        for r in carrega(documento=documento)
        if r.vigencia and r.vigencia.reavaliar_em
        and date.fromisoformat(r.vigencia.reavaliar_em) < hoje
    ]
    assert not vencidas, (
        f"regras com reavaliação vencida: {vencidas}. "
        "Confira a fonte, atualize a regra e mova a data — ou remova a regra."
    )


def test_vigencia_chega_no_achado():
    """Quem lê o laudo precisa ver que a regra tem data de reavaliação e fonte."""
    com_vigencia = [r for r in carrega() if r.vigencia]
    assert com_vigencia, "o repo precisa ter ao menos uma regra com vigência declarada"

    regra = regra_de_item(vigencia=com_vigencia[0].vigencia)
    saida = aplica(nota("1"), [regra])[0].para_dict()
    assert saida["vigencia"]["reavaliar_em"]
    assert saida["vigencia"]["fonte"]


def test_regra_sem_vigencia_nao_polui_a_saida():
    assert "vigencia" not in aplica(nota("1"), [regra_de_item()])[0].para_dict()


def test_data_de_vigencia_invalida_e_recusada(tmp_path):
    _escreve(tmp_path, {"reavaliar_em": "setembro de 2026"})
    with pytest.raises(ValueError, match="não é data ISO"):
        carrega(raiz=tmp_path)


def test_data_sem_aspas_no_yaml_e_aceita(tmp_path):
    """`yaml` devolve `date` quando a data não está entre aspas. Não pode explodir."""
    caminho = tmp_path / "nfe" / "t.yaml"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        "grupo: t\nregras:\n  - id: t1\n    tipo: existe\n    campo: ide/nNF\n"
        "    mensagem: m\n    acao: a\n    vigencia:\n      reavaliar_em: 2099-01-01\n",
        encoding="utf-8",
    )
    assert carrega(raiz=tmp_path)[0].vigencia.reavaliar_em == "2099-01-01"


def test_status_antigo_pede_migracao(tmp_path):
    """`status: pendente_confirmacao` não tinha saída. Falhar é melhor que ignorar."""
    caminho = tmp_path / "nfe" / "t.yaml"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        "grupo: t\nregras:\n  - id: t1\n    tipo: existe\n    campo: ide/nNF\n"
        "    mensagem: m\n    acao: a\n    status: pendente_confirmacao\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="vigencia"):
        carrega(raiz=tmp_path)


def test_escopo_invalido_e_recusado(tmp_path):
    caminho = tmp_path / "nfe" / "t.yaml"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        "grupo: t\nregras:\n  - id: t1\n    tipo: existe\n    campo: ide/nNF\n"
        "    mensagem: m\n    acao: a\n    escopo: subitem\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="escopo"):
        carrega(raiz=tmp_path)


def _escreve(tmp_path: Path, vigencia: dict) -> None:
    caminho = tmp_path / "nfe" / "t.yaml"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        yaml.safe_dump(
            {"grupo": "t", "regras": [{
                "id": "t1", "tipo": "existe", "campo": "ide/nNF",
                "mensagem": "m", "acao": "a", "vigencia": vigencia,
            }]},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


# ---- caminho absoluto -----------------------------------------------------

def test_caminho_absoluto_escapa_do_item():
    """`/` no início vale a partir da raiz, mesmo numa regra de escopo item.

    Existe porque há regra que precisa olhar o item e algo fora dele ao mesmo
    tempo — "item com IBS/CBS exige o grupo de totais da nota". Sem isso, essa
    regra só conseguia enxergar o primeiro `det`.
    """
    doc = Documento.de_texto(
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">'
        '<infNFe versao="4.00">'
        '<det nItem="1"><imposto/></det>'
        '<det nItem="2"><imposto><IBSCBS/></imposto></det>'
        "<total><ICMSTot><vNF>1.00</vNF></ICMSTot></total>"
        "</infNFe></NFe>"
    )
    alvo_do_item = Alvo(doc).itens[0]
    assert alvo_do_item.existe("/total/ICMSTot/vNF"), "o absoluto precisa alcançar a raiz"
    assert not alvo_do_item.existe("total/ICMSTot/vNF"), "o relativo não sai do item"
    assert alvo_do_item.texto("/total/ICMSTot/vNF") == "1.00"


def test_caminho_absoluto_no_escopo_documento_nao_muda_nada():
    """Compatibilidade: na raiz, `/x` e `x` são a mesma coisa."""
    doc = Documento.de_texto(
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe versao="4.00">'
        "<ide><nNF>7</nNF></ide></infNFe></NFe>"
    )
    raiz = Alvo(doc)
    assert raiz.texto("ide/nNF") == raiz.texto("/ide/nNF") == "7"


def test_regra_de_item_enxerga_o_documento_inteiro():
    """O caso real: cada item que traz IBS/CBS cobra o grupo de totais da nota."""
    doc = Documento.de_texto(
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe versao="4.00">'
        '<det nItem="1"><imposto/></det>'
        '<det nItem="9"><imposto><IBSCBS><CST>000</CST></IBSCBS></imposto></det>'
        "</infNFe></NFe>"
    )
    regra = Regra(
        id="t", tipo="condicional", severidade="erro", mensagem="m", grupo="t",
        escopo="item", quando_campo="imposto/IBSCBS/CST", campo="/total/IBSCBSTot",
    )
    achados = aplica(doc, [regra])
    assert [a.item for a in achados] == ["9"], "só o item que tem IBS/CBS cobra o total"
