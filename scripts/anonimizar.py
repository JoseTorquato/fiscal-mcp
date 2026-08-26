#!/usr/bin/env python3
"""Anonimiza XML fiscal sem quebrar o problema fiscal que ele reproduz.

Existe por um motivo prático: a melhor contribuição para este projeto é um XML
de verdade — o que quebra na prática nunca é o que a gente imagina sentado. Só
que XML de verdade é XML de cliente, e vazar dado de cliente é pior que não ter
a ferramenta. Este script é a ponte entre as duas coisas.

O que troca e o que preserva sai da mesma pergunta, feita campo a campo: *isso
identifica alguém* ou *isso faz a regra fiscal funcionar*? NCM, CFOP, CST,
cClassTrib, alíquota, valor e a geografia (UF, cMun, xMun) ficam, porque são
eles que reproduzem o problema. Nome, documento, endereço, contato e texto
livre saem. Na dúvida, sai: um XML anonimizado demais nunca custou nada.

Três propriedades sustentam o resto:

  determinismo   o mesmo valor de entrada vira sempre o mesmo de saída, aqui e
                 na sua máquina, hoje e no mês que vem. Sem isso o diff entre
                 original e anonimizado é ilegível e ninguém confere nada.
  estabilidade   dentro do arquivo, emitente e destinatário continuam sendo
                 dois documentos *diferentes*, e cada um continua igual a si
                 mesmo em toda ocorrência — inclusive dentro da chave de acesso.
  idempotência   anonimizar o que já está anonimizado não muda nada.

Os substitutos saem da ordem de aparição (o primeiro CNPJ vira o CNPJ 1), e não
de hash do valor original. É essa escolha que faz a idempotência cair de graça:
o substituto, relido, ocupa a mesma posição na fila e mapeia para si mesmo.

    python scripts/anonimizar.py nota.xml
    python scripts/anonimizar.py nota.xml -o anon.xml
    python scripts/anonimizar.py nota.xml --conferir
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_mcp.chave import TAMANHO as CHAVE_NFE  # noqa: E402
from fiscal_mcp.chave import calcula_dv  # noqa: E402
from fiscal_mcp.nfse import CHAVE_CNPJ as NFSE_CNPJ  # noqa: E402

# ---------------------------------------------------------------------------
# o que sai inteiro
# ---------------------------------------------------------------------------

# Signature carrega o certificado e o hash do documento original: substituir não
# faria sentido, porque assinatura de conteúdo trocado não é assinatura. protNFe
# traz o número de protocolo real, que amarra o arquivo a uma nota autorizada de
# verdade — e é justamente esse amarre que não pode viajar.
REMOVIDOS = {"Signature", "protNFe"}

# ---------------------------------------------------------------------------
# o que troca por substituto numerado e estável
# ---------------------------------------------------------------------------


def _modulo11(base: str, peso_maximo: int) -> str:
    """Dígito verificador por módulo 11, pesos crescentes da direita para a esquerda.

    É o mesmo algoritmo da chave de acesso (ver fiscal_mcp/chave.py), com uma
    diferença por documento: o CNPJ recicla o peso em 9, o CPF sobe até 10 sem
    reciclar. Daí o parâmetro em vez de duas funções quase iguais.
    """
    soma = 0
    peso = 2
    for digito in reversed(base):
        soma += int(digito) * peso
        peso = 2 if peso == peso_maximo else peso + 1
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def cnpj_ficticio(n: int) -> str:
    """CNPJ fictício de ordem `n`, com dígito verificador válido.

    A raiz começa em 10000001: é obviamente inventado para quem olha, mas passa
    em validação de formato e de DV — que é o que o XML precisa para continuar
    exercitando as mesmas regras que exercitava antes.
    """
    base = f"{10_000_000 + n:08d}0001"
    d1 = _modulo11(base, 9)
    return base + d1 + _modulo11(base + d1, 9)


def cpf_ficticio(n: int) -> str:
    """CPF fictício de ordem `n`, com dígito verificador válido."""
    base = f"{100_000_000 + n:09d}"
    d1 = _modulo11(base, 11)
    return base + d1 + _modulo11(base + d1, 11)


def _inscricao_ficticia(n: int, original: str) -> str:
    """Inscrição estadual/municipal fictícia, do mesmo comprimento da original.

    Manter o comprimento é o que garante que o campo continue casando com o
    formato declarado no leiaute. Valor não numérico (ISENTO, por exemplo) é
    palavra de regra e não identificação: passa intacto.
    """
    if not original.isdigit():
        return original
    return f"{n:0{len(original)}d}"


# Cada tipo tem sua própria fila. A ordem de aparição no documento define o
# número, e é isso que torna a saída estável entre execuções e idempotente.
GERADORES = {
    "cnpj": lambda n, _: cnpj_ficticio(n),
    "cpf": lambda n, _: cpf_ficticio(n),
    "nome": lambda n, _: f"Empresa {n} Ltda",
    "produto": lambda n, _: f"Produto {n}",
    "servico": lambda n, _: f"Servico {n}",
    "inscricao": _inscricao_ficticia,
    # cNF é o código numérico aleatório da nota. Sozinho não identifica ninguém,
    # mas é ele que, junto do resto, faz a chave resolver para um documento real.
    "cnf": lambda n, _: f"{10_000_000 + n:08d}",
    "observacao": lambda n, _: f"Texto {n} removido na anonimizacao",
    "campo": lambda n, _: f"campo{n}",
}

# tag (sem namespace) -> fila de substitutos
POR_FILA = {
    "CNPJ": "cnpj",
    "CPF": "cpf",
    "xNome": "nome",
    "xFant": "nome",
    "xProd": "produto",
    "xDescServ": "servico",
    "IE": "inscricao",
    "IEST": "inscricao",
    "IM": "inscricao",
    "ISUF": "inscricao",
    "cNF": "cnf",
    "xTexto": "observacao",
    "xJust": "observacao",
}

# Trocas fixas: o valor não precisa ser único, só precisa não ser de ninguém.
POR_VALOR_FIXO = {
    "xLgr": "Rua Exemplo",
    "nro": "100",
    "xCpl": "Sala 1",
    "xBairro": "Centro",
    "CEP": "00000000",
    "fone": "1130000000",
    "email": "contato@exemplo.com.br",
    # CNAE diz o ramo de atividade — sozinho já estreita muito quem é a empresa.
    "CNAE": "8299799",
    "infCpl": "Informacoes complementares removidas na anonimizacao",
    "infAdFisco": "Informacoes ao fisco removidas na anonimizacao",
}

# Texto livre que preservamos de propósito, para o alerta de tag desconhecida
# não gritar à toa. Geografia manda em regra fiscal (alíquota interestadual,
# município de incidência do ISS) e descrição de tabela oficial é igual para
# todo mundo — nenhum dos dois identifica alguém.
PRESERVADOS = {
    "xMun", "xUF", "xPais", "xLocEmi", "xLocPrestacao", "xLocIncid",
    "xTribNac", "xMotivo",
}

# Razão social exigida por lei na nota de homologação: é texto de norma, igual
# em toda nota de teste do país. Trocar esconderia exatamente o que a regra
# est-homologacao-razao-social existe para verificar.
RAZAO_HOMOLOGACAO = "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO"

# Tags que carregam chave de acesso de 44 dígitos no texto.
TAGS_CHAVE = {"chNFe", "refNFe", "chNFeRef", "refCTe", "chCTe"}

# Redes de segurança contra o que não previmos: e-mail e documento formatado
# aparecendo em campo que este script não trata.
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_DOC_FORMATADO = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")

# Substituto curto demais para conferir sem falso positivo: 'nro' vira "100" e
# procurar um número de três dígitos no XML acha o vProd da nota. Ver
# `procura_residuos` — o número da rua, sozinho, também não identifica ninguém.
SEM_CONFERENCIA = {"nro"}
TAMANHO_MINIMO_CONFERENCIA = 5

# A partir de 11 dígitos (CPF, CNPJ, chave) procuramos o valor original *dentro*
# de outros números, porque é assim que ele vaza: escondido numa chave que não
# soubemos reconstruir. Abaixo disso a busca por trecho só produz coincidência —
# um CEP de 8 dígitos aparece por acaso no meio de qualquer chave de 44.
TAMANHO_BUSCA_EM_TRECHO = 11


def _local(tag) -> str:
    """Nome do elemento sem namespace. Comentário tem `.tag` função, não string."""
    if not isinstance(tag, str):
        return ""
    return tag.split("}", 1)[-1] if "}" in tag else tag


@dataclass
class Resultado:
    """A saída anonimizada mais tudo que é preciso para conferir o que houve."""

    xml: str
    filas: dict[str, dict[str, str]] = field(default_factory=dict)
    fixos: dict[str, dict[str, str]] = field(default_factory=dict)
    chaves: dict[str, str] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)
    removidos: dict[str, int] = field(default_factory=dict)

    @property
    def trocas(self) -> int:
        das_filas = sum(len(m) for m in self.filas.values())
        return das_filas + sum(len(m) for m in self.fixos.values()) + len(self.chaves)


class Anonimizador:
    """Guarda as filas de substitutos enquanto percorre a árvore.

    Duas passadas de propósito. A primeira só fixa quem vira o quê, na ordem em
    que os elementos aparecem; a segunda escreve. Sem isso a chave de acesso —
    que é o primeiro atributo do documento — mapearia o CNPJ do emitente antes
    de o elemento `emit/CNPJ` existir para o mapa, e o número 1 da fila cairia
    no lugar errado dependendo de onde a chave aparecesse.
    """

    def __init__(self) -> None:
        self.filas: dict[str, dict[str, str]] = {}
        self.fixos: dict[str, dict[str, str]] = {}
        self.chaves: dict[str, str] = {}
        self.avisos: list[str] = []
        self.removidos: dict[str, int] = {}
        self.chave_nova: str | None = None

    # ---- filas ------------------------------------------------------------

    def troca(self, fila: str, original: str) -> str:
        mapa = self.filas.setdefault(fila, {})
        if original not in mapa:
            mapa[original] = GERADORES[fila](len(mapa) + 1, original)
        return mapa[original]

    def _avisa(self, mensagem: str) -> None:
        if mensagem not in self.avisos:
            self.avisos.append(mensagem)

    # ---- remoção ----------------------------------------------------------

    def _remove(self, raiz: etree._Element) -> None:
        """Tira assinatura, protocolo e comentários.

        Comentário some junto porque emissor comercial costuma carimbar ali o
        nome do cliente, o usuário que emitiu ou o caminho do arquivo na rede —
        e ninguém lê comentário de XML antes de anexar num issue.
        """
        for irmao in list(raiz.itersiblings(preceding=True)) + list(raiz.itersiblings()):
            if not isinstance(irmao.tag, str):
                # fica fora do elemento raiz; some sozinho ao serializar a raiz
                self._conta_removido("comentario")

        alvos = [
            elemento
            for elemento in raiz.iter()
            if not isinstance(elemento.tag, str) or _local(elemento.tag) in REMOVIDOS
        ]
        for elemento in alvos:
            pai = elemento.getparent()
            if pai is None:
                continue
            self._conta_removido(_local(elemento.tag) or "comentario")
            pai.remove(elemento)

    def _conta_removido(self, rotulo: str) -> None:
        self.removidos[rotulo] = self.removidos.get(rotulo, 0) + 1

    # ---- passada 1: fixa os substitutos -----------------------------------

    def _mapeia(self, raiz: etree._Element) -> None:
        for elemento in raiz.iter():
            tag = _local(elemento.tag)
            fila = POR_FILA.get(tag)
            if not fila:
                continue
            valor = (elemento.text or "").strip()
            if valor and not self._e_razao_de_lei(tag, valor):
                self.troca(fila, valor)

    @staticmethod
    def _e_razao_de_lei(tag: str, valor: str) -> bool:
        return tag in ("xNome", "xFant") and valor.upper().startswith(RAZAO_HOMOLOGACAO)

    # ---- passada 2: escreve -----------------------------------------------

    def _reescreve(self, raiz: etree._Element) -> None:
        for elemento in raiz.iter():
            tag = _local(elemento.tag)
            if not tag:
                continue
            self._atributos(elemento, tag)

            valor = (elemento.text or "").strip()
            if not valor:
                continue

            if tag in TAGS_CHAVE:
                elemento.text = self._chave(valor, tag)
            elif tag == "cDV" and self.chave_nova:
                # o cDV declarado tem de acompanhar o DV da chave reconstruída
                elemento.text = self.chave_nova[-1]
            elif tag in POR_FILA:
                if not self._e_razao_de_lei(tag, valor):
                    elemento.text = self.troca(POR_FILA[tag], valor)
            elif tag in POR_VALOR_FIXO:
                novo = POR_VALOR_FIXO[tag]
                self.fixos.setdefault(tag, {})[valor] = novo
                elemento.text = novo
            elif tag.startswith("x") and tag not in PRESERVADOS:
                # convenção do leiaute: tag iniciada em 'x' é texto livre, e
                # texto livre é onde nome de cliente aparece sem avisar
                self._avisa(
                    f"<{tag}> é texto livre e este script não a trata — confira o "
                    f"conteúdo à mão antes de publicar o arquivo"
                )

    def _atributos(self, elemento: etree._Element, tag: str) -> None:
        identificador = elemento.get("Id")
        if identificador:
            novo = self._identificador(identificador, tag)
            if novo != identificador:
                elemento.set("Id", novo)
        campo = elemento.get("xCampo")
        if campo:
            # obsCont/obsFisco: o rótulo do campo é livre e cabe nome de cliente
            elemento.set("xCampo", self.troca("campo", campo))

    # ---- chave de acesso --------------------------------------------------

    def _identificador(self, identificador: str, tag: str) -> str:
        prefixo = "".join(c for c in identificador if not c.isdigit())
        digitos = "".join(c for c in identificador if c.isdigit())
        if not digitos:
            return identificador
        if len(digitos) == CHAVE_NFE:
            nova = self._chave_nfe(digitos)
            self.chave_nova = nova
            self.chaves[digitos] = nova
            return prefixo + nova
        nova = self._chave_nfse(digitos, tag)
        if nova != digitos:
            self.chaves[digitos] = nova
        return prefixo + nova

    def _chave(self, valor: str, tag: str) -> str:
        digitos = "".join(c for c in valor if c.isdigit())
        if len(digitos) != CHAVE_NFE:
            self._avisa(
                f"<{tag}> tem {len(digitos)} dígitos, não {CHAVE_NFE}: deixei como "
                f"está porque não sei o que há dentro — confira à mão"
            )
            return valor
        nova = self._chave_nfe(digitos)
        self.chaves[digitos] = nova
        return nova

    def _chave_nfe(self, digitos: str) -> str:
        """Reconstrói a chave de 44 dígitos com CNPJ e cNF trocados.

        Todo o resto fica: cUF, ano/mês, modelo, série, número e tipo de emissão
        são o que faz a nota ser aquela nota fiscalmente. O dígito verificador é
        recalculado — sem isso a própria validação passaria a acusar a chave, e
        o arquivo anonimizado deixaria de reproduzir o problema original.
        """
        bruto = digitos[6:20]
        cpfs = self.filas.get("cpf", {})
        if bruto.startswith("000") and bruto[3:] in cpfs:
            # emissor pessoa física entra na chave como CPF com três zeros à frente
            novo_documento = "000" + self.troca("cpf", bruto[3:])
        else:
            novo_documento = self.troca("cnpj", bruto)
        novo_cnf = self.troca("cnf", digitos[35:43])
        base = digitos[:6] + novo_documento + digitos[20:35] + novo_cnf
        return base + str(calcula_dv(base))

    def _chave_nfse(self, digitos: str, tag: str) -> str:
        """Troca o documento dentro de uma chave de NFS-e nacional.

        A posição do CNPJ na chave de 50 dígitos está confirmada contra
        documento real (ver fiscal_mcp/nfse.py); a da chave da DPS não está.
        Onde não há confirmação, procuramos o documento em todos os
        deslocamentos e só mexemos se houver exatamente uma ocorrência —
        inventar leiaute de chave fiscal é o tipo de erro que só aparece no
        cliente. O DV da NFS-e não é recalculado porque o algoritmo dela não foi
        confirmado; a chave sai anonimizada e inválida, e isso é dito em voz
        alta em vez de chutado.
        """
        inicio, fim = NFSE_CNPJ
        conhecidos = self.filas.get("cnpj", {})
        if digitos[inicio:fim] in conhecidos:
            return digitos[:inicio] + conhecidos[digitos[inicio:fim]] + digitos[fim:]

        posicoes = [
            (i, original)
            for original in conhecidos
            for i in range(len(digitos) - len(original) + 1)
            if digitos[i:i + len(original)] == original
        ]
        if len(posicoes) == 1:
            i, original = posicoes[0]
            return digitos[:i] + conhecidos[original] + digitos[i + len(original):]

        if posicoes:
            self._avisa(
                f"o Id de <{tag}> traz um documento conhecido em mais de uma posição "
                f"— não mexi, para não corromper a chave. Confira à mão"
            )
        else:
            self._avisa(
                f"o Id de <{tag}> tem {len(digitos)} dígitos e não achei nele nenhum "
                f"documento conhecido: deixei intacto, mas ele pode carregar o CNPJ "
                f"real — confira à mão"
            )
        return digitos

    # ---- rede de segurança -------------------------------------------------

    def _alerta_sobras(self, raiz: etree._Element) -> None:
        """Varre o que sobrou atrás do que parece dado pessoal e não foi tratado."""
        for elemento in raiz.iter():
            tag = _local(elemento.tag) or "?"
            for valor in [elemento.text or ""] + [str(v) for v in elemento.values()]:
                if _EMAIL.search(valor) and valor.strip() != POR_VALOR_FIXO["email"]:
                    self._avisa(f"sobrou algo com cara de e-mail em <{tag}>")
                if _DOC_FORMATADO.search(valor):
                    self._avisa(f"sobrou algo com cara de CPF/CNPJ em <{tag}>")

    # ---- orquestração ------------------------------------------------------

    def executa(self, raiz: etree._Element) -> None:
        self._remove(raiz)
        self._mapeia(raiz)
        self._reescreve(raiz)
        self._alerta_sobras(raiz)


def _parse(xml: str | bytes) -> etree._Element:
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    # mesmo endurecimento de fiscal_mcp/documento.py: o arquivo vem de terceiro
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
    return etree.fromstring(xml, parser=parser)


def _desembrulha_nfeproc(raiz: etree._Element) -> etree._Element:
    """`nfeProc` sem `protNFe` vira `NFe`.

    O protocolo sai porque amarra o arquivo a uma autorização real. Só que o
    schema oficial exige `protNFe` dentro de `nfeProc` — deixar o invólucro
    produziria um documento que não passa no próprio XSD, e o primeiro uso do
    XML contribuído seria justamente rodá-lo no validador.

    Um XML anonimizado existe para reproduzir problema de validação, não para
    provar autorização. Sem protocolo, o invólucro não tem mais o que embrulhar.
    """
    if _local(raiz.tag) != "nfeProc":
        return raiz
    nfe = next((f for f in raiz if isinstance(f.tag, str) and _local(f.tag) == "NFe"), None)
    if nfe is None:
        return raiz
    # o tail é a indentação que existia entre </NFe> e </nfeProc>; carregá-la
    # para a raiz nova quebraria a idempotência por um espaço em branco
    nfe.tail = None
    return nfe


def anonimiza(xml: str | bytes) -> Resultado:
    """Anonimiza o XML e devolve a saída junto do mapa do que foi trocado."""
    raiz = _parse(xml)
    anon = Anonimizador()
    anon.executa(raiz)
    raiz = _desembrulha_nfeproc(raiz)
    # serializa a partir da raiz, e não da árvore: é o que descarta de uma vez
    # comentário e DOCTYPE que estejam fora do elemento raiz
    corpo = etree.tostring(raiz, encoding="unicode")
    return Resultado(
        xml='<?xml version="1.0" encoding="UTF-8"?>\n' + corpo + "\n",
        filas=anon.filas,
        fixos=anon.fixos,
        chaves=anon.chaves,
        avisos=anon.avisos,
        removidos=anon.removidos,
    )


# ---------------------------------------------------------------------------
# conferência
# ---------------------------------------------------------------------------


def _valores_do_xml(xml: str) -> list[tuple[str, str]]:
    """Todo texto e todo atributo da saída, com a tag de origem.

    Conferir valor por valor, e não o arquivo inteiro concatenado, evita o falso
    positivo em que dois números vizinhos formam por acaso um CNPJ.
    """
    try:
        raiz = _parse(xml)
    except etree.XMLSyntaxError:
        return [("?", xml)]
    achados = []
    for elemento in raiz.iter():
        tag = _local(elemento.tag) or "?"
        if elemento.text:
            achados.append((tag, elemento.text))
        achados += [(tag, str(valor)) for valor in elemento.values()]
    return achados


def _mascara(valor: str) -> str:
    """Mostra o bastante para achar o campo, sem reimprimir o dado inteiro.

    O relatório costuma ir para um log ou para um issue; reimprimir o CNPJ
    original inteiro ali derrubaria o propósito do script.
    """
    if len(valor) <= 4:
        return "*" * len(valor)
    return valor[:2] + "*" * (len(valor) - 4) + valor[-2:]


def _pares_conferiveis(resultado: Resultado) -> list[tuple[str, str, str]]:
    """(rótulo, original, substituto) do que vale a pena procurar na saída."""
    pares: list[tuple[str, str, str]] = []
    for fila, mapa in sorted(resultado.filas.items()):
        pares += [(fila, o, n) for o, n in mapa.items()]
    for tag, mapa in sorted(resultado.fixos.items()):
        if tag in SEM_CONFERENCIA:
            continue
        pares += [(tag, o, n) for o, n in mapa.items()]
    pares += [("chave", o, n) for o, n in resultado.chaves.items()]
    return [
        (rotulo, original, novo)
        for rotulo, original, novo in pares
        if original != novo
        and len(original) >= TAMANHO_MINIMO_CONFERENCIA
        # valor de um dígito só repetido (00000000000000) não é documento de
        # ninguém: nenhum validador de CPF ou CNPJ aceita, e procurá-lo só
        # encontra o enchimento de zeros de alguma chave
        and len(set(original)) > 1
    ]


def procura_residuos(resultado: Resultado, saida: str | None = None) -> list[str]:
    """Relê a saída procurando valor original que tenha escapado.

    É a rede que impede o erro caro, e por isso prefere acusar demais a deixar
    passar: se der falso positivo, o custo é abrir o arquivo e olhar.
    """
    valores = _valores_do_xml(resultado.xml if saida is None else saida)
    achados = []
    for rotulo, original, _novo in _pares_conferiveis(resultado):
        procurado = original.lower()
        so_digitos = original.isdigit()
        por_trecho = not so_digitos or len(original) >= TAMANHO_BUSCA_EM_TRECHO
        for tag, valor in valores:
            alvo = re.sub(r"\D", "", valor) if so_digitos else valor.lower()
            bateu = procurado in alvo if por_trecho else procurado == alvo
            if bateu:
                achados.append(f"{rotulo} '{_mascara(original)}' ainda aparece em <{tag}>")
                break
    return achados


def relatorio(resultado: Resultado) -> list[str]:
    """Linhas do relatório de `--conferir`, com o original sempre mascarado."""
    linhas = []
    for rotulo, mapa in sorted(resultado.filas.items()):
        linhas += [f"  {rotulo:<10} {_mascara(o):>22}  ->  {n}" for o, n in mapa.items()]
    for tag, mapa in sorted(resultado.fixos.items()):
        linhas += [f"  {tag:<10} {_mascara(o):>22}  ->  {n}" for o, n in mapa.items()]
    linhas += [
        f"  {'chave':<10} {_mascara(o):>22}  ->  {n}" for o, n in resultado.chaves.items()
    ]
    linhas += [
        f"  {'removido':<10} {rotulo} ({quantas})"
        for rotulo, quantas in sorted(resultado.removidos.items())
    ]
    return linhas


# ---------------------------------------------------------------------------
# linha de comando
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(
        prog="anonimizar.py",
        description=(
            "Anonimiza XML de NF-e ou NFS-e nacional preservando o que faz a regra "
            "fiscal funcionar."
        ),
    )
    p.add_argument("arquivo", help="caminho do XML de entrada")
    p.add_argument("-o", "--saida", help="arquivo de saída (padrão: saída padrão)")
    p.add_argument(
        "--conferir",
        action="store_true",
        help="relê a saída procurando resíduo do original; sai com 1 se achar",
    )
    args = p.parse_args(argv)

    caminho = Path(args.arquivo)
    if not caminho.is_file():
        print(f"arquivo não encontrado: {caminho}", file=sys.stderr)
        return 2

    try:
        resultado = anonimiza(caminho.read_bytes())
    except etree.XMLSyntaxError as exc:
        print(f"XML malformado: {exc}", file=sys.stderr)
        return 2

    if args.saida:
        Path(args.saida).write_text(resultado.xml, encoding="utf-8")
    else:
        sys.stdout.write(resultado.xml)

    # aviso vai sempre para a saída de erro: melhor barulhento que vazando
    for aviso in resultado.avisos:
        print(f"aviso: {aviso}", file=sys.stderr)

    if not args.conferir:
        return 0

    print(f"\n{resultado.trocas} valor(es) trocado(s):", file=sys.stderr)
    for linha in relatorio(resultado):
        print(linha, file=sys.stderr)

    residuos = procura_residuos(resultado)
    if residuos:
        alarme = "\nRESÍDUO DO ORIGINAL NA SAÍDA — não publique este arquivo:"
        print(alarme, file=sys.stderr)
        for residuo in residuos:
            print(f"  {residuo}", file=sys.stderr)
        return 1

    print("\nnenhum resíduo do original encontrado na saída.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
