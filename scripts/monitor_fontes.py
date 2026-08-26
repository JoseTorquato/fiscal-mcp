#!/usr/bin/env python3
"""Vigia as fontes oficiais e avisa um humano quando sai documento novo.

    python scripts/monitor_fontes.py           # imprime o que achou
    python scripts/monitor_fontes.py --json    # relatório e issues em JSON
    python scripts/monitor_fontes.py --semear  # grava o que está no ar em fontes.yaml

Funciona na mão, sem GitHub: quem abre a issue é o workflow agendado, a partir
do JSON. O monitor só descobre e descreve.

**Ele não interpreta conteúdo.** Não lê a nota técnica, não deriva regra, não
sugere código e não encosta em `regras/nfe/` nem em `regras/tabelas/`. Durante a
pesquisa da spec 05, uma extração automatizada do PDF de uma NT produziu códigos
de rejeição que não existem — que é exatamente o modo de falha que este projeto
existe para impedir. Nota técnica precisa ser lida por gente; o papel do monitor
termina em "olha isto".

Também não roda na suíte de testes nem no CI de push/PR, pela mesma razão que a
tabela oficial vive versionada: indisponibilidade de site de terceiro não pode
quebrar o build de quem depende do pacote. Ver `regras/tabelas/PROCEDENCIA.md`.

Códigos de saída: 0 quando o monitor concluiu a checagem — inclusive quando a
fonte estava fora do ar, porque isso é achado, não falha do monitor. Diferente
de 0 só quando o próprio monitor quebrou, que aí é bug nosso.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import date
from http.cookiejar import CookieJar
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "regras" / "fontes.yaml"

sys.path.insert(0, str(Path(__file__).resolve().parent))

# A extração e a normalização da tabela já existem e são a definição do que
# conta como "a tabela mudou". Reimplementar aqui criaria duas verdades — e a
# segunda passaria a acusar mudança onde não houve.
import baixar_tabelas  # noqa: E402

# Situações possíveis de uma fonte. Só a primeira dispensa humano.
SEM_MUDANCA = "sem_mudanca"
MUDOU = "mudou"
INDISPONIVEL = "indisponivel"
FORMATO_INESPERADO = "formato_inesperado"
PROCEDENCIA_DIVERGENTE = "procedencia_divergente"


# --------------------------------------------------------------------------- #
# rede
# --------------------------------------------------------------------------- #

def baixa(url: str, tempo_limite: int = 90) -> str:
    """Busca a página. Único ponto do módulo que toca a rede — é o que os
    testes substituem para continuarem offline."""
    # O Portal da NF-e responde 302 em laço para quem não guarda o cookie de
    # sessão. Sem o CookieJar o monitor concluiria "fonte fora do ar" toda
    # segunda-feira e o alerta que importa se perderia no meio do ruído.
    abridor = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    abridor.addheaders = [("User-Agent", "fiscal-mcp/monitor-de-fontes")]
    with abridor.open(url, timeout=tempo_limite) as resposta:
        bruto = resposta.read()
        codificacao = resposta.headers.get_content_charset() or "utf-8"
    try:
        return bruto.decode(codificacao)
    except (UnicodeDecodeError, LookupError):
        # O Portal declara UTF-8 no cabeçalho HTTP e ISO-8859-1 no `<meta>` da
        # própria página. Hoje entrega UTF-8; se um dia trocar, decodificar
        # errado faria "Nota Técnica" virar outro texto e *todo* documento
        # pareceria novo. Cair para latin-1 é preferível ao alarme falso.
        return bruto.decode("iso-8859-1")


# --------------------------------------------------------------------------- #
# fonte do tipo `lista_de_documentos`
# --------------------------------------------------------------------------- #

# Regex e não lxml de propósito: a página aninha um segundo documento XHTML
# completo dentro de uma `<div>`, e cada parser conserta isso de um jeito.
# O que precisamos é literal e estável há anos — o rótulo da seção e o título
# dentro do `<span class="tituloConteudo">`.
_SECAO = re.compile(r'<p class="tituloSessao">(.*?)</p>', re.S)
_TITULO = re.compile(r'class="tituloConteudo"[^>]*>(.*?)</span>', re.S)


def _texto(bruto: str) -> str:
    """Título como um humano o leria: sem tags, sem entidade, sem espaço duplo.

    O portal alterna `Nota Técnica`, `Nota&nbsp;Técnica` e `Nota Técnica ` no
    mesmo documento. Sem normalizar, o mesmo documento entraria como novo a cada
    execução — e o monitor viraria a coisa que ninguém lê.
    """
    sem_tags = re.sub(r"<[^>]+>", " ", bruto)
    texto = unicodedata.normalize("NFKC", html.unescape(sem_tags))
    return " ".join(texto.split())


def titulos_por_secao(pagina: str, secoes: dict[str, str]) -> dict[str, list[str]]:
    """Mapeia cada seção da página para a chave usada em `fontes.yaml`.

    `secoes` vem do YAML e não do código: o dia em que o portal renomear
    "Documentos vigentes" é um dia em que alguém precisa olhar, não um dia de
    editar constante escondida.
    """
    partes = _SECAO.split(pagina)
    if len(partes) < 3:
        raise FormatoInesperado(
            "não encontrei nenhuma seção `tituloSessao` na página — "
            "o portal mudou de formato"
        )

    achados: dict[str, list[str]] = {}
    desconhecidas = []
    for indice in range(1, len(partes), 2):
        rotulo = _texto(partes[indice])
        chave = secoes.get(rotulo)
        if chave is None:
            desconhecidas.append(rotulo)
            continue
        achados[chave] = [_texto(t) for t in _TITULO.findall(partes[indice + 1])]

    if desconhecidas:
        raise FormatoInesperado(
            "seção não declarada em regras/fontes.yaml: "
            + ", ".join(sorted(desconhecidas))
        )
    faltando = sorted(set(secoes.values()) - set(achados))
    if faltando:
        raise FormatoInesperado("seção sumiu da página: " + ", ".join(faltando))
    if not any(achados.values()):
        raise FormatoInesperado("nenhum documento listado — página vazia ou remontada")
    return achados


class FormatoInesperado(Exception):
    """A fonte respondeu, mas não com o que sabemos ler. É achado, não crash."""


def confere_lista_de_documentos(fonte: dict, baixador) -> dict:
    conhecidos = fonte.get("documentos_conhecidos") or {}
    secoes = fonte["secoes"]

    try:
        no_ar = titulos_por_secao(baixador(fonte["url"]), secoes)
    except FormatoInesperado as erro:
        return {"situacao": FORMATO_INESPERADO, "achados": [str(erro)]}
    except (urllib.error.URLError, OSError, TimeoutError) as erro:
        return {"situacao": INDISPONIVEL, "achados": [f"{type(erro).__name__}: {erro}"]}

    # Onde cada título estava e onde está agora. Documento novo é o sinal
    # principal; documento que troca de seção (sai de vigência, volta a vigorar)
    # ou some da página também é fato fiscal, e um humano decide o que fazer.
    antes = {t: chave for chave, lista in conhecidos.items()
             if isinstance(lista, list) for t in lista}
    agora = {t: chave for chave, lista in no_ar.items() for t in lista}

    achados = []
    for titulo, secao in agora.items():
        anterior = antes.get(titulo)
        if anterior is None:
            achados.append(f"documento novo em `{secao}`: {titulo}")
        elif anterior != secao:
            achados.append(f"mudou de `{anterior}` para `{secao}`: {titulo}")
    for titulo, secao in antes.items():
        if titulo not in agora:
            achados.append(f"sumiu de `{secao}`: {titulo}")

    situacao = MUDOU if achados else SEM_MUDANCA
    return {
        "situacao": situacao,
        "achados": sorted(achados),
        "documentos_no_ar": sum(len(v) for v in no_ar.values()),
    }


# --------------------------------------------------------------------------- #
# fonte do tipo `tabela`
# --------------------------------------------------------------------------- #

_SHA_DECLARADO = re.compile(r"\*\*sha256\*\*\s*\|\s*`([0-9a-f]{64})`")


def sha_declarado(procedencia: Path) -> str | None:
    achado = _SHA_DECLARADO.search(procedencia.read_text(encoding="utf-8"))
    return achado.group(1) if achado else None


def diferencas_da_tabela(versionada: dict, no_ar: dict) -> list[str]:
    """Diz *o que* mudou, não só *que* mudou.

    Uma issue que só informa "o sha divergiu" obriga o humano a refazer o
    trabalho do monitor antes de começar o dele.
    """
    achados = []
    antes_pub = versionada.get("publicacao_declarada_pela_fonte")
    agora_pub = no_ar.get("publicacao_declarada_pela_fonte")
    if antes_pub != agora_pub:
        achados.append(f"publicação declarada pela fonte: {antes_pub} → {agora_pub}")

    def indexa(tabela: dict) -> tuple[set[str], dict[str, dict]]:
        cst = {grupo["Cst"] for grupo in tabela.get("cst", [])}
        classificacoes = {
            linha["CodClassTrib"]: linha
            for grupo in tabela.get("cst", [])
            for linha in grupo.get("ClassificacoesTributarias", [])
        }
        return cst, classificacoes

    cst_antes, class_antes = indexa(versionada)
    cst_agora, class_agora = indexa(no_ar)

    for rotulo, conjunto in (("CST novo", cst_agora - cst_antes),
                             ("CST removido", cst_antes - cst_agora)):
        if conjunto:
            achados.append(f"{rotulo}: {', '.join(sorted(conjunto))}")

    novas = sorted(set(class_agora) - set(class_antes))
    removidas = sorted(set(class_antes) - set(class_agora))
    alteradas = sorted(c for c in set(class_antes) & set(class_agora)
                       if class_antes[c] != class_agora[c])
    for rotulo, codigos in (("cClassTrib novo", novas),
                            ("cClassTrib removido", removidas),
                            ("cClassTrib alterado", alteradas)):
        if codigos:
            achados.append(f"{rotulo} ({len(codigos)}): {_amostra(codigos)}")

    if not achados:
        # Mudou algo fora do recorte acima (campo novo no leiaute da tabela,
        # por exemplo). Vale alerta igual — não se conclui "nada mudou".
        achados.append("a tabela mudou em campo que este monitor não sabe resumir")
    return achados


def _amostra(codigos: list[str], quantos: int = 12) -> str:
    if len(codigos) <= quantos:
        return ", ".join(codigos)
    return ", ".join(codigos[:quantos]) + f", … (+{len(codigos) - quantos})"


def confere_tabela(fonte: dict, raiz: Path, baixador) -> dict:
    arquivo = raiz / fonte["arquivo"]
    procedencia = raiz / fonte["procedencia"]

    # Antes de olhar a fonte: o arquivo versionado ainda é o que a procedência
    # declara? Se não, alguém editou dado oficial à mão, e comparar contra a
    # fonte a partir daí só produziria confusão.
    declarado = sha_declarado(procedencia)
    real = hashlib.sha256(arquivo.read_bytes()).hexdigest() if arquivo.is_file() else None
    if real is None:
        return {"situacao": PROCEDENCIA_DIVERGENTE,
                "achados": [f"`{fonte['arquivo']}` não está no repositório"]}
    if declarado != real:
        return {"situacao": PROCEDENCIA_DIVERGENTE, "achados": [
            f"sha256 do arquivo versionado (`{real}`) não bate com o declarado "
            f"em `{fonte['procedencia']}` (`{declarado}`)"]}

    try:
        pagina = baixador(fonte["url"])
    except (urllib.error.URLError, OSError, TimeoutError) as erro:
        return {"situacao": INDISPONIVEL, "achados": [f"{type(erro).__name__}: {erro}"]}

    try:
        # `extrai_json` encerra o processo quando não encontra os dados — ótimo
        # para o script de download, inaceitável aqui: o monitor precisa
        # reportar a fonte quebrada, não morrer junto com ela.
        no_ar = baixar_tabelas.normaliza(baixar_tabelas.extrai_json(pagina))
    except SystemExit as erro:
        return {"situacao": FORMATO_INESPERADO, "achados": [str(erro)]}
    except (ValueError, KeyError, TypeError) as erro:
        return {"situacao": FORMATO_INESPERADO,
                "achados": [f"não consegui normalizar a tabela: {erro}"]}

    versionada = json.loads(arquivo.read_text(encoding="utf-8"))
    if versionada == no_ar:
        # `normaliza` garante ordem estável, então igualdade de estrutura é
        # igualdade byte a byte — e o sha256 declarado continua descrevendo a
        # tabela que está no ar.
        return {"situacao": SEM_MUDANCA, "achados": [], "sha256_declarado": declarado}

    return {"situacao": MUDOU, "achados": diferencas_da_tabela(versionada, no_ar),
            "sha256_declarado": declarado}


# --------------------------------------------------------------------------- #
# relatório
# --------------------------------------------------------------------------- #

CONFERIDORES = {
    "lista_de_documentos": lambda fonte, raiz, baixador:
        confere_lista_de_documentos(fonte, baixador),
    "tabela": confere_tabela,
}


def carrega_fontes(caminho: Path = FONTES) -> list[dict]:
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    return dados["fontes"]


def verifica(fontes: list[dict], raiz: Path = RAIZ, baixador=baixa,
             hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    resultados = []
    for fonte in fontes:
        conferidor = CONFERIDORES.get(fonte["tipo"])
        if conferidor is None:
            resultado = {"situacao": FORMATO_INESPERADO,
                         "achados": [f"tipo de fonte desconhecido: {fonte['tipo']}"]}
        else:
            resultado = conferidor(fonte, raiz, baixador)
        resultados.append({
            "id": fonte["id"], "nome": fonte["nome"], "url": fonte["url"],
            **resultado,
        })

    relatorio = {
        "detectado_em": hoje.isoformat(),
        "fontes": resultados,
        "precisa_de_humano": any(r["situacao"] != SEM_MUDANCA for r in resultados),
    }
    relatorio["alertas"] = [alerta(r, hoje) for r in resultados
                            if r["situacao"] != SEM_MUDANCA]
    return relatorio


# --------------------------------------------------------------------------- #
# issue para humano
# --------------------------------------------------------------------------- #

TITULOS = {
    MUDOU: "Fonte oficial mudou: {nome}",
    INDISPONIVEL: "Fonte oficial não respondeu: {nome}",
    FORMATO_INESPERADO: "Fonte oficial mudou de formato: {nome}",
    PROCEDENCIA_DIVERGENTE: "Dado versionado não bate com a procedência: {nome}",
}

# O que o humano precisa decidir, por situação. Issue sem checklist vira ruído
# e é fechada sem ação — que é o mesmo que não ter monitor.
CHECKLISTS = {
    MUDOU: [
        # Sem link relativo: corpo de issue no GitHub não resolve caminho do
        # repositório, e link quebrado num checklist é convite para pular o item.
        "Ler o documento **na fonte oficial**, com olho humano — sem extração "
        "automatizada de PDF (`docs/spec/05-camada-a-ibs-cbs.md` §3)",
        "Decidir se vira regra e com que severidade — Camada A (estrutural, pode "
        "ser `erro`) ou Camada B (código de rejeição, só entra confirmado)",
        "Atualizar a procedência do dado: `regras/tabelas/PROCEDENCIA.md` e/ou "
        "`regras/fontes.yaml` (`python scripts/monitor_fontes.py --semear`)",
        "Registrar no `CHANGELOG.md`: data de detecção, o que mudou e a partir "
        "de quando é obrigatório",
        "Se a conclusão for *nada muda*, fechar esta issue dizendo por quê — "
        "silêncio não é decisão",
    ],
    INDISPONIVEL: [
        "Conferir se a URL ainda é a oficial (portal migrado? endereço novo?)",
        "Se foi indisponibilidade passageira, fechar — a próxima execução confirma",
        "Se persistir, corrigir a URL em `regras/fontes.yaml`",
    ],
    FORMATO_INESPERADO: [
        "Abrir a página e ver o que mudou na estrutura",
        "Ajustar `scripts/monitor_fontes.py` e/ou `regras/fontes.yaml`",
        "Conferir **manualmente** se algum documento novo passou despercebido "
        "enquanto o monitor estava cego",
    ],
    PROCEDENCIA_DIVERGENTE: [
        "Descobrir quem alterou o arquivo e por quê — dado oficial não se edita "
        "à mão",
        "Rodar `python scripts/baixar_tabelas.py`, conferir o diff e atualizar a "
        "procedência",
        "Registrar no `CHANGELOG.md` se a mudança for legítima",
    ],
}

RODAPE = (
    "<sub>Aberta automaticamente por <code>scripts/monitor_fontes.py</code>. "
    "O monitor detecta e avisa; ele não lê o documento, não interpreta conteúdo "
    "e não sugere código — isso é trabalho de gente, e errar isso é pior que não "
    "ter monitor. Ver <code>docs/spec/04-manutencao.md</code>.</sub>"
)


def _marcador(resultado: dict) -> str:
    """Identidade da issue, para não abrir duplicata.

    Para mudança, o marcador inclui o conteúdo do achado: documento novo
    diferente é assunto diferente e merece issue própria. Para fonte fora do ar
    ou quebrada, é fixo por fonte — senão cada timeout com mensagem diferente
    abriria uma issue nova e a caixa viraria ruído.
    """
    base = f"monitor-fontes/{resultado['id']}/{resultado['situacao']}"
    if resultado["situacao"] in (INDISPONIVEL, FORMATO_INESPERADO):
        return base
    corpo = json.dumps(sorted(resultado["achados"]), ensure_ascii=False)
    return f"{base}/{hashlib.sha256(corpo.encode('utf-8')).hexdigest()[:12]}"


def alerta(resultado: dict, hoje: date) -> dict:
    situacao = resultado["situacao"]
    marcador = _marcador(resultado)
    achados = "\n".join(f"- {a}" for a in resultado["achados"])
    checklist = "\n".join(f"- [ ] {i}" for i in CHECKLISTS[situacao])

    corpo = f"""## O que mudou

