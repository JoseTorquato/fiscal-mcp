"""Leitura de XML de NF-e: do documento bruto para uma estrutura navegável.

Duas responsabilidades, e só:
  1. desembrulhar o XML (nfeProc, NFe, com ou sem namespace);
  2. expor caminhos e valores para o motor de regras e para o resumo.

Não valida — quem valida é `regras.py`. Não conhece regra fiscal.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import ClassVar

from lxml import etree

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


class XmlInvalido(Exception):
    """XML malformado ou que não é o documento fiscal esperado."""


class DocumentoNaoSuportado(XmlInvalido):
    """É um documento fiscal reconhecível, mas de um tipo ainda não suportado.

    Existe como tipo próprio para quem chama não precisar casar mensagem de
    erro por texto — o que já quebrou uma vez.
    """

    def __init__(self, mensagem: str, sigla: str) -> None:
        super().__init__(mensagem)
        self.sigla = sigla


# Outros documentos fiscais que chegam aqui por engano. Dizer "não é NF-e" é
# tecnicamente certo e inútil: quem mandou um XML fiscal merece saber o que
# mandou e o que esperar.
OUTROS_DOCUMENTOS = {
    "NFSe": ("NFS-e", "nota fiscal de serviço, padrão nacional"),
    "infNFSe": ("NFS-e", "nota fiscal de serviço, padrão nacional"),
    "DPS": ("DPS", "declaração de prestação de serviços, que origina a NFS-e"),
    "CTe": ("CT-e", "conhecimento de transporte eletrônico"),
    "infCte": ("CT-e", "conhecimento de transporte eletrônico"),
    "MDFe": ("MDF-e", "manifesto eletrônico de documentos fiscais"),
    "infMDFe": ("MDF-e", "manifesto eletrônico de documentos fiscais"),
    "ConsultaNFSeResposta": ("NFS-e", "resposta de consulta de NFS-e"),
}


def _levanta_diagnostico(arvore: etree._Element) -> None:
    """Levanta o erro mais informativo possível sobre o que o arquivo é."""
    nomes = {_sem_ns(e.tag) for e in arvore.iter() if isinstance(e.tag, str)}
    for marcador, (sigla, descricao) in OUTROS_DOCUMENTOS.items():
        if marcador in nomes:
            raise DocumentoNaoSuportado(
                f"este arquivo é um {sigla} ({descricao}), não uma NF-e. "
                f"O fiscal-mcp ainda valida apenas NF-e e NFC-e (modelos 55 e 65) — "
                f"suporte a {sigla} está no roadmap.",
                sigla=sigla,
            )
    raise XmlInvalido("não encontrei o elemento infNFe — isto não parece um XML de NF-e")


def _sem_ns(tag) -> str:
    """Nome do elemento sem o namespace.

    Comentário e instrução de processamento têm `.tag` como função no lxml, não
    string — e XML de NF-e vem com comentário mais vezes do que se espera.
    """
    if not isinstance(tag, str):
        return ""
    return tag.split("}", 1)[-1] if "}" in tag else tag


@dataclass
class Navegavel:
    """Navegação genérica sobre XML fiscal, compartilhada por NF-e e NFS-e.

    Só sabe andar na árvore e ler valor. Não conhece regra fiscal nem leiaute
    de documento — quem conhece são as subclasses e o motor de regras.
    """

    arvore: etree._Element
    raiz: etree._Element

    # atributos de classe, não campos: cada documento fixa o seu namespace
    ns: ClassVar[dict[str, str]] = {}
    prefixo: ClassVar[str] = ""

    @staticmethod
    def _parse(xml: str | bytes) -> etree._Element:
        if isinstance(xml, str):
            xml = xml.encode("utf-8")
        try:
            # resolve_entities=False evita XXE — XML fiscal vem de terceiro
            parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
            return etree.fromstring(xml, parser=parser)
        except etree.XMLSyntaxError as exc:
            raise XmlInvalido(f"XML malformado: {exc}") from exc

    def elemento(self, caminho: str, de: etree._Element | None = None) -> etree._Element | None:
        atual = de if de is not None else self.raiz
        for parte in caminho.split("/"):
            if atual is None:
                return None
            achado = atual.find(f"{self.prefixo}:{parte}", self.ns)
            if achado is None:
                achado = next((f for f in atual if _sem_ns(f.tag) == parte), None)
            atual = achado
        return atual

    def texto(self, caminho: str, de: etree._Element | None = None) -> str | None:
        elemento = self.elemento(caminho, de)
        return elemento.text.strip() if elemento is not None and elemento.text else None

    def existe(self, caminho: str, de: etree._Element | None = None) -> bool:
        return self.elemento(caminho, de) is not None

    def decimal(self, caminho: str, de: etree._Element | None = None) -> Decimal | None:
        bruto = self.texto(caminho, de)
        if bruto is None:
            return None
        try:
            return Decimal(bruto)
        except InvalidOperation:
            return None


@dataclass
class Documento(Navegavel):
    """Um documento fiscal carregado. `raiz` é o elemento `infNFe`."""

    ns: ClassVar[dict[str, str]] = NS
    prefixo: ClassVar[str] = "nfe"

    @classmethod
    def de_texto(cls, xml: str | bytes) -> "Documento":
        arvore = cls._parse(xml)
        raiz = arvore.find(".//nfe:infNFe", NS)
        if raiz is None:  # sem namespace declarado
            raiz = next((e for e in arvore.iter() if _sem_ns(e.tag) == "infNFe"), None)
        if raiz is None:
            _levanta_diagnostico(arvore)
        return cls(arvore=arvore, raiz=raiz)

    @property
    def itens(self) -> list[etree._Element]:
        achados = self.raiz.findall("nfe:det", NS)
        return achados or [f for f in self.raiz if _sem_ns(f.tag) == "det"]

    @property
    def chave(self) -> str | None:
        """Chave de acesso, do atributo Id do infNFe (vem prefixada por 'NFe')."""
        ident = self.raiz.get("Id") or ""
        digitos = "".join(c for c in ident if c.isdigit())
        return digitos or None

    @property
    def versao(self) -> str | None:
        return self.raiz.get("versao")

    @property
    def autorizada(self) -> bool:
        """Tem protocolo de autorização? XML sem protocolo ainda não foi autorizado."""
        return any(_sem_ns(e.tag) == "protNFe" for e in self.arvore.iter())

    # ---- resumo -----------------------------------------------------------

    def resumo(self) -> dict:
        """Estrutura enxuta, feita para caber no contexto de um agente.

        O XML inteiro de uma nota com muitos itens estoura contexto à toa; por
        isso os itens vêm resumidos e limitados.
        """
        itens = []
        for det in self.itens[:50]:
            itens.append({
                "n": det.get("nItem"),
                "codigo": self.texto("prod/cProd", det),
                "descricao": self.texto("prod/xProd", det),
                "ncm": self.texto("prod/NCM", det),
                "cfop": self.texto("prod/CFOP", det),
                "quantidade": self.texto("prod/qCom", det),
                "valor": self.texto("prod/vProd", det),
            })

        return {
            "chave": self.chave,
            "versao_leiaute": self.versao,
            "autorizada": self.autorizada,
            "identificacao": {
                "modelo": self.texto("ide/mod"),
                "serie": self.texto("ide/serie"),
                "numero": self.texto("ide/nNF"),
                "emissao": self.texto("ide/dhEmi"),
                "natureza_operacao": self.texto("ide/natOp"),
                "tipo": self.texto("ide/tpNF"),
                "ambiente": {"1": "producao", "2": "homologacao"}.get(
                    self.texto("ide/tpAmb") or "", self.texto("ide/tpAmb")
                ),
            },
            "emitente": {
                "cnpj": self.texto("emit/CNPJ"),
                "nome": self.texto("emit/xNome"),
                "uf": self.texto("emit/enderEmit/UF"),
            },
            "destinatario": {
                # CPF/CNPJ do destinatário é dado pessoal: só o indicador de
                # presença por padrão. Ver spec 03 (minimização, LGPD).
                "identificado": self.existe("dest/CNPJ") or self.existe("dest/CPF"),
                "nome": self.texto("dest/xNome"),
                "uf": self.texto("dest/enderDest/UF"),
            },
            "totais": {
                "produtos": self.texto("total/ICMSTot/vProd"),
                "nota": self.texto("total/ICMSTot/vNF"),
                "icms": self.texto("total/ICMSTot/vICMS"),
                "desconto": self.texto("total/ICMSTot/vDesc"),
                "frete": self.texto("total/ICMSTot/vFrete"),
            },
            "quantidade_itens": len(self.itens),
            "itens": itens,
            "itens_omitidos": max(0, len(self.itens) - 50),
        }
