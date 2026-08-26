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

Toda regra tem um **escopo**: `documento` (o padrão, avaliado uma vez na raiz)
ou `item`, avaliado uma vez por `det`, com os caminhos relativos ao item. O
grosso do leiaute de IBS/CBS é por item — ver docs/spec/05-camada-a-ibs-cbs.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml
from lxml import etree

from .documento import Documento

RAIZ_REGRAS = Path(__file__).resolve().parent / "regras"
if not RAIZ_REGRAS.is_dir():  # repositório clonado, não instalado
    RAIZ_REGRAS = Path(__file__).resolve().parent.parent / "regras"

SEVERIDADES = ("erro", "aviso", "informacao")
ESCOPOS = ("documento", "item")


@dataclass(frozen=True)
class Vigencia:
    """Quando a regra passa a valer e quando ela precisa ser reavaliada.

    Substitui o antigo `status: pendente_confirmacao`, que era honesto e não
    tinha saída — nada obrigava a revisitar. `reavaliar_em` é data concreta, e
    um teste falha quando ela passa: a manutenção deixa de depender de memória
    e vira evidência pública. Ver docs/spec/04-manutencao.md.
    """

    desde: str = ""
    reavaliar_em: str = ""
    fonte: str = ""
    observacao: str = ""

    def para_dict(self) -> dict:
        pares = (
            ("desde", self.desde),
            ("reavaliar_em", self.reavaliar_em),
            ("fonte", self.fonte),
            ("observacao", self.observacao.strip()),
        )
        return {chave: valor for chave, valor in pares if valor}


@dataclass(frozen=True)
class Regra:
    id: str
    tipo: str
    severidade: str
    mensagem: str
    grupo: str
    acao: str = ""
    escopo: str = "documento"
    """documento | item — ver ESCOPOS."""
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
    vigencia: Vigencia | None = None


@dataclass
class Alvo:
    """O que uma regra enxerga quando é avaliada.

    Escopo `documento`: a raiz do documento. Escopo `item`: um `det`, com os
    caminhos relativos a ele. Os executores não precisam saber qual dos dois é
    — é o que mantém os tipos de regra iguais nos dois escopos.
    """

    doc: Documento
    base: etree._Element | None = None
    item: str | None = None
    """Número do item (`nItem`), quando o alvo é um `det`."""

    def texto(self, campo: str) -> str | None:
        return self.doc.texto(campo, self.base)

    def existe(self, campo: str) -> bool:
        return self.doc.existe(campo, self.base)

    def decimal(self, campo: str):
        return self.doc.decimal(campo, self.base)

    @property
    def itens(self) -> list["Alvo"]:
        """Um alvo por `det`. Documento sem itens (NFS-e) devolve lista vazia.

        O número vem do atributo `nItem`, não do índice: nota com numeração
        não sequencial existe, e apontar "item 3" para o que a nota chama de
        item 7 manda quem lê procurar no lugar errado.
        """
        dets = getattr(self.doc, "itens", [])
        return [
            Alvo(self.doc, det, det.get("nItem") or str(posicao))
            for posicao, det in enumerate(dets, start=1)
        ]


@dataclass
class Achado:
    regra: Regra
    detalhe: str = ""
    item: str | None = None

    def para_dict(self) -> dict:
        d = {
            "id": self.regra.id,
            "severidade": self.regra.severidade,
            "grupo": self.regra.grupo,
            "problema": self.regra.mensagem,
        }
        if self.item:
            d["item"] = self.item
        if self.detalhe:
            d["detalhe"] = f"item {self.item}: {self.detalhe}" if self.item else self.detalhe
        if self.regra.acao:
            d["acao"] = self.regra.acao
        if self.regra.referencia:
            d["referencia"] = self.regra.referencia
        if self.regra.vigencia:
            d["vigencia"] = self.regra.vigencia.para_dict()
        return d


def _data(valor, onde: str) -> str:
    """Data ISO como string. `yaml` já devolve `date` quando não está entre aspas."""
    if valor in (None, ""):
        return ""
    if isinstance(valor, date):
        return valor.isoformat()
    try:
        return date.fromisoformat(str(valor)).isoformat()
    except ValueError as exc:
        raise ValueError(f"{onde} = '{valor}' não é data ISO (AAAA-MM-DD)") from exc


