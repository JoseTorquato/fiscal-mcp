"""NFS-e do padrão nacional.

Estrutura mapeada a partir de uma NFS-e real, versão 1.01, namespace
`http://www.sped.fazenda.gov.br/nfse`.

O documento é aninhado: a NFS-e (emitida pelo sistema) envolve a DPS
(declaração que o prestador enviou). Cada uma tem sua própria chave:

    NFSe
    └── infNFSe            Id com 50 dígitos
        ├── emit           quem emitiu a nota
        ├── valores/vLiq
        └── DPS
            └── infDPS     Id com 42 dígitos
                ├── prest  prestador do serviço
                ├── toma   tomador do serviço
                ├── serv   descrição e código de tributação
                └── valores/trib/tribMun/tribISSQN

Diferente da NF-e, não há itens: uma NFS-e descreve um serviço.
"""

from __future__ import annotations

from typing import ClassVar

from lxml import etree

from .documento import Navegavel, XmlInvalido, _sem_ns

NS = {"nfse": "http://www.sped.fazenda.gov.br/nfse"}

# Posições confirmadas contra uma NFS-e real. O que não está aqui não foi
# confirmado e por isso não é interpretado — inventar decomposição de chave
# fiscal é o tipo de erro que só aparece no cliente.
CHAVE_TAMANHO = 50
CHAVE_MUNICIPIO = (0, 7)
CHAVE_CNPJ = (9, 23)
CHAVE_NUMERO = (27, 36)
CHAVE_AAMM = (36, 40)

DPS_TAMANHO = 42


class DocumentoNFSe(Navegavel):
    """NFS-e do padrão nacional carregada."""

    ns: ClassVar[dict[str, str]] = NS
    prefixo: ClassVar[str] = "nfse"

    @classmethod
    def de_texto(cls, xml: str | bytes) -> "DocumentoNFSe":
        arvore = cls._parse(xml)
        raiz = arvore.find(".//nfse:infNFSe", NS)
        if raiz is None:
            raiz = next((e for e in arvore.iter() if _sem_ns(e.tag) == "infNFSe"), None)
        if raiz is None:
            raise XmlInvalido(
                "não encontrei o elemento infNFSe — isto não parece uma NFS-e do "
                "padrão nacional"
            )
        return cls(arvore=arvore, raiz=raiz)

    @property
    def dps(self) -> etree._Element | None:
        return self.elemento("DPS/infDPS")

    @property
    def chave(self) -> str | None:
        digitos = "".join(c for c in (self.raiz.get("Id") or "") if c.isdigit())
        return digitos or None

    @property
    def chave_dps(self) -> str | None:
        dps = self.dps
        if dps is None:
            return None
        digitos = "".join(c for c in (dps.get("Id") or "") if c.isdigit())
        return digitos or None

    @property
    def versao(self) -> str | None:
        return self.arvore.get("versao") or self.raiz.get("versao")

    def resumo(self) -> dict:
        """Resumo enxuto. Documento e nome do tomador ficam de fora por minimização."""
        dps = self.dps
        return {
            "documento": "NFS-e",
            "padrao": "nacional",
            "versao_leiaute": self.versao,
            "chave": self.chave,
            "chave_dps": self.chave_dps,
            "identificacao": {
                "numero_nfse": self.texto("nNFSe"),
                "numero_dps": self.texto("nDPS", dps),
                "serie_dps": self.texto("serie", dps),
                "emissao": self.texto("dhEmi", dps),
                "competencia": self.texto("dCompet", dps),
                "processamento": self.texto("dhProc"),
                "situacao": self.texto("cStat"),
                "ambiente": {"1": "producao", "2": "homologacao"}.get(
                    self.texto("tpAmb", dps) or "", self.texto("tpAmb", dps)
                ),
            },
            "local": {
                "emissao": self.texto("xLocEmi"),
                "prestacao": self.texto("xLocPrestacao"),
                "incidencia": self.texto("xLocIncid"),
                "codigo_municipio_emissao": self.texto("cLocEmi", dps),
            },
            "prestador": {
                "cnpj": self.texto("prest/CNPJ", dps),
                "nome": self.texto("emit/xNome"),
                "uf": self.texto("emit/enderNac/UF"),
                "simples_nacional": self.texto("prest/regTrib/opSimpNac", dps),
            },
            "tomador": {
                # dado pessoal: só o indicador, nunca o documento
                "identificado": self.existe("toma/CNPJ", dps) or self.existe("toma/CPF", dps),
                "municipio": self.texto("toma/end/endNac/cMun", dps),
            },
            "servico": {
                "codigo_tributacao_nacional": self.texto("serv/cServ/cTribNac", dps),
                "descricao": self.texto("serv/cServ/xDescServ", dps),
                "local_prestacao": self.texto("serv/locPrest/cLocPrestacao", dps),
                "tributacao_nacional": self.texto("xTribNac"),
            },
            "valores": {
                "servico": self.texto("DPS/infDPS/valores/vServPrest/vServ"),
                "liquido": self.texto("valores/vLiq"),
                "retencao_issqn": self.texto("valores/trib/tribMun/tpRetISSQN", dps),
            },
            "assinada": any(_sem_ns(e.tag) == "Signature" for e in self.arvore.iter()),
        }


def analisa_chave(texto: str) -> dict:
    """Analisa a chave de 50 dígitos da NFS-e nacional.

    Interpreta apenas as posições confirmadas contra documento real. Não há
    verificação de dígito verificador aqui: o algoritmo da NFS-e nacional não
    foi confirmado, e chutar isso produziria acusação falsa.
    """
    from .chave import UFS, limpa

    v = limpa(texto)
    if not v:
        return {"ok": False, "erro": "nenhum dígito encontrado no texto informado"}
    if len(v) != CHAVE_TAMANHO:
        return {
            "ok": False,
            "erro": f"a chave tem {len(v)} dígitos, esperados {CHAVE_TAMANHO} para NFS-e",
            "acao": "A NF-e usa 44 dígitos e a NFS-e do padrão nacional usa 50.",
        }

    municipio = v[slice(*CHAVE_MUNICIPIO)]
    uf = UFS.get(municipio[:2])
    ano, mes = v[36:38], v[38:40]
    problemas = []
    if uf is None:
        problemas.append({
            "campo": "codigo_municipio",
            "problema": f"os dois primeiros dígitos ('{municipio[:2]}') não são uma UF válida",
            "acao": "A chave começa pelo código IBGE do município, cujo prefixo é a UF.",
        })
    if not 1 <= int(mes) <= 12:
        problemas.append({
            "campo": "AAMM",
            "problema": f"mês '{mes}' inválido",
            "acao": "As posições 39 e 40 da chave são o mês de emissão, de 01 a 12.",
        })

    return {
        "ok": not problemas,
        "documento": "NFS-e (padrão nacional)",
        "chave": v,
        "codigo_municipio": municipio,
        "uf": uf,
        "cnpj_prestador": v[slice(*CHAVE_CNPJ)],
        "numero": int(v[slice(*CHAVE_NUMERO)]),
        "emissao": f"{mes}/20{ano}",
        "problemas": problemas,
        "nota": (
            "Decomposição baseada nas posições confirmadas contra documento real. "
            "Não há verificação de dígito verificador: o algoritmo da NFS-e "
            "nacional ainda não foi confirmado."
        ),
    }
