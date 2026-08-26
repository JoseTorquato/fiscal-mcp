"""As 14 regras da Camada A de IBS/CBS (spec 05 §6).

Contrato de qualidade: **duas fixtures por regra**. Uma que a regra reprova e
uma que ela aprova. Sem as duas, a regra não entra — regra que só tem fixture de
reprovação pode estar acusando o mundo inteiro, e regra que só tem fixture de
aprovação pode estar morta.

A fixture de aprovação é sempre a mesma: `exemplos/nfe-ibs-cbs.xml`, uma nota
correta e completa. Cada teste de reprovação estraga um pedaço dela. Isso torna
o teste de ausência de falso positivo (`test_nota_correta_passa_sem_nenhum_erro`)
o mais importante do repositório: ele é o que garante que nenhuma das outras
regras acusa quem não fez nada de errado.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_mcp.regras import carrega  # noqa: E402
from fiscal_mcp.validador import valida_nfe  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CORRETA = (RAIZ / "exemplos" / "nfe-ibs-cbs.xml").read_text(encoding="utf-8")


def achados(xml: str, severidade: str | None = None) -> list[dict]:
    r = valida_nfe(xml)
    return [a for a in r["achados"] if severidade is None or a["severidade"] == severidade]


def ids(xml: str, severidade: str | None = None) -> set[str]:
    return {a["id"] for a in achados(xml, severidade)}


def quebra(*trocas: tuple[str, str]) -> str:
    """A nota correta com um pedaço estragado. Falha alto se o alvo não existe."""
    xml = CORRETA
    for de, para in trocas:
        assert de in xml, f"a fixture mudou: '{de}' não está mais no XML"
        xml = xml.replace(de, para, 1)
    return xml


# ---- o teste que mais importa --------------------------------------------

def test_nota_correta_passa_sem_nenhum_erro():
    """Uma nota válida e completa com IBS/CBS não pode gerar UM erro sequer.

    É o teste que sustenta a promessa do projeto. Falso positivo em nota real
    destrói a confiança de forma irreversível: o validador é desinstalado no
    mesmo dia e não volta.
    """
    r = valida_nfe(CORRETA)
    assert r["erros"] == 0, [a["id"] for a in r["achados"] if a["severidade"] == "erro"]
    assert r["ok"]


def test_nota_correta_nao_gera_nem_aviso_de_ibs():
    """Aviso indevido também é ruído. A nota está certa: o laudo fica limpo."""
    assert not [a for a in achados(CORRETA) if a["id"].startswith("ibs-")]


# ---- L-01 · CST existe na tabela oficial ---------------------------------

def test_cst_inexistente_e_reprovado():
    xml = quebra(("<CST>000</CST>", "<CST>999</CST>"))
    assert "ibs-cst-existe" in ids(xml, "erro")


# ---- L-02 · cClassTrib começa pelo CST -----------------------------------

def test_cclasstrib_que_nao_casa_com_o_cst_e_reprovado():
    """O erro mais comum em produção: classificação genérica para todos os itens."""
    xml = quebra(("<cClassTrib>000001</cClassTrib>", "<cClassTrib>200001</cClassTrib>"))
    assert "ibs-cclasstrib-prefixo-cst" in ids(xml, "erro")


# ---- L-03 · cClassTrib existe --------------------------------------------

def test_cclasstrib_inexistente_e_reprovado():
    xml = quebra(
        ("<CST>000</CST>", "<CST>999</CST>"),
        ("<cClassTrib>000001</cClassTrib>", "<cClassTrib>999999</cClassTrib>"),
    )
    assert "ibs-cclasstrib-existe" in ids(xml, "erro")


# ---- L-04 · cClassTrib permitido no modelo -------------------------------

def test_cclasstrib_nao_permitido_no_modelo_e_reprovado():
    """`200001` existe na tabela, mas os indicadores dizem que não vale em NF-e."""
    xml = quebra(
        ("<CST>000</CST>", "<CST>200</CST>"),
        ("<cClassTrib>000001</cClassTrib>", "<cClassTrib>200001</cClassTrib>"),
    )
    achado = [a for a in achados(xml, "erro") if a["id"] == "ibs-cclasstrib-modelo"]
    assert achado, ids(xml, "erro")
    assert "modelo 55" in achado[0]["detalhe"]


# ---- L-05 · subgrupos exigidos pelos indicadores -------------------------

def test_subgrupo_exigido_pela_classificacao_e_acusado_como_aviso():
    """CST 620 é monofásico: a tabela exige gIBSCBSMono, que a fixture não tem."""
    xml = quebra(
        ("<CST>000</CST>", "<CST>620</CST>"),
        ("<cClassTrib>000001</cClassTrib>", "<cClassTrib>620001</cClassTrib>"),
    )
    achado = [a for a in achados(xml) if a["id"] == "ibs-subgrupos-obrigatorios"]
    assert achado, "a regra de subgrupos deveria ter disparado"
    assert achado[0]["severidade"] == "aviso", (
        "L-05 nasce como aviso: promover a erro exige três XMLs reais sem falso positivo"
    )


def test_l05_traz_data_de_reavaliacao():
    """Regra que ainda não estabilizou precisa dizer quando será revista."""
    regra = next(r for r in carrega() if r.id == "ibs-subgrupos-obrigatorios")
    assert regra.vigencia and regra.vigencia.reavaliar_em


# ---- L-06 · vIBS = vIBSUF + vIBSMun --------------------------------------

def test_vibs_que_nao_soma_as_parcelas_e_reprovado():
    xml = quebra(("<vIBS>0.20</vIBS>", "<vIBS>0.50</vIBS>"))
    achado = [a for a in achados(xml, "erro") if a["id"] == "ibs-vibs-soma-uf-mun"]
    assert achado
    assert "diferença de 0.30" in achado[0]["detalhe"]


def test_vibs_tolera_centavo_de_arredondamento():
    """Arredondamento item a item é fonte conhecida de divergência de centavos."""
    xml = quebra(("<vIBSUF>0.20</vIBSUF>", "<vIBSUF>0.21</vIBSUF>"))
    assert "ibs-vibs-soma-uf-mun" not in ids(xml, "erro")


# ---- L-07 · totais batem com a soma dos itens ----------------------------

def test_total_de_ibs_divergente_e_reprovado():
    xml = quebra(("<vIBS>0.25</vIBS>", "<vIBS>9.99</vIBS>"))
    assert "ibs-totais-conferem-ibs" in ids(xml, "erro")


def test_total_de_cbs_divergente_e_reprovado():
    xml = quebra(("<vCBS>2.25</vCBS>", "<vCBS>9.99</vCBS>"))
    assert "ibs-totais-conferem-cbs" in ids(xml, "erro")


# ---- L-08 · um regime por item -------------------------------------------

def test_dois_regimes_no_mesmo_item_e_reprovado():
    xml = quebra(("</gIBSCBS>", "</gIBSCBS><gIBSCBSMono/>"))
    achado = [a for a in achados(xml, "erro") if a["id"] == "ibs-grupo-exclusivo"]
    assert achado
    assert "gIBSCBSMono" in achado[0]["detalhe"]


# ---- L-09 · CST 620 exige o grupo de monofasia ---------------------------

def test_cst_620_sem_grupo_de_monofasia_e_reprovado():
    xml = quebra(
        ("<CST>000</CST>", "<CST>620</CST>"),
        ("<cClassTrib>000001</cClassTrib>", "<cClassTrib>620001</cClassTrib>"),
    )
    assert "ibs-cst-620-exige-mono" in ids(xml, "erro")


# ---- L-10 · item com IBS/CBS exige o grupo de totais ---------------------

def test_item_com_ibs_e_nota_sem_totais_e_reprovado():
    xml = CORRETA[:CORRETA.index("<IBSCBSTot>")] + CORRETA[CORRETA.index("</IBSCBSTot>") + 12:]
    assert "ibs-totais-presentes" in ids(xml, "erro")


def test_nota_sem_ibs_nenhum_nao_exige_totais():
    """Errar para este lado acusaria toda nota que ainda não implantou IBS/CBS."""
    sem_ibs = (RAIZ / "exemplos" / "nfe-valida.xml").read_text(encoding="utf-8")
    assert "ibs-totais-presentes" not in ids(sem_ibs, "erro")


# ---- L-11 · formato de competApur ----------------------------------------

def test_competencia_fora_do_formato_e_reprovada():
    xml = quebra((
        "<gIBSCBS>",
        "<gAjusteCompet><competApur>agosto/2026</competApur></gAjusteCompet><gIBSCBS>",
    ))
    assert "ibs-competapur-formato" in ids(xml, "erro")


@pytest.mark.parametrize("competencia", ["2026-08", "2026-01", "2026-12"])
def test_competencia_valida_passa(competencia):
    xml = quebra((
        "<gIBSCBS>",
        f"<gAjusteCompet><competApur>{competencia}</competApur></gAjusteCompet><gIBSCBS>",
    ))
    assert "ibs-competapur-formato" not in ids(xml, "erro")


# ---- L-12 · escala decimal: a regra saiu, o schema cobre -----------------

def test_escala_decimal_e_responsabilidade_do_schema():
    """A regra de formato escrita à mão tinha falso positivo; o XSD não tem.

    O tipo TDec1302RTC aceita `0` sozinho. A regra exigia sempre duas casas e
    teria reprovado nota válida. Ficou com o schema, que carrega o padrão real.
    """
    assert "ibs-escala-decimal" not in {r.id for r in carrega()}

    # o vBC do IBSCBS, não o do ICMS — a nota tem os dois
    dentro_do_grupo = "<gIBSCBS>\n            <vBC>"
    xml = quebra((dentro_do_grupo + "200.00</vBC>", dentro_do_grupo + "200.0000</vBC>"))
    pegou = [a for a in achados(xml, "erro") if a["grupo"] == "schema"]
    assert pegou, "sem a regra, quem precisa pegar escala errada é o schema"
    assert "200.0000" in pegou[0]["problema"]


# ---- L-13 · enums ---------------------------------------------------------

def test_enum_de_credito_presumido_zfm_fora_do_dominio_e_reprovado():
    """O domínio 0-4 foi conferido no XSD oficial, não extraído de PDF."""
    xml = quebra((
        "</gIBSCBS>",
        "</gIBSCBS><gCredPresIBSZFM><competApur>2026-08</competApur>"
        "<tpCredPresIBSZFM>9</tpCredPresIBSZFM>"
        "<vCredPresIBSZFM>0.00</vCredPresIBSZFM></gCredPresIBSZFM>",
    ))
    assert "ibs-enum-credpres-zfm" in ids(xml, "erro")


@pytest.mark.parametrize("valor", ["0", "1", "2", "3", "4"])
def test_enum_de_credito_presumido_zfm_aceita_o_dominio_do_xsd(valor):
    xml = quebra((
        "</gIBSCBS>",
        f"</gIBSCBS><gCredPresIBSZFM><competApur>2026-08</competApur>"
        f"<tpCredPresIBSZFM>{valor}</tpCredPresIBSZFM>"
        f"<vCredPresIBSZFM>0.00</vCredPresIBSZFM></gCredPresIBSZFM>",
    ))
    assert "ibs-enum-credpres-zfm" not in ids(xml, "erro")


def test_dois_creditos_presumidos_no_mesmo_item_e_reprovado():
    """Segundo choice do grupo, que só o XSD revelou."""
    xml = quebra((
        "</gIBSCBS>",
        "</gIBSCBS><gCredPresOper/><gCredPresIBSZFM/>",
    ))
    assert "ibs-credito-presumido-exclusivo" in ids(xml, "erro")


# ---- L-14 · alíquotas de 2026 (aviso) ------------------------------------

def test_aliquota_estadual_diferente_vira_aviso():
    xml = quebra(("<pIBSUF>0.10</pIBSUF>", "<pIBSUF>0.15</pIBSUF>"))
    achado = [a for a in achados(xml) if a["id"] == "ibs-aliquota-uf-2026"]
    assert achado and achado[0]["severidade"] == "aviso", (
        "a repartição entre parcela estadual e municipal não está confirmada em "
        "fonte oficial — enquanto não estiver, esta regra não pode reprovar"
    )


def test_aliquota_de_cbs_diferente_vira_aviso():
    xml = quebra(("<pCBS>0.90</pCBS>", "<pCBS>1.20</pCBS>"))
    achado = [a for a in achados(xml) if a["id"] == "ibs-aliquota-cbs-2026"]
    assert achado and achado[0]["severidade"] == "aviso"


@pytest.mark.parametrize("escrito", ["0.10", "0.1000", "0.1"])
def test_mesma_aliquota_em_outra_escala_nao_gera_aviso(escrito):
    xml = quebra(("<pIBSUF>0.10</pIBSUF>", f"<pIBSUF>{escrito}</pIBSUF>"))
    assert "ibs-aliquota-uf-2026" not in ids(xml)


# ---- integridade do conjunto ---------------------------------------------

def test_toda_regra_de_ibs_tem_acao_e_referencia():
    for r in carrega():
        if not r.id.startswith("ibs-"):
            continue
        assert r.acao, f"{r.id} sem ação"
        assert r.referencia, f"{r.id} sem referência à fonte"


def test_nenhuma_regra_de_ibs_cita_codigo_de_rejeicao():
    """Nenhum número de rejeição entra sem leitura humana da NT (spec 05 §3).

    Durante a pesquisa, uma extração automatizada do PDF produziu códigos
    inexistentes. Citar número errado é pior que não citar número nenhum.
    """
    import re

    for r in carrega():
        if not r.id.startswith("ibs-"):
            continue
        texto = f"{r.mensagem} {r.acao} {r.referencia}"
        suspeitos = re.findall(r"[Rr]ejei[çc][ãa]o\s+(\d{3,4})", texto)
        assert not suspeitos, f"{r.id} cita código de rejeição não confirmado: {suspeitos}"


def test_as_regras_da_camada_a_estao_todas_presentes():
    esperadas = {
        "ibs-grupo-ausente",
        "ibs-cst-existe", "ibs-cclasstrib-prefixo-cst", "ibs-cclasstrib-existe",
        "ibs-cclasstrib-modelo", "ibs-subgrupos-obrigatorios", "ibs-vibs-soma-uf-mun",
        "ibs-totais-conferem-ibs", "ibs-totais-conferem-cbs", "ibs-grupo-exclusivo",
        "ibs-cst-620-exige-mono", "ibs-totais-presentes", "ibs-competapur-formato",
        "ibs-enum-credpres-zfm",
        "ibs-credito-presumido-exclusivo",
        "ibs-aliquota-uf-2026", "ibs-aliquota-cbs-2026",
    }
    assert {r.id for r in carrega() if r.id.startswith("ibs-")} == esperadas
