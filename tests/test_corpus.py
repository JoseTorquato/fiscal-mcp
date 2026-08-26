"""Validação contra o corpus de amostras MIT da `nfelib`.

As fixtures deste repositório foram escritas por quem escreveu as regras — o que
significa que elas provam consistência interna, não ausência de falso positivo.
Este arquivo roda o validador inteiro contra documentos de **formato real**, que
ninguém aqui escreveu, e verifica as duas coisas que um falso positivo quebraria.

Não substitui rodar contra nota real de contribuinte, que continua sendo a
contribuição mais valiosa que este projeto pode receber. Mas pega a classe de
erro mais comum: regra que parece certa contra XML sintético e acusa errado
contra documento de verdade.

As amostras vêm da `nfelib` (MIT) e só existem com o extra `[xsd]` instalado.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_mcp import schema  # noqa: E402
from fiscal_mcp.validador import valida_nfe  # noqa: E402

precisa_do_extra = pytest.mark.skipif(
    not schema.disponivel(), reason="extra [xsd] não instalado"
)

# Regras que consultam a tabela oficial. São as mais perigosas do repositório:
# um erro no mapeamento faria a ferramenta reprovar nota correta de todo mundo
# que usa aquele CST. Nenhuma delas pode disparar contra documento de formato
# real — se disparar, o problema é nosso, não do documento.
REGRAS_DE_TABELA = {
    "ibs-cst-existe",
    "ibs-cclasstrib-existe",
    "ibs-cclasstrib-modelo",
    "ibs-cclasstrib-prefixo-cst",
}


def amostras() -> list[Path]:
    """O corpus, ou lista vazia sem o extra.

    O `parametrize` chama isto na COLETA, antes de qualquer skipif rodar — se
    aqui estourasse ImportError, a suíte inteira quebraria na instalação sem o
    extra, que é justamente o cenário que o CI precisa exercitar.
    """
    try:
        import nfelib
    except ImportError:
        return []
    base = Path(nfelib.__file__).parent / "nfe" / "samples" / "v4_0" / "leiauteNFe"
    return sorted(base.glob("*.xml"))


@precisa_do_extra
def test_o_corpus_existe():
    assert len(amostras()) >= 10, "corpus pequeno demais para significar alguma coisa"


@precisa_do_extra
@pytest.mark.parametrize("caminho", amostras(), ids=lambda p: p.stem[:28])
def test_nenhuma_regra_de_tabela_acusa_documento_de_formato_real(caminho):
    """A falha que destruiria a confiança de forma irreversível.

    CST e cClassTrib vêm da tabela oficial embarcada. Se o mapeamento estiver
    errado, a ferramenta reprova nota correta — e validador que faz isso é
    desinstalado no mesmo dia e não volta.
    """
    r = valida_nfe(caminho.read_text(encoding="utf-8", errors="replace"), incluir_resumo=False)
    acusadas = {
        a["id"] for a in r["achados"]
        if a["severidade"] == "erro" and a["id"] in REGRAS_DE_TABELA
    }
    assert not acusadas, f"{caminho.name}: {acusadas}"


@precisa_do_extra
@pytest.mark.parametrize("caminho", amostras(), ids=lambda p: p.stem[:28])
def test_nao_inventamos_erro_de_schema(caminho):
    """Se o XSD aprova o documento, nossa camada não pode reprovar.

    Divergir do próprio validador que estamos usando significaria bug na
    tradução ou no rebaixamento por versão — e falso positivo em schema é pior
    que em regra, porque parece autoritativo.
    """
    from lxml import etree

    xml = caminho.read_text(encoding="utf-8", errors="replace")
    arvore = etree.fromstring(
        xml.encode("utf-8"), etree.XMLParser(no_network=True, resolve_entities=False)
    )
    raiz = etree.QName(arvore).localname
    valido_para_o_lxml = schema._esquema(raiz).validate(etree.ElementTree(arvore))
    if not valido_para_o_lxml:
        pytest.skip("a amostra não passa no XSD oficial; não é caso para este teste")

    erros = [
        a for a in schema.valida(xml)
        if a["severidade"] == "erro" and a["grupo"] == "schema"
    ]
    assert not erros, f"{caminho.name}: {erros}"


@precisa_do_extra
def test_a_maioria_do_corpus_passa_limpa():
    """Medida grossa, mas é a que denuncia regressão ampla.

    Quando este número cair, alguma regra passou a acusar em massa. As amostras
    que legitimamente falham são poucas e conhecidas: uma é inválida no schema
    de propósito e outra tem valores de preenchimento incoerentes entre si
    (vIBS = 0 com vIBSUF = 16, vProd de 14,88 contra total de 158.106,35) — a
    aritmética delas é ruído de amostra, não erro nosso.
    """
    limpas = 0
    sujas: dict[str, list[str]] = {}
    for caminho in amostras():
        r = valida_nfe(caminho.read_text(encoding="utf-8", errors="replace"), incluir_resumo=False)
        erros = [a["id"] for a in r["achados"] if a["severidade"] == "erro"]
        if erros:
            sujas[caminho.name] = erros
        else:
            limpas += 1
    total = len(amostras())
    assert limpas >= total - 2, f"{limpas}/{total} limpas; falharam: {sujas}"
