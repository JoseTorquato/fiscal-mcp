"""Validação por schema XSD, com as mensagens traduzidas para português.

A validação por regra pega o que a regra conhece. O XSD pega o resto: elemento
fora de ordem, cardinalidade violada, tipo errado, campo inventado. É a
diferença entre "achei o campo e ele parece estranho" e "esta nota não passa no
validador da SEFAZ".

**Rodar o XSD é uma tarde; traduzir é o produto.** `lxml` devolve coisas como

    Element '{http://www.portalfiscal.inf.br/nfe}IBSCBS': Missing child
    element(s). Expected is ( {http://www.portalfiscal.inf.br/nfe}cClassTrib ).

que é inútil para um agente e quase inútil para um humano. Sem tradução esta
camada não vale mais que o `xmllint` que o dev já tem. Ver docs/spec/06.

Duas garantias que não podem ser quebradas:

1. **Zero rede.** `XMLSchema` do lxml resolve `xs:include` — os parsers daqui
   usam `no_network=True` e há teste explícito para isso.
2. **Mensagem não reconhecida sai crua e marcada.** Nunca é engolida nem
   adivinhada. Achado cru e honesto é melhor que achado bonito e errado.

## Duas armadilhas de versão, e como não acusar errado

**Documento não assinado nunca passa no XSD.** O schema oficial exige
`Signature` dentro de `NFe`. Como esta ferramenta não assina nada, por decisão
(ADR-0010), o caso normal de uso é justamente o XML ainda não assinado. Esse
achado sai como `informacao`, explicando o que é — reprovar aqui seria reprovar
todo mundo que usa a ferramenta para o que ela existe.

**O pacote de schemas pode ser anterior ao leiaute do documento.** Quando o erro
cita um elemento que não existe em lugar nenhum do pacote embarcado, o
diagnóstico honesto não é "a nota está errada" e sim "o schema não conhece isso".
Esses achados são rebaixados para aviso, dizendo o porquê. A verificação é por
evidência — o conjunto de nomes vem do próprio XSD, não de uma lista escrita à
mão que envelheceria em silêncio.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from lxml import etree

RAIZ_SCHEMA = Path(__file__).resolve().parent / "regras" / "schema"
if not RAIZ_SCHEMA.is_dir():  # repositório clonado, não instalado
    RAIZ_SCHEMA = Path(__file__).resolve().parent.parent / "regras" / "schema"

NS_NFE = "http://www.portalfiscal.inf.br/nfe"

MENSAGEM_SEM_ASSINATURA = re.compile(r"Element 'NFe'.*Expected is one of.*Signature")


class SchemaIndisponivel(Exception):
    """O extra `[xsd]` não está instalado. Não é erro do documento."""


@dataclass(frozen=True)
class Traducao:
    id: str
    padrao: re.Pattern
    problema: str
    acao: str
    severidade: str = ""


@lru_cache(maxsize=1)
def _traducoes() -> tuple[Traducao, ...]:
    caminho = RAIZ_SCHEMA / "traducoes.yaml"
    if not caminho.is_file():
        return ()
    doc = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    return tuple(
        Traducao(
            id=t["id"],
            padrao=re.compile(t["padrao"]),
            problema=t["problema"],
            acao=t.get("acao", ""),
            severidade=t.get("severidade", ""),
        )
        for t in doc.get("traducoes", [])
    )


def disponivel() -> bool:
    """O extra `[xsd]` está instalado?"""
    try:
        import nfelib  # noqa: F401
    except ImportError:
        return False
    return True


@lru_cache(maxsize=1)
def pacote() -> str:
    """Identificação do pacote de schemas em uso, para a saída declarar.

    Quem depende de uma validação precisa saber contra o quê ela rodou. Sem isso
    "passou no schema" é uma frase sem sujeito.
    """
    try:
        import importlib.metadata as meta

        import nfelib
    except ImportError as exc:
        raise SchemaIndisponivel("extra [xsd] não instalado") from exc

    versao = meta.version("nfelib")
    raiz = Path(nfelib.__file__).parent
    return f"{identifica(raiz / 'nfe' / 'schemas' / 'v4_0', declarado_pela_nfelib(raiz))} (nfelib {versao})"


def pacotes_conhecidos() -> dict:
    """O registro versionado em regras/schema/pacotes.yaml, com procedência."""
    caminho = RAIZ_SCHEMA / "pacotes.yaml"
    if not caminho.is_file():
        return {"arquivos": [], "pacotes": []}
    return yaml.safe_load(caminho.read_text(encoding="utf-8")) or {"arquivos": [], "pacotes": []}


def sha256_dos_xsd(base: Path, arquivos: list[str]) -> dict[str, str | None]:
    """sha256 de cada XSD instalado; None para o que não existe."""
    import hashlib

    return {
        nome: hashlib.sha256((base / nome).read_bytes()).hexdigest() if (base / nome).is_file() else None
        for nome in arquivos
    }


def declarado_pela_nfelib(raiz_nfelib: Path) -> str | None:
    """O ZIP que a própria nfelib diz ter embarcado, lido como texto.

    A nfelib (desde a 2.6.0) grava `SCHEMA_PACKAGE` nos bindings gerados. Ler o
    arquivo em vez de importá-lo evita carregar os bindings inteiros só para
    saber um nome. Serve de conferência, não de verdade: quem decide é o
    conteúdo dos XSD.
    """
    init = raiz_nfelib / "nfe" / "bindings" / "v4_0" / "__init__.py"
    if not init.is_file():
        return None
    achado = re.search(
        r"SCHEMA_PACKAGE[^=]*=\s*['\"][^'\"]*?\(zip\s+(PL_[0-9A-Za-z_.]+)\)",
        init.read_text(encoding="utf-8", errors="replace"),
    )
    return achado.group(1) if achado else None


def identifica(base: Path, declarado: str | None = None) -> str:
    """Nome do pacote cujo conteúdo é exatamente o dos XSD em `base`.

    O nome vem do registro versionado, casado por sha256 — não de texto do XSD
    nem de string fixa no código. Conteúdo que não bate com nenhum pacote
    registrado diz isso, junto com o que a nfelib declara: um nome adivinhado
    seria "passou no schema" com o sujeito errado.
    """
    registro = pacotes_conhecidos()
    instalados = sha256_dos_xsd(base, registro.get("arquivos", []))
    for pacote_ in registro.get("pacotes", []):
        if instalados and pacote_.get("sha256") == instalados:
            nome = pacote_["nome"]
            if declarado and declarado != nome:
                # o conteúdo manda; a divergência fica à vista em vez de escondida
                return f"{nome} — a nfelib declara {declarado}, mas o conteúdo é o do {nome}"
            return nome
    sufixo = f"; a nfelib declara {declarado}" if declarado else ""
    return f"pacote não identificado — conteúdo fora de regras/schema/pacotes.yaml{sufixo}"


@lru_cache(maxsize=1)
def _nomes_conhecidos() -> frozenset[str]:
    """Todo nome de elemento que o pacote de schemas embarcado conhece.

    Serve para separar "a nota está errada" de "o schema não conhece isso". Vem
    do próprio XSD porque lista escrita à mão envelhece em silêncio — e um
    rebaixamento indevido esconde erro de verdade.
    """
    import nfelib

    base = Path(nfelib.__file__).parent / "nfe" / "schemas" / "v4_0"
    nomes: set[str] = set()
    for arquivo in base.glob("*.xsd"):
        nomes |= set(re.findall(
            r'name="(\w+)"', arquivo.read_text(encoding="utf-8", errors="replace")
        ))
    return frozenset(nomes)


@lru_cache(maxsize=2)
def _esquema(raiz: str) -> etree.XMLSchema:
    try:
        import nfelib
    except ImportError as exc:
        raise SchemaIndisponivel(
            "validação por schema exige o extra: pip install 'fiscal-mcp[xsd]'"
        ) from exc

    base = Path(nfelib.__file__).parent / "nfe" / "schemas" / "v4_0"
    arquivo = "procNFe_v4.00.xsd" if raiz == "nfeProc" else "nfe_v4.00.xsd"
    # no_network=True aqui é o que impede o lxml de sair buscando xs:import
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    return etree.XMLSchema(etree.parse(str(base / arquivo), parser))


def _sem_ns(texto: str) -> str:
    """Tira a URL do namespace. Ninguém precisa ver o portal fiscal na mensagem."""
    return texto.replace(f"{{{NS_NFE}}}", "")


def _item_do_erro(arvore: etree._ElementTree, caminho: str | None) -> str | None:
    """Descobre em qual item o erro caiu, pelo `nItem` — não pela posição.

    O lxml devolve caminho anônimo (`/*/*/*[6]/*[2]`), que resolve contra o
    documento. Subir até o `det` e ler o `nItem` é o que faz a mensagem apontar
    para o item que a nota chama assim, e não para a terceira posição.
    """
    if not caminho:
        return None
    try:
        achados = arvore.xpath(caminho)
    except etree.XPathError:
        return None
    if not achados:
        return None
    elemento = achados[0]
    while elemento is not None:
        marca = elemento.tag
        if isinstance(marca, str) and _sem_ns(marca).split("}")[-1] == "det":
            return elemento.get("nItem")
        elemento = elemento.getparent()
    return None


def _elementos_citados(mensagem: str) -> set[str]:
    return set(re.findall(rf"\{{{re.escape(NS_NFE)}\}}(\w+)", mensagem))


def _traduz(mensagem: str) -> tuple[str, str, str, str] | None:
    """(id, problema, acao, severidade) da primeira tradução que casar."""
    limpa = _sem_ns(mensagem)
    for traducao in _traducoes():
        casou = traducao.padrao.search(limpa)
        if not casou:
            continue
        campos = {k: v for k, v in casou.groupdict().items() if v}
        try:
            return (
                traducao.id,
                traducao.problema.format(**campos),
                traducao.acao.format(**campos),
                traducao.severidade,
            )
        except (KeyError, IndexError):
            # tradução com campo que o padrão não captura: a mensagem sai crua e
            # marcada, como qualquer outra não reconhecida. Melhor que estourar
            # no meio de uma validação por causa de um typo no YAML
            return None
    return None


def valida(xml: str | bytes) -> list[dict]:
    """Achados de schema, já traduzidos. Levanta `SchemaIndisponivel` sem o extra.

    Só devolve achados; quem monta o laudo é o validador.
    """
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    parser = etree.XMLParser(no_network=True, resolve_entities=False, huge_tree=False)
    arvore = etree.ElementTree(etree.fromstring(xml, parser=parser))
    raiz = _sem_ns(arvore.getroot().tag).split("}")[-1]

    esquema = _esquema(raiz)
    if esquema.validate(arvore):
        return []

    achados = []
    for erro in esquema.error_log:
        achados.append(_achado(erro, arvore))
    return achados


def _achado(erro, arvore: etree._ElementTree) -> dict:
    mensagem = erro.message

    if MENSAGEM_SEM_ASSINATURA.search(_sem_ns(mensagem)):
        # o caso normal de uso desta ferramenta é o XML ainda não assinado
        return {
            "id": "schema-sem-assinatura",
            "severidade": "informacao",
            "grupo": "schema",
            "problema": "o documento não está assinado digitalmente",
            "detalhe": f"linha {erro.line} do XML",
            "acao": (
                "Esperado se você ainda não assinou: o schema oficial exige a "
                "assinatura dentro do elemento NFe, e esta ferramenta não assina "
                "nada, por decisão. Assine com o certificado A1 do emitente antes "
                "de transmitir — a SEFAZ recusa documento sem assinatura válida."
            ),
        }

    citados = _elementos_citados(mensagem)
    desconhecidos = citados - _nomes_conhecidos()

    traduzido = _traduz(mensagem)
    if traduzido:
        identificador, problema, acao, severidade = traduzido
    else:
        # cru e marcado: adivinhar aqui produziria achado bonito e errado
        identificador, problema = "schema-nao-traduzido", _sem_ns(mensagem)
        acao = (
            "Mensagem do validador de schema ainda sem tradução. Abra uma issue "
            "com este texto para que ela entre no catálogo."
        )
        severidade = ""

    achado = {
        "id": identificador,
        "severidade": severidade or "erro",
        "grupo": "schema",
        "problema": problema,
        "acao": acao,
    }

    item = _item_do_erro(arvore, erro.path)
    if item:
        achado["item"] = item
    achado["detalhe"] = (
        f"item {item}, linha {erro.line} do XML" if item else f"linha {erro.line} do XML"
    )
    if identificador == "schema-nao-traduzido":
        achado["traduzido"] = False

    if desconhecidos:
        # o documento usa estrutura posterior ao pacote: "não esperado aqui"
        # significa "o schema não conhece", não "a nota está errada"
        achado["severidade"] = "aviso"
        achado["nao_coberto_pelo_pacote"] = sorted(desconhecidos)
        achado["acao"] = (
            f"O pacote de schemas embarcado ({pacote()}) não conhece "
            f"{', '.join(sorted(desconhecidos))}, então este achado é aviso e não "
            "erro: o documento parece usar leiaute posterior ao pacote. Confira "
            "contra a nota técnica que você está implementando."
        )
    return achado