{achados}

## Onde

| | |
|---|---|
| **Fonte** | {resultado['nome']} |
| **URL** | <{resultado['url']}> |
| **Identificador** | `{resultado['id']}` |
| **Detectado em** | {hoje.strftime('%d/%m/%Y')} |

## O que decidir — isto é trabalho de gente

{checklist}

---

{RODAPE}

<!-- {marcador} -->
"""
    return {
        "marcador": marcador,
        "titulo": TITULOS[situacao].format(nome=resultado["nome"]),
        "corpo": corpo,
        "rotulos": ["monitor-fontes"],
    }


# --------------------------------------------------------------------------- #
# semeadura
# --------------------------------------------------------------------------- #

def bloco_de_conhecidos(no_ar: dict[str, list[str]], hoje: date,
                        indentacao: str = "    ") -> str:
    linhas = [f"{indentacao}documentos_conhecidos:",
              f"{indentacao}  conferido_em: {hoje.isoformat()}"]
    for chave, titulos in no_ar.items():
        if not titulos:
            linhas.append(f"{indentacao}  {chave}: []")
            continue
        linhas.append(f"{indentacao}  {chave}:")
        # A lista inteira de uma vez, e não título a título: o `safe_dump` de um
        # escalar solto acrescenta o marcador `...` de fim de documento YAML.
        bruto = yaml.safe_dump(titulos, allow_unicode=True, default_flow_style=False,
                               width=10 ** 6, sort_keys=False)
        linhas.extend(f"{indentacao}    {l}" for l in bruto.strip().splitlines())
    return "\n".join(linhas) + "\n"


def substitui_bloco(texto: str, bloco: str, chave: str = "documentos_conhecidos") -> str:
    """Troca só o bloco da lista, por linha, preservando o resto do arquivo.

    Reescrever o YAML com `yaml.safe_dump` seria mais curto e apagaria todos os
    comentários — e num arquivo cuja tese é "regra é dado", o dado sem o porquê
    é dado morto.
    """
    linhas = texto.splitlines(keepends=True)
    inicio = next((i for i, l in enumerate(linhas) if l.strip() == f"{chave}:"), None)
    if inicio is None:
        raise SystemExit(f"não encontrei `{chave}:` em regras/fontes.yaml")
    recuo = len(linhas[inicio]) - len(linhas[inicio].lstrip())
    fim = len(linhas)
    for i in range(inicio + 1, len(linhas)):
        atual = linhas[i]
        if atual.strip() and (len(atual) - len(atual.lstrip())) <= recuo:
            fim = i
            break
    return "".join(linhas[:inicio]) + bloco + "".join(linhas[fim:])


def semeia(caminho: Path, raiz: Path, baixador, hoje: date) -> int:
    fontes = carrega_fontes(caminho)
    listas = [f for f in fontes if f["tipo"] == "lista_de_documentos"]
    if len(listas) != 1:
        raise SystemExit(
            "--semear só sabe lidar com exatamente uma fonte do tipo "
            f"`lista_de_documentos`; encontrei {len(listas)}"
        )
    fonte = listas[0]
    no_ar = titulos_por_secao(baixador(fonte["url"]), fonte["secoes"])
    texto = substitui_bloco(caminho.read_text(encoding="utf-8"),
                            bloco_de_conhecidos(no_ar, hoje))
    caminho.write_text(texto, encoding="utf-8", newline="\n")
    for chave, titulos in no_ar.items():
        print(f"{chave}: {len(titulos)} documentos")
    print(f"\ngravado em {caminho.relative_to(raiz)} — confira o diff antes de commitar.")
    return 0


# --------------------------------------------------------------------------- #
# linha de comando
# --------------------------------------------------------------------------- #

SINAIS = {SEM_MUDANCA: "ok  ", MUDOU: "MUDOU", INDISPONIVEL: "FORA ",
          FORMATO_INESPERADO: "FORMATO", PROCEDENCIA_DIVERGENTE: "PROCEDÊNCIA"}


def imprime(relatorio: dict) -> None:
    print(f"fontes conferidas em {relatorio['detectado_em']}\n")
    for fonte in relatorio["fontes"]:
        print(f"[{SINAIS[fonte['situacao']]}] {fonte['nome']}")
        print(f"          {fonte['url']}")
        for achado in fonte["achados"]:
            print(f"          · {achado}")
        print()
    if not relatorio["precisa_de_humano"]:
        print("nada a fazer — nenhuma fonte mudou.")
        return
    print(f"{len(relatorio['alertas'])} assunto(s) para um humano ler:")
    for a in relatorio["alertas"]:
        print(f"  · {a['titulo']}   ({a['marcador']})")


def main(argv: list[str] | None = None) -> int:
    # Saída sempre em UTF-8. No Windows, redirecionar stdout troca a codificação
    # para a página de código do console e o JSON sai com acento quebrado — o
    # `jq` do workflow engasgaria, e o título da nota técnica chegaria torto na
    # issue.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    analisador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analisador.add_argument("--json", action="store_true",
                            help="relatório e corpo das issues em JSON")
    analisador.add_argument("--semear", action="store_true",
                            help="grava em regras/fontes.yaml os documentos que "
                                 "estão no ar agora")
    argumentos = analisador.parse_args(argv)

    if argumentos.semear:
        return semeia(FONTES, RAIZ, baixa, date.today())

    relatorio = verifica(carrega_fontes(FONTES))
    if argumentos.json:
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    else:
        imprime(relatorio)
    # Sempre 0: fonte fora do ar é achado, não falha do monitor. Ver o cabeçalho
    # do módulo e o comentário em .github/workflows/monitor-fontes.yml.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