def _vigencia(bruto: dict, onde: str) -> Vigencia | None:
    dados = bruto.get("vigencia")
    if dados is None:
        return None
    if not isinstance(dados, dict):
        raise ValueError(f"{onde}: vigencia precisa ser um bloco, não '{dados}'")
    return Vigencia(
        desde=_data(dados.get("desde"), f"{onde}: vigencia.desde"),
        reavaliar_em=_data(dados.get("reavaliar_em"), f"{onde}: vigencia.reavaliar_em"),
        fonte=str(dados.get("fonte", "") or ""),
        observacao=str(dados.get("observacao", "") or ""),
    )


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
            escopo = bruto.get("escopo", "documento")
            if escopo not in ESCOPOS:
                raise ValueError(
                    f"{arquivo}: escopo '{escopo}' inválido em '{rid}' — use um de {list(ESCOPOS)}"
                )
            if "status" in bruto:
                raise ValueError(
                    f"{arquivo}: '{rid}' ainda usa 'status'. Substitua pelo bloco "
                    f"'vigencia' com reavaliar_em — ver docs/spec/05-camada-a-ibs-cbs.md §5.4"
                )
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
                escopo=escopo,
                vigencia=_vigencia(bruto, f"{arquivo}: {rid}"),
            ))
    return regras


# ---- execução dos tipos ---------------------------------------------------
#
# Todo executor recebe um `Alvo`, não o documento: é o que faz o mesmo tipo de
# regra valer para o documento inteiro e para um item, sem código duplicado.

def _existe(alvo: Alvo, r: Regra) -> str | None:
    for campo in (r.campos or (r.campo,)):
        if not alvo.existe(campo):
            return f"ausente: {campo}"
    return None


def _nao_vazio(alvo: Alvo, r: Regra) -> str | None:
    for campo in (r.campos or (r.campo,)):
        if not (alvo.texto(campo) or "").strip():
            return f"vazio ou ausente: {campo}"
    return None


def _valor_em(alvo: Alvo, r: Regra) -> str | None:
    atual = alvo.texto(r.campo)
    if atual is None:
        return None  # ausência é problema de outra regra
    if atual not in r.valores:
        return f"{r.campo} = '{atual}', esperado um de {list(r.valores)}"
    return None


def _formato(alvo: Alvo, r: Regra) -> str | None:
    atual = alvo.texto(r.campo)
    if atual is None:
        return None
    if not re.fullmatch(r.padrao, atual):
        return f"{r.campo} = '{atual}' não casa com o formato esperado"
    return None


def _soma_itens(alvo: Alvo, r: Regra) -> str | None:
    total = alvo.decimal(r.campo_total)
    if total is None:
        return None
    soma = Decimal("0")
    for item in alvo.itens:
        parcela = item.decimal(r.campo_item)
        if parcela is not None:
            soma += parcela
    diferenca = abs(soma - total)
    if diferenca > Decimal(r.tolerancia):
        return f"soma dos itens = {soma}, {r.campo_total} = {total}, diferença de {diferenca}"
    return None


def _condicional(alvo: Alvo, r: Regra) -> str | None:
    gatilho = alvo.texto(r.quando_campo)
    if gatilho is None or (r.quando_valor and gatilho not in r.quando_valor):
        return None
    for campo in (r.campos or (r.campo,)):
        if not alvo.existe(campo):
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


def _posicao(item: str | None) -> tuple[int, str]:
    """Ordena itens por número quando dá, e por texto quando não dá."""
    if item is None:
        return (-1, "")
    return (int(item), "") if item.isdigit() else (10**9, item)


def aplica(doc: Documento, regras: list[Regra]) -> list[Achado]:
    """Roda todas as regras sobre o documento.

    Uma regra de escopo `item` pode gerar mais de um achado — um por `det`
    que a viola. Quem conta achados conta achados, não regras.
    """
    achados: list[Achado] = []
    for regra in regras:
        executor = EXECUTORES.get(regra.tipo)
        if executor is None:
            raise ValueError(f"tipo de regra desconhecido: '{regra.tipo}' em {regra.id}")
        raiz = Alvo(doc)
        for alvo in (raiz.itens if regra.escopo == "item" else [raiz]):
            detalhe = executor(alvo, regra)
            if detalhe:
                achados.append(Achado(regra=regra, detalhe=detalhe, item=alvo.item))
    ordem = {"erro": 0, "aviso": 1, "informacao": 2}
    return sorted(
        achados,
        key=lambda a: (ordem.get(a.regra.severidade, 9), a.regra.id, _posicao(a.item)),
    )
