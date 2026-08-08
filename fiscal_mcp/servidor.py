"""Servidor MCP — a camada fina sobre o núcleo.

Toda a lógica vive em `validador.py`, `chave.py` e `rejeicoes.py`, que não
importam nada de MCP. Aqui só se declara a superfície que o agente enxerga.

⚠️ Fatia zero: nenhuma ferramenta aqui assina, transmite, emite ou cancela
documento. Tudo roda offline, sem certificado. Ver
docs/adr/0010-fatia-zero-sem-credencial.md.

    fiscal-mcp-servidor          # stdio, para configurar num cliente MCP
"""

from __future__ import annotations

import json

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from . import __version__, rejeicoes
from .chave import analisa as _analisa_chave
from .nfse import analisa_chave as _analisa_chave_nfse
from .validador import explica_nfe as _explica_nfe
from .validador import explica_nfse as _explica_nfse
from .validador import valida_nfe as _valida_nfe
from .validador import valida_nfse as _valida_nfse

mcp = MCPServer(
    name="fiscal-mcp",
    version=__version__,
    instructions=(
        "Ferramentas para validar e ler documentos fiscais brasileiros offline. "
        "NENHUMA delas assina, transmite, emite ou cancela documento — não há como "
        "causar efeito fiscal por aqui. Validação local não substitui a validação "
        "da SEFAZ nem garante autorização."
    ),
)

# Todas as ferramentas desta fatia são leitura pura: sem rede, sem credencial,
# sem efeito colateral. Declarar isso no protocolo permite que o cliente trate
# as chamadas como seguras.
SO_LEITURA = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


def _json(dados: dict) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2)


@mcp.tool(annotations=SO_LEITURA)
def validar_nfe(xml: str, incluir_resumo: bool = True) -> str:
    """Valida um XML de NF-e localmente, sem transmitir nada.

    Somente leitura. Sem efeito fiscal — não assina, não emite, não envia à SEFAZ.

    Confere estrutura mínima, coerência dos totais com os itens, formato dos
    campos e o dígito verificador da chave de acesso. Também sinaliza os campos
    de IBS e CBS, obrigatórios desde 03/08/2026.

    Cada achado traz severidade, o que está errado e o que fazer. Passar aqui
    não garante autorização pela SEFAZ: é validação local, feita para evitar
    gastar uma transmissão com erro previsível.

    Args:
        xml: conteúdo do XML da NF-e.
        incluir_resumo: inclui o resumo do documento junto do resultado.
    """
    return _json(_valida_nfe(xml, incluir_resumo=incluir_resumo))


@mcp.tool(annotations=SO_LEITURA)
def explicar_nfe(xml: str) -> str:
    """Interpreta um XML de NF-e e devolve um resumo estruturado.

    Somente leitura. Sem efeito fiscal.

    Devolve identificação, emitente, totais e itens em formato enxuto, em vez do
    XML inteiro — que estoura contexto sem necessidade. Documento e nome do
    destinatário são omitidos por minimização de dado pessoal; o resumo informa
    apenas se há destinatário identificado.

    Args:
        xml: conteúdo do XML da NF-e.
    """
    return _json(_explica_nfe(xml))


@mcp.tool(annotations=SO_LEITURA)
def validar_nfse(xml: str, incluir_resumo: bool = True) -> str:
    """Valida uma NFS-e do padrão nacional localmente, sem transmitir nada.

    Somente leitura. Sem efeito fiscal.

    Cobre a NFS-e do padrão nacional (namespace sped.fazenda.gov.br/nfse):
    estrutura, campos obrigatórios da DPS embutida, dados do prestador, código
    de tributação e composição da chave de 50 dígitos.

    NÃO cobre padrões municipais próprios. Não verifica dígito verificador — o
    algoritmo da NFS-e nacional ainda não foi confirmado — nem valida a
    assinatura digital.

    Args:
        xml: conteúdo do XML da NFS-e.
        incluir_resumo: inclui o resumo do documento junto do resultado.
    """
    return _json(_valida_nfse(xml, incluir_resumo=incluir_resumo))


@mcp.tool(annotations=SO_LEITURA)
def explicar_nfse(xml: str) -> str:
    """Interpreta uma NFS-e do padrão nacional e devolve resumo estruturado.

    Somente leitura. Sem efeito fiscal.

    Traz identificação, locais de emissão e incidência, prestador, serviço e
    valores. Documento e nome do tomador são omitidos por minimização de dado
    pessoal; o resumo informa apenas se há tomador identificado.

    Args:
        xml: conteúdo do XML da NFS-e.
    """
    return _json(_explica_nfse(xml))


@mcp.tool(annotations=SO_LEITURA)
def validar_chave_nfse(chave: str) -> str:
    """Analisa a chave de 50 dígitos de uma NFS-e do padrão nacional.

    Somente leitura. Sem efeito fiscal.

    Decompõe as posições confirmadas contra documento real: código IBGE do
    município emissor, CNPJ do prestador, número e mês de emissão. NÃO verifica
    dígito verificador, porque o algoritmo ainda não foi confirmado.

    Para chave de NF-e (44 dígitos), use validar_chave_acesso.

    Args:
        chave: os 50 dígitos, com ou sem separadores.
    """
    return _json(_analisa_chave_nfse(chave))


@mcp.tool(annotations=SO_LEITURA)
def explicar_rejeicao(codigo_ou_mensagem: str) -> str:
    """Traduz um código de rejeição da SEFAZ em significado e ação.

    Somente leitura. Sem efeito fiscal.

    Aceita o código puro ("539") ou a mensagem completa ("Rejeicao: 539 - ...").
    Devolve o que aconteceu, o que fazer e se a situação é reversível.

    Atenção ao campo `reversivel`: rejeição por denegação (301, 302) NÃO se
    resolve reemitindo.

    Args:
        codigo_ou_mensagem: o código de três dígitos ou a mensagem da SEFAZ.
    """
    return _json(rejeicoes.explica(codigo_ou_mensagem))


@mcp.tool(annotations=SO_LEITURA)
def validar_chave_acesso(chave: str) -> str:
    """Analisa uma chave de acesso de 44 dígitos e confere o dígito verificador.

    Somente leitura. Sem efeito fiscal.

    Decompõe a chave em UF, data de emissão, CNPJ do emitente, modelo, série e
    número, e verifica o dígito por módulo 11. Aceita a chave com espaços ou
    formatada em grupos, como aparece no DANFE.

    Args:
        chave: os 44 dígitos, com ou sem separadores.
    """
    return _json(_analisa_chave(chave))


@mcp.tool(annotations=SO_LEITURA)
def listar_rejeicoes_conhecidas() -> str:
    """Lista os códigos de rejeição presentes no catálogo.

    Somente leitura. Útil para o agente saber o que consegue traduzir antes de
    perguntar.
    """
    catalogo = rejeicoes.listar()
    return _json({
        "total": len(catalogo),
        "rejeicoes": catalogo,
        "nota": (
            "Catálogo parcial, com as rejeições mais frequentes em integração nova. "
            "Código ausente não significa que não exista."
        ),
    })


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
