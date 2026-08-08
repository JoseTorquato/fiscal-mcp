"""Motor de regras declarativas.

Regra fiscal muda por imposição externa — nota técnica, ato normativo, reforma.
Se cada mudança dessas exigir mexer em código, a manutenção não escala e a
promessa central do produto não se sustenta.

Por isso as regras vivem em YAML (`regras/`) e este módulo só as executa.
Absorver uma nota técnica passa a ser, no caso comum, editar um arquivo de dados.

Tipos de regra suportados:

  existe        elemento precisa estar presente
  nao_vazio     presente e com conteúdo
  valor_em      conteúdo precisa estar num conjunto
  formato       conteúdo precisa casar com uma expressão
  soma_itens    total precisa bater com a soma dos itens, dentro de tolerância
  condicional   se um campo tem certo valor, outro passa a ser obrigatório
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import yaml

from .documento import Documento

RAIZ_REGRAS = Path(__file__).resolve().parent / "regras"
if not RAIZ_REGRAS.is_dir():  # repositório clonado, não instalado
    RAIZ_REGRAS = Path(__file__).resolve().parent.parent / "regras"

SEVERIDADES = ("erro", "aviso", "informacao")


@dataclass(frozen=True)
class Regra:
    id: str
    tipo: str
    severidade: str
    mensagem: str
    grupo: str
    acao: str = ""
    campo: str = ""
    campos: tuple[str, ...] = ()
    valores: tuple[str, ...] = ()
    padrao: str = ""
    campo_item: str = ""
    campo_total: str = ""
    tolerancia: str = "0.01"
    quando_campo: str = ""
    quando_valor: tuple[str, ...] = ()
    referencia: str = ""
    status: str = "vigente"
    """vigente | pendente_confirmacao — ver regras/nfe/ibs-cbs.yaml."""


@dataclass
class Achado:
    regra: Regra
    detalhe: str = ""

    def para_dict(self) -> dict:
        d = {
            "id": self.regra.id,
            "severidade": self.regra.severidade,
            "grupo": self.regra.grupo,
            "problema": self.regra.mensagem,
        }
        if self.detalhe:
            d["detalhe"] = self.detalhe
        if self.regra.acao:
            d["acao"] = self.regra.acao
        if self.regra.referencia:
            d["referencia"] = self.regra.referencia
        if self.regra.status != "vigente":
            d["status_da_regra"] = self.regra.status
        return d


def carrega(raiz: Path | None = None, documento: str = "nfe") -> list[Regra]:
    base = (raiz or RAIZ_REGRAS) / documento
    if not base.is_dir():
        raise FileNotFoundError(f"não encontrei regras em {base}")

    regras: list[Regra] = []
    vistos: dict[str, Path] = {}
    for arquivo in sorted(base.glob("*.yaml")):
        doc = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
        grupo = doc.get("grupo", arquivo.stem)
        for bruto in doc.get("regras", []):
            rid = bruto.get("id")
            if not rid:
                raise ValueError(f"{arquivo}: regra sem id")
            if rid in vistos:
                raise ValueError(f"id duplicado '{rid}' em {arquivo} e {vistos[rid]}")
            vistos[rid] = arquivo
            sev = bruto.get("severidade", "erro")
            if sev not in SEVERIDADES:
                raise ValueError(f"{arquivo}: severidade '{sev}' inválida em '{rid}'")
            regras.append(Regra(
                id=rid,
                tipo=bruto["tipo"],
                severidade=sev,
                mensagem=bruto["mensagem"],
                grupo=grupo,
                acao=bruto.get("acao", ""),
                campo=bruto.get("campo", ""),
                campos=tuple(bruto.get("campos", ()) or ()),
                valores=tuple(str(v) for v in bruto.get("valores", ()) or ()),
                padrao=bruto.get("padrao", ""),
                campo_item=bruto.get("campo_item", ""),
                campo_total=bruto.get("campo_total", ""),
                tolerancia=str(bruto.get("tolerancia", "0.01")),
                quando_campo=bruto.get("quando_campo", ""),
                quando_valor=tuple(str(v) for v in bruto.get("quando_valor", ()) or ()),
                referencia=bruto.get("referencia", ""),
                status=bruto.get("status", "vigente"),
            ))
    return regras


# ---- execução dos tipos ---------------------------------------------------

def _existe(doc: Documento, r: Regra) -> str | None:
    for campo in (r.campos or (r.campo,)):
        if not doc.existe(campo):
            return f"ausente: {campo}"
    return None


def _nao_vazio(doc: Documento, r: Regra) -> str | None:
    for campo in (r.campos or (r.campo,)):
        if not (doc.texto(campo) or "").strip():
            return f"vazio ou ausente: {campo}"
    return None


def _valor_em(doc: Documento, r: Regra) -> str | None:
    atual = doc.texto(r.campo)
    if atual is None:
        return None  # ausência é problema de outra regra
    if atual not in r.valores:
        return f"{r.campo} = '{atual}', esperado um de {list(r.valores)}"
    return None


def _formato(doc: Documento, r: Regra) -> str | None:
    atual = doc.texto(r.campo)
    if atual is None:
        return None
    if not re.fullmatch(r.padrao, atual):
        return f"{r.campo} = '{atual}' não casa com o formato esperado"
    return None


def _soma_itens(doc: Documento, r: Regra) -> str | None:
    total = doc.decimal(r.campo_total)
    if total is None:
        return None
    soma = Decimal("0")
    for det in doc.itens:
        parcela = doc.decimal(r.campo_item, det)
        if parcela is not None:
            soma += parcela
    diferenca = abs(soma - total)
    if diferenca > Decimal(r.tolerancia):
        return f"soma dos itens = {soma}, {r.campo_total} = {total}, diferença de {diferenca}"
    return None


def _condicional(doc: Documento, r: Regra) -> str | None:
    gatilho = doc.texto(r.quando_campo)
    if gatilho is None or (r.quando_valor and gatilho not in r.quando_valor):
        return None
    for campo in (r.campos or (r.campo,)):
        if not doc.existe(campo):
            return f"{r.quando_campo} = '{gatilho}' exige {campo}, que está ausente"
    return None


EXECUTORES = {
    "existe": _existe,
    "nao_vazio": _nao_vazio,
    "valor_em": _valor_em,
    "formato": _formato,
    "soma_itens": _soma_itens,
    "condicional": _condicional,
}


def aplica(doc: Documento, regras: list[Regra]) -> list[Achado]:
    achados: list[Achado] = []
    for regra in regras:
        executor = EXECUTORES.get(regra.tipo)
        if executor is None:
            raise ValueError(f"tipo de regra desconhecido: '{regra.tipo}' em {regra.id}")
        detalhe = executor(doc, regra)
        if detalhe:
            achados.append(Achado(regra=regra, detalhe=detalhe))
    ordem = {"erro": 0, "aviso": 1, "informacao": 2}
    return sorted(achados, key=lambda a: (ordem.get(a.regra.severidade, 9), a.regra.id))
