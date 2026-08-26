"""Motor de regras declarativas.

Regra fiscal muda por imposição externa — nota técnica, ato normativo, reforma.
Se cada mudança dessas exigir mexer em código, a manutenção não escala e a
promessa central do produto não se sustenta.

Por isso as regras vivem em YAML (`regras/`) e este módulo só as executa.
Absorver uma nota técnica passa a ser, no caso comum, editar um arquivo de dados.

Tipos de regra suportados:

  existe                   elemento precisa estar presente
  nao_vazio                presente e com conteúdo
  valor_em                 conteúdo precisa estar num conjunto
  formato                  conteúdo precisa casar com uma expressão
  soma_itens               total precisa bater com a soma dos itens
  condicional              se um campo tem certo valor, outro passa a ser obrigatório
  prefixo_de               campo precisa começar pelo conteúdo de outro campo
  em_tabela                valor precisa existir na tabela oficial embarcada
  subgrupos_por_indicador  indicadores da tabela exigem ou vedam subgrupos
  soma_campos              campo precisa ser a soma de outros campos
  exclusivo                no máximo um dos campos pode estar presente
  valor_numerico_em        valor precisa ser um de uma lista, comparado como número

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
    tolerancia: str = ""
    """Vazio significa "o padrão do tipo" — ver `_tolerancia`."""
    quando_campo: str = ""
    quando_valor: tuple[str, ...] = ()
    campo_referencia: str = ""
    tamanho: int = 0
    tabela: str = ""
    coluna: str = ""
    filtro: str = ""
    campo_chave: str = ""
    mapa: tuple[tuple[str, str], ...] = ()
    """Indicador da tabela oficial → caminho XML. Tupla porque a regra é imutável."""
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

    def _resolve(self, campo: str) -> tuple[str, etree._Element | None]:
        """Caminho iniciado por `/` é absoluto, a partir da raiz do documento.

        Existe porque há regra que precisa dos dois ao mesmo tempo: olhar um
        campo do item e outro fora dele. Sem isso, "item com IBS/CBS exige o
        grupo de totais" só conseguia enxergar o primeiro item da nota.
        """
        if campo.startswith("/"):
            return campo[1:], None
        return campo, self.base

    def texto(self, campo: str) -> str | None:
        caminho, base = self._resolve(campo)
        return self.doc.texto(caminho, base)

    def existe(self, campo: str) -> bool:
        caminho, base = self._resolve(campo)
        return self.doc.existe(caminho, base)

    def decimal(self, campo: str):
        caminho, base = self._resolve(campo)
        return self.doc.decimal(caminho, base)

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


class NaoAvaliavel(Exception):
    """A regra não pôde ser avaliada porque falta o dado de que ela depende.

    Vira achado de `informacao`, nunca de `erro`. Uma regra que dependa da
    tabela oficial e não a encontre está diante de um defeito de instalação, não
    de uma nota errada — reprovar aqui seria a pior falha possível deste
    projeto: acusar quem não fez nada de errado.
    """


@dataclass
class Achado:
    regra: Regra
    detalhe: str = ""
    item: str | None = None
    severidade: str = ""
    """Sobrepõe a severidade da regra. Só o rebaixamento usa isto — ver NaoAvaliavel."""

    def para_dict(self) -> dict:
        d = {
            "id": self.regra.id,
            "severidade": self.severidade or self.regra.severidade,
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


def _mapa(bruto: dict, onde: str) -> tuple[tuple[str, str], ...]:
    dados = bruto.get("mapa")
    if dados is None:
        return ()
    if not isinstance(dados, dict):
        raise ValueError(f"{onde}: mapa precisa ser um bloco de indicador → caminho")
    return tuple((str(k), str(v)) for k, v in sorted(dados.items()))


# Colunas e filtros que o motor sabe consultar. Fechado de propósito: filtro
# arbitrário viraria código escondido dentro de dado, que é o oposto da tese.
COLUNAS = {"cst", "cclasstrib"}
FILTROS = {"", "modelo_do_documento"}
TABELAS = {"cst-cclasstrib"}

# Campos que cada tipo exige. Erro de configuração precisa aparecer no
# carregamento, não em produção validando nota de cliente.
OBRIGATORIOS = {
    "prefixo_de": ("campo", "campo_referencia"),
    "em_tabela": ("campo", "tabela", "coluna"),
    "subgrupos_por_indicador": ("campo_chave", "tabela", "coluna", "mapa"),
    "soma_campos": ("campo_total", "campos"),
    "exclusivo": ("campos",),
    "valor_numerico_em": ("campo", "valores"),
}


def _confere_configuracao(r: Regra, onde: str) -> None:
    if r.tipo not in EXECUTORES:
        raise ValueError(f"{onde}: tipo de regra desconhecido '{r.tipo}'")
    for campo in OBRIGATORIOS.get(r.tipo, ()):
        if not getattr(r, campo):
            raise ValueError(f"{onde}: tipo '{r.tipo}' exige o campo '{campo}'")

    if r.tabela and r.tabela not in TABELAS:
        raise ValueError(f"{onde}: tabela '{r.tabela}' não existe — há {sorted(TABELAS)}")
    if r.coluna and r.coluna not in COLUNAS:
        raise ValueError(f"{onde}: coluna '{r.coluna}' não existe — há {sorted(COLUNAS)}")
    if r.filtro not in FILTROS:
        raise ValueError(f"{onde}: filtro '{r.filtro}' não existe — há {sorted(FILTROS - {''})}")
    if r.filtro == "modelo_do_documento" and r.coluna != "cclasstrib":
        # só a classificação carrega IndNfe/IndNfce; pedir isso ao CST estouraria
        # em runtime, validando nota de cliente — o pior lugar para descobrir
        raise ValueError(
            f"{onde}: filtro 'modelo_do_documento' só vale com coluna 'cclasstrib', "
            f"porque os indicadores por documento existem só nesse nível"
        )
    if r.tolerancia:
        try:
            Decimal(r.tolerancia)
        except ArithmeticError as exc:
            raise ValueError(f"{onde}: tolerancia '{r.tolerancia}' não é número") from exc
    if r.tipo == "valor_numerico_em":
        for valor in r.valores:
            try:
                Decimal(valor)
            except ArithmeticError as exc:
                raise ValueError(f"{onde}: valor '{valor}' não é número") from exc

    if r.mapa:
        _confere_indicadores(r, onde)


def _confere_indicadores(r: Regra, onde: str) -> None:
    """Indicador que não existe na tabela oficial é erro de digitação da regra.

    Falhar aqui é barulhento e chato — e é exatamente o ponto. O silêncio
    alternativo seria uma regra que nunca dispara e ninguém percebe.
    """
    from . import tabelas as mod_tabelas

    try:
        tabela = mod_tabelas.cst_cclasstrib()
    except mod_tabelas.TabelaAusente:
        return  # sem tabela não há o que conferir; a regra vira `informacao` em runtime
    conhecidos = tabela.indicadores_conhecidos
    for indicador, _caminho in r.mapa:
        if indicador not in conhecidos:
            raise ValueError(
                f"{onde}: indicador '{indicador}' não existe na tabela {r.tabela}. "
                f"Confira o nome contra regras/tabelas/{r.tabela}.json"
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
                campo_referencia=bruto.get("campo_referencia", ""),
                tamanho=int(bruto.get("tamanho", 0) or 0),
                tabela=bruto.get("tabela", ""),
                coluna=bruto.get("coluna", ""),
                filtro=bruto.get("filtro", ""),
                campo_chave=bruto.get("campo_chave", ""),
                mapa=_mapa(bruto, f"{arquivo}: {rid}"),
                referencia=bruto.get("referencia", ""),
                escopo=escopo,
                vigencia=_vigencia(bruto, f"{arquivo}: {rid}"),
            ))
            _confere_configuracao(regras[-1], f"{arquivo}: {rid}")
    return regras


# ---- execução dos tipos ---------------------------------------------------
#
# Todo executor recebe um `Alvo`, não o documento: é o que faz o mesmo tipo de
# regra valer para o documento inteiro e para um item, sem código duplicado.

def _tolerancia(r: Regra, padrao: str) -> Decimal:
    """Tolerância da regra, ou o padrão do tipo quando o YAML não declara.

    Aritmética de totais tolera centavo de arredondamento; alíquota não tolera
    nada. Um padrão global só serviria a um dos dois casos.
    """
    return Decimal(r.tolerancia or padrao)


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
    for campo in (r.campos or (r.campo,)):
        atual = alvo.texto(campo)
        if atual is None:
            continue  # ausência é problema de outra regra
        if not re.fullmatch(r.padrao, atual):
            return f"{campo} = '{atual}' não casa com o formato esperado"
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
    if diferenca > _tolerancia(r, "0.01"):
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


def _prefixo_de(alvo: Alvo, r: Regra) -> str | None:
    """O campo precisa começar pelo conteúdo de outro campo.

    Pega o erro mais relatado em produção com IBS/CBS: ERP que liga o módulo com
    uma classificação genérica igual para todos os itens, sem casar com o CST.
    """
    atual = alvo.texto(r.campo)
    referencia = alvo.texto(r.campo_referencia)
    if atual is None or referencia is None:
        return None
    tamanho = r.tamanho or len(referencia)
    if atual[:tamanho] != referencia[:tamanho]:
        return f"{r.campo} = '{atual}' não começa por {r.campo_referencia} = '{referencia}'"
    return None


def _linhas(r: Regra) -> tuple[dict, str]:
    """Devolve as linhas da tabela pedida e a versão embarcada.

    Levanta `NaoAvaliavel` quando a tabela não está no pacote. É o ponto único
    onde a camada de dados oficiais entra no motor.
    """
    from . import tabelas as mod_tabelas  # tardio: o motor não depende de tabela

    try:
        tabela = mod_tabelas.cst_cclasstrib()
    except mod_tabelas.TabelaAusente as exc:
        raise NaoAvaliavel(f"regra não avaliada: {exc}") from exc
    linhas = {"cst": tabela.cst, "cclasstrib": tabela.classificacoes}[r.coluna]
    return linhas, tabela.versao


def _em_tabela(alvo: Alvo, r: Regra) -> str | None:
    """O valor precisa existir na tabela oficial embarcada."""
    atual = alvo.texto(r.campo)
    if atual is None:
        return None
    linhas, versao = _linhas(r)
    encontrada = linhas.get(atual)
    if encontrada is None:
        return f"{r.campo} = '{atual}' não existe na tabela {r.tabela} {versao}"

    if r.filtro == "modelo_do_documento":
        # a tabela diz, por cClassTrib, em quais documentos o código vale
        modelo = alvo.doc.texto("ide/mod")
        permitido = encontrada.vale_para_modelo(modelo)
        if permitido is False:
            nome = {"55": "NF-e", "65": "NFC-e"}.get(modelo, modelo)
            return f"{r.campo} = '{atual}' não é permitido no modelo {modelo} ({nome})"
    return None


def _indicadores_de(r: Regra, chave: str) -> dict[str, bool] | None:
    """Indicadores que valem para o código, no nível que a regra pediu."""
    from . import tabelas as mod_tabelas

    try:
        tabela = mod_tabelas.cst_cclasstrib()
    except mod_tabelas.TabelaAusente as exc:
        raise NaoAvaliavel(f"regra não avaliada: {exc}") from exc
    if r.coluna == "cst":
        grupo = tabela.cst.get(chave)
        return grupo.indicadores if grupo else None
    return tabela.indicadores_de(chave)


def _subgrupos_por_indicador(alvo: Alvo, r: Regra) -> str | None:
    """Exige ou veda subgrupos conforme os indicadores da tabela oficial.

    É a regra que ninguém mais tem e também a que mais pode acusar errado: ela
    depende de o mapa entre coluna da tabela e caminho XML estar certo. Por isso
    nasce como aviso no YAML, e só vira erro depois de rodar contra XML real
    (spec 05 §6).
    """
    chave = alvo.texto(r.campo_chave)
    if chave is None:
        return None
    indicadores = _indicadores_de(r, chave)
    if indicadores is None:
        return None  # código inexistente é problema da regra `em_tabela`

    faltando, vedados = [], []
    for indicador, caminho in r.mapa:
        exigido = indicadores.get(indicador)
        presente = alvo.existe(caminho)
        if exigido and not presente:
            faltando.append(caminho)
        elif exigido is False and presente:
            vedados.append(caminho)

    partes = []
    if faltando:
        partes.append(f"exige {', '.join(faltando)}, que está ausente")
    if vedados:
        partes.append(f"não admite {', '.join(vedados)}, que está presente")
    return f"{r.campo_chave} = '{chave}' " + " e ".join(partes) if partes else None


def _soma_campos(alvo: Alvo, r: Regra) -> str | None:
    """Um campo precisa ser a soma de outros, dentro de tolerância.

    Exige todas as parcelas presentes: tratar parcela ausente como zero acusaria
    grupo incompleto como erro de aritmética, que é diagnóstico errado.
    """
    total = alvo.decimal(r.campo_total)
    if total is None:
        return None
    parcelas = [alvo.decimal(campo) for campo in r.campos]
    if any(p is None for p in parcelas):
        return None
    soma = sum(parcelas, Decimal("0"))
    diferenca = abs(soma - total)
    if diferenca > _tolerancia(r, "0.01"):
        soma_escrita = " + ".join(r.campos)
        return (
            f"{r.campo_total} = {total}, {soma_escrita} = {soma}, "
            f"diferença de {diferenca}"
        )
    return None


def _exclusivo(alvo: Alvo, r: Regra) -> str | None:
    """No máximo um dos campos pode estar presente."""
    presentes = [campo for campo in r.campos if alvo.existe(campo)]
    if len(presentes) > 1:
        return f"presentes ao mesmo tempo: {', '.join(presentes)}"
    return None


def _valor_numerico_em(alvo: Alvo, r: Regra) -> str | None:
    """O valor precisa ser um de uma lista, comparado como número.

    `0.10`, `0.1000` e `0.100` são o mesmo valor. Comparar como texto geraria
    achado em nota correta só porque o emissor escolheu outra escala decimal.
    """
    atual = alvo.decimal(r.campo)
    if atual is None:
        return None  # ausente ou não numérico: problema de outra regra
    tolerancia = _tolerancia(r, "0")
    esperados = [Decimal(v) for v in r.valores]
    if any(abs(atual - esperado) <= tolerancia for esperado in esperados):
        return None
    return f"{r.campo} = {atual}, esperado {' ou '.join(str(e) for e in esperados)}"


EXECUTORES = {
    "existe": _existe,
    "nao_vazio": _nao_vazio,
    "valor_em": _valor_em,
    "formato": _formato,
    "soma_itens": _soma_itens,
    "condicional": _condicional,
    "prefixo_de": _prefixo_de,
    "em_tabela": _em_tabela,
    "subgrupos_por_indicador": _subgrupos_por_indicador,
    "soma_campos": _soma_campos,
    "exclusivo": _exclusivo,
    "valor_numerico_em": _valor_numerico_em,
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
            try:
                detalhe = executor(alvo, regra)
            except NaoAvaliavel as motivo:
                # uma vez por regra, não uma vez por item: falta de tabela é um
                # fato do ambiente, e repeti-lo por item afogaria o laudo
                achados.append(Achado(
                    regra=regra, detalhe=str(motivo), severidade="informacao",
                ))
                break
            if detalhe:
                achados.append(Achado(regra=regra, detalhe=detalhe, item=alvo.item))
    ordem = {"erro": 0, "aviso": 1, "informacao": 2}
    return sorted(
        achados,
        key=lambda a: (
            ordem.get(a.severidade or a.regra.severidade, 9), a.regra.id, _posicao(a.item),
        ),
    )
