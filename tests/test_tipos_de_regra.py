"""Testes dos tipos de regra da Camada A (spec 05 §5.2).

Três contratos são testados em todos os tipos, porque violá-los é como um
validador começa a acusar errado:

1. campo ausente devolve None — obrigatoriedade é de outra regra (spec §5.3);
2. tabela ausente vira `informacao`, nunca `erro` — defeito de instalação não
   pode reprovar nota de ninguém;
3. número é comparado como número — `0.10` e `0.1000` são o mesmo valor.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_mcp import tabelas  # noqa: E402
from fiscal_mcp.documento import Documento  # noqa: E402
from fiscal_mcp.regras import Regra, aplica, carrega  # noqa: E402


def nota(imposto: str = "", *, modelo: str = "55", nItem: str = "1") -> Documento:
    """NF-e de um item, com o XML de imposto que o teste quiser."""
    return Documento.de_texto(
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">'
        '<infNFe versao="4.00" Id="NFe43260812345678000195550010000012341123456786">'
        f"<ide><mod>{modelo}</mod></ide>"
        f'<det nItem="{nItem}"><prod><vProd>10.00</vProd></prod>'
        f"<imposto>{imposto}</imposto></det>"
        "</infNFe></NFe>"
    )


def regra(**campos) -> Regra:
    base = dict(
        id="t", severidade="erro", mensagem="m", grupo="t", escopo="item",
    )
    return Regra(**{**base, **campos})


def roda(doc: Documento, r: Regra) -> list[dict]:
    return [a.para_dict() for a in aplica(doc, [r])]


def detalhe(doc: Documento, r: Regra) -> str:
    achados = roda(doc, r)
    assert achados, "esperava um achado e não veio nenhum"
    return achados[0]["detalhe"]


# ---- prefixo_de -----------------------------------------------------------

PREFIXO = dict(
    tipo="prefixo_de", campo="imposto/IBSCBS/cClassTrib",
    campo_referencia="imposto/IBSCBS/CST", tamanho=3,
)


def test_prefixo_de_reprova_quando_nao_casa():
    doc = nota("<IBSCBS><CST>200</CST><cClassTrib>000123</cClassTrib></IBSCBS>")
    assert detalhe(doc, regra(**PREFIXO)) == (
        "item 1: imposto/IBSCBS/cClassTrib = '000123' não começa por imposto/IBSCBS/CST = '200'"
    )


def test_prefixo_de_aprova_quando_casa():
    doc = nota("<IBSCBS><CST>200</CST><cClassTrib>200008</cClassTrib></IBSCBS>")
    assert roda(doc, regra(**PREFIXO)) == []


def test_prefixo_de_ignora_campo_ausente():
    """Sem o grupo, quem reclama é uma regra `existe` — não catorze regras."""
    assert roda(nota(), regra(**PREFIXO)) == []
    assert roda(nota("<IBSCBS><CST>200</CST></IBSCBS>"), regra(**PREFIXO)) == []


# ---- em_tabela ------------------------------------------------------------

CST_EXISTE = dict(
    tipo="em_tabela", campo="imposto/IBSCBS/CST", tabela="cst-cclasstrib", coluna="cst",
)
CLASS_MODELO = dict(
    tipo="em_tabela", campo="imposto/IBSCBS/cClassTrib", tabela="cst-cclasstrib",
    coluna="cclasstrib", filtro="modelo_do_documento",
)


def test_em_tabela_reprova_codigo_inexistente():
    doc = nota("<IBSCBS><CST>999</CST></IBSCBS>")
    d = detalhe(doc, regra(**CST_EXISTE))
    assert "imposto/IBSCBS/CST = '999' não existe na tabela cst-cclasstrib" in d
    assert "2026-06-22" in d, "o achado precisa dizer contra qual versão validou"


def test_em_tabela_aprova_codigo_oficial():
    assert roda(nota("<IBSCBS><CST>000</CST></IBSCBS>"), regra(**CST_EXISTE)) == []


def test_em_tabela_ignora_campo_ausente():
    assert roda(nota(), regra(**CST_EXISTE)) == []


def test_filtro_de_modelo_usa_o_indicador_da_tabela():
    """`200001` existe, mas a tabela diz que não vale para NF-e nem NFC-e."""
    doc = nota("<IBSCBS><cClassTrib>200001</cClassTrib></IBSCBS>", modelo="55")
    assert "não é permitido no modelo 55 (NF-e)" in detalhe(doc, regra(**CLASS_MODELO))


def test_filtro_de_modelo_aprova_o_que_a_tabela_permite():
    doc = nota("<IBSCBS><cClassTrib>000001</cClassTrib></IBSCBS>", modelo="55")
    assert roda(doc, regra(**CLASS_MODELO)) == []


def test_tabela_ausente_vira_informacao_e_nao_erro(monkeypatch):
    """Defeito de instalação não pode reprovar a nota de ninguém."""
    def sem_tabela(*_a, **_k):
        raise tabelas.TabelaAusente("tabela não encontrada em lugar nenhum")

    monkeypatch.setattr(tabelas, "cst_cclasstrib", sem_tabela)
    achados = roda(nota("<IBSCBS><CST>999</CST></IBSCBS>"), regra(**CST_EXISTE))
    assert len(achados) == 1
    assert achados[0]["severidade"] == "informacao"
    assert "não avaliada" in achados[0]["detalhe"]


def test_tabela_ausente_nao_repete_o_aviso_por_item(monkeypatch):
    def sem_tabela(*_a, **_k):
        raise tabelas.TabelaAusente("ausente")

    monkeypatch.setattr(tabelas, "cst_cclasstrib", sem_tabela)
    doc = Documento.de_texto(
        '<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe versao="4.00">'
        + "".join(f'<det nItem="{n}"><imposto><IBSCBS><CST>9</CST></IBSCBS></imposto></det>'
                  for n in "123")
        + "</infNFe></NFe>"
    )
    assert len(roda(doc, regra(**CST_EXISTE))) == 1


# ---- subgrupos_por_indicador ----------------------------------------------

SUBGRUPOS = dict(
    tipo="subgrupos_por_indicador", campo_chave="imposto/IBSCBS/cClassTrib",
    tabela="cst-cclasstrib", coluna="cclasstrib",
    mapa=(("IndReducaoAliq", "imposto/IBSCBS/gIBSCBS/gRed"),),
)


def _com_indicador(valor: bool, indicador: str = "IndReducaoAliq") -> str:
    """Acha na tabela oficial um cClassTrib com o indicador no estado pedido.

    Escolher o código a partir da própria tabela, e não fixá-lo no teste, é o que
    faz este teste continuar significando a mesma coisa quando a tabela mudar.
    """
    tabela = tabelas.cst_cclasstrib()
    for codigo in tabela.classificacoes:
        if tabela.indicadores_de(codigo).get(indicador) is valor:
            return codigo
    raise AssertionError(f"nenhum cClassTrib com {indicador} = {valor} na tabela")


def test_subgrupo_exigido_e_ausente_e_acusado():
    codigo = _com_indicador(True)
    doc = nota(f"<IBSCBS><cClassTrib>{codigo}</cClassTrib></IBSCBS>")
    d = detalhe(doc, regra(**SUBGRUPOS))
    assert f"cClassTrib = '{codigo}' exige imposto/IBSCBS/gIBSCBS/gRed" in d
    assert "ausente" in d


def test_subgrupo_exigido_e_presente_passa():
    codigo = _com_indicador(True)
    doc = nota(
        f"<IBSCBS><cClassTrib>{codigo}</cClassTrib>"
        f"<gIBSCBS><gRed><pRedAliq>30.00</pRedAliq></gRed></gIBSCBS></IBSCBS>"
    )
    assert roda(doc, regra(**SUBGRUPOS)) == []


def test_subgrupo_vedado_e_presente_e_acusado():
    codigo = _com_indicador(False)
    doc = nota(
        f"<IBSCBS><cClassTrib>{codigo}</cClassTrib>"
        f"<gIBSCBS><gRed/></gIBSCBS></IBSCBS>"
    )
    assert "não admite imposto/IBSCBS/gIBSCBS/gRed" in detalhe(doc, regra(**SUBGRUPOS))


def test_subgrupo_ignora_cclasstrib_fora_da_tabela():
    """Código inexistente é problema da `em_tabela`, não desta regra."""
    doc = nota("<IBSCBS><cClassTrib>999999</cClassTrib></IBSCBS>")
    assert roda(doc, regra(**SUBGRUPOS)) == []


# ---- soma_campos ----------------------------------------------------------

SOMA = dict(
    tipo="soma_campos", campo_total="imposto/IBSCBS/vIBS",
    campos=("imposto/IBSCBS/gIBSUF/vIBSUF", "imposto/IBSCBS/gIBSMun/vIBSMun"),
)


def test_soma_campos_acusa_diferenca():
    doc = nota(
        "<IBSCBS><vIBS>10.00</vIBS>"
        "<gIBSUF><vIBSUF>6.00</vIBSUF></gIBSUF>"
        "<gIBSMun><vIBSMun>3.50</vIBSMun></gIBSMun></IBSCBS>"
    )
    d = detalhe(doc, regra(**SOMA))
    assert "imposto/IBSCBS/vIBS = 10.00" in d and "= 9.50" in d and "diferença de 0.50" in d


def test_soma_campos_aceita_arredondamento_dentro_da_tolerancia():
    doc = nota(
        "<IBSCBS><vIBS>10.00</vIBS>"
        "<gIBSUF><vIBSUF>6.00</vIBSUF></gIBSUF>"
        "<gIBSMun><vIBSMun>4.005</vIBSMun></gIBSMun></IBSCBS>"
    )
    assert roda(doc, regra(**SOMA)) == []


def test_soma_campos_ignora_parcela_ausente():
    """Grupo incompleto não é erro de aritmética. Diagnóstico errado é ruído."""
    doc = nota("<IBSCBS><vIBS>10.00</vIBS><gIBSUF><vIBSUF>6.00</vIBSUF></gIBSUF></IBSCBS>")
    assert roda(doc, regra(**SOMA)) == []


def test_soma_campos_compara_como_decimal():
    doc = nota(
        "<IBSCBS><vIBS>10.0000</vIBS>"
        "<gIBSUF><vIBSUF>6.00</vIBSUF></gIBSUF>"
        "<gIBSMun><vIBSMun>4.000</vIBSMun></gIBSMun></IBSCBS>"
    )
    assert roda(doc, regra(**SOMA)) == []


# ---- exclusivo ------------------------------------------------------------

EXCLUSIVO = dict(
    tipo="exclusivo",
    campos=("imposto/IBSCBS/gIBSCBS", "imposto/IBSCBS/gIBSCBSMono", "imposto/IBSCBS/gTransfCred"),
)


def test_exclusivo_acusa_dois_ramos_presentes():
    doc = nota("<IBSCBS><gIBSCBS/><gIBSCBSMono/></IBSCBS>")
    assert detalhe(doc, regra(**EXCLUSIVO)) == (
        "item 1: presentes ao mesmo tempo: imposto/IBSCBS/gIBSCBS, imposto/IBSCBS/gIBSCBSMono"
    )


def test_exclusivo_aprova_um_ramo_so():
    assert roda(nota("<IBSCBS><gIBSCBS/></IBSCBS>"), regra(**EXCLUSIVO)) == []


def test_exclusivo_aprova_nenhum_ramo():
    assert roda(nota("<IBSCBS/>"), regra(**EXCLUSIVO)) == []


# ---- valor_numerico_em ----------------------------------------------------

ALIQUOTA = dict(tipo="valor_numerico_em", campo="imposto/IBSCBS/pIBSUF", valores=("0.10",))


def test_valor_numerico_acusa_aliquota_diferente():
    doc = nota("<IBSCBS><pIBSUF>0.1500</pIBSUF></IBSCBS>")
    assert detalhe(doc, regra(**ALIQUOTA)) == (
        "item 1: imposto/IBSCBS/pIBSUF = 0.1500, esperado 0.10"
    )


@pytest.mark.parametrize("escrito", ["0.10", "0.1000", "0.100", ".10", "0.1"])
def test_mesma_aliquota_em_escalas_diferentes_nunca_gera_achado(escrito):
    """O emissor escolhe a escala decimal. Reprovar por isso seria acusar errado."""
    doc = nota(f"<IBSCBS><pIBSUF>{escrito}</pIBSUF></IBSCBS>")
    assert roda(doc, regra(**ALIQUOTA)) == []


def test_valor_numerico_ignora_campo_ausente_ou_nao_numerico():
    assert roda(nota("<IBSCBS/>"), regra(**ALIQUOTA)) == []
    assert roda(nota("<IBSCBS><pIBSUF>zero</pIBSUF></IBSCBS>"), regra(**ALIQUOTA)) == []


# ---- configuração: erro de regra aparece no carregamento ------------------

def escreve(tmp_path: Path, regra_bruta: dict) -> Path:
    caminho = tmp_path / "nfe" / "t.yaml"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    completa = {"id": "t1", "mensagem": "m", "acao": "a", **regra_bruta}
    caminho.write_text(
        yaml.safe_dump({"grupo": "t", "regras": [completa]}, allow_unicode=True),
        encoding="utf-8",
    )
    return tmp_path


def test_campo_obrigatorio_do_tipo_e_cobrado(tmp_path):
    raiz = escreve(tmp_path, {"tipo": "prefixo_de", "campo": "a"})
    with pytest.raises(ValueError, match="exige o campo 'campo_referencia'"):
        carrega(raiz=raiz)


def test_tabela_inexistente_e_recusada(tmp_path):
    raiz = escreve(tmp_path, {
        "tipo": "em_tabela", "campo": "a", "tabela": "inventada", "coluna": "cst",
    })
    with pytest.raises(ValueError, match="tabela 'inventada' não existe"):
        carrega(raiz=raiz)


def test_coluna_inexistente_e_recusada(tmp_path):
    raiz = escreve(tmp_path, {
        "tipo": "em_tabela", "campo": "a", "tabela": "cst-cclasstrib", "coluna": "cor",
    })
    with pytest.raises(ValueError, match="coluna 'cor' não existe"):
        carrega(raiz=raiz)


def test_indicador_inexistente_no_mapa_e_recusado(tmp_path):
    """Regra que nunca dispara porque o indicador foi digitado errado é pior que
    regra que falha alto no carregamento."""
    raiz = escreve(tmp_path, {
        "tipo": "subgrupos_por_indicador", "campo_chave": "a",
        "tabela": "cst-cclasstrib", "coluna": "cclasstrib",
        "mapa": {"IndReducaoAliquota": "gRed"},
    })
    with pytest.raises(ValueError, match="indicador 'IndReducaoAliquota' não existe"):
        carrega(raiz=raiz)


def test_filtro_inexistente_e_recusado(tmp_path):
    raiz = escreve(tmp_path, {
        "tipo": "em_tabela", "campo": "a", "tabela": "cst-cclasstrib",
        "coluna": "cst", "filtro": "por_uf",
    })
    with pytest.raises(ValueError, match="filtro 'por_uf' não existe"):
        carrega(raiz=raiz)


def test_valor_nao_numerico_em_valor_numerico_em_e_recusado(tmp_path):
    raiz = escreve(tmp_path, {
        "tipo": "valor_numerico_em", "campo": "a", "valores": ["dez por cento"],
    })
    with pytest.raises(ValueError, match="não é número"):
        carrega(raiz=raiz)
