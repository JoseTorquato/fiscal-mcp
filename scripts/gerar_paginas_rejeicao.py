"""Gera as páginas de docs/rejeicoes/ a partir de regras/rejeicoes.yaml.

Quem leva uma rejeição da SEFAZ vai ao Google e digita "rejeição 539 nfe". O que
está lá é fórum de 2015 e site de ERP vendendo. Estas páginas existem para ser a
resposta que faltava — e são para dev, não para contador: o que muda é qual campo
do XML editar e como reproduzir o diagnóstico, não o que a legislação diz.

O conteúdo é dado, não HTML escrito à mão. Quando o catálogo crescer, as páginas
crescem junto — e quando ele não tiver material para um exemplo honesto, a página
sai marcando a falta em vez de inventar XML fiscal errado.

    python scripts/gerar_paginas_rejeicao.py

Determinístico e offline: rodar duas vezes produz bytes idênticos, e nada aqui
abre rede. Isso é o que permite versionar a saída e testar que ela está em dia.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from fiscal_mcp import rejeicoes  # noqa: E402

SAIDA = RAIZ / "docs" / "rejeicoes"
SITE = "https://josetorquato.dev/fiscal-mcp/"
REPO = "https://github.com/JoseTorquato/fiscal-mcp"
# Título da issue já preenchido: quem chegou aqui levando uma rejeição não
# deveria precisar pensar no assunto do texto. O %C3%A7%C3%A3o é "ção".
NOVA_REJEICAO = f"{REPO}/issues/new?title=rejei%C3%A7%C3%A3o%20"


# ---- utilidades -----------------------------------------------------------

def esc(texto: str) -> str:
    return html.escape(str(texto), quote=True)


def limpa(valor: str | None) -> str:
    """Normaliza bloco de YAML: `>` dobra as linhas e deixa \\n no fim."""
    return " ".join((valor or "").split())


def titulo_curto(significa: str) -> str:
    """Título de aba não pode ter 100 caracteres — corta no travessão."""
    curto = limpa(significa).rstrip(".")
    return curto if len(curto) <= 56 else curto.split(" — ")[0]


def bloco(codigo_xml: str, destaques: list[str], variante: str) -> str:
    """<pre> do XML com as linhas relevantes marcadas.

    O destaque vem do catálogo como lista de trechos: assim quem edita o YAML
    decide o que importa, sem precisar mexer em HTML.
    """
    linhas = []
    for linha in codigo_xml.rstrip("\n").split("\n"):
        marcada = any(d in linha for d in destaques)
        conteudo = esc(linha) or "&nbsp;"
        if marcada:
            linhas.append(f'<span class="hl {variante}">{conteudo}</span>')
        else:
            linhas.append(conteudo)
    return "<pre>" + "\n".join(linhas) + "</pre>"


# ---- pedaços de página ----------------------------------------------------

def cabecalho(titulo: str, descricao: str, canonical: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(titulo)}</title>
<meta name="description" content="{esc(descricao)}">
<link rel="canonical" href="{esc(canonical)}">
<link rel="icon" type="image/svg+xml" href="../logo.svg">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(descricao)}">
<meta property="og:url" content="{esc(canonical)}">
<link rel="stylesheet" href="../estilo.css">
</head>
<body>

<header>
  <div class="wrap">
    <a class="brand" href="../"><img src="../logo.svg" alt="">fiscal<span class="suf">-mcp</span></a>
    <nav>
      <a href="../#usar">Usar</a>
      <a href="../#cobertura">Cobertura</a>
      <a href="./">Rejeições</a>
      <a href="https://pypi.org/project/fiscal-mcp/">PyPI</a>
      <a href="{REPO}">GitHub</a>
    </nav>
  </div>
</header>
"""


RODAPE = f"""
<footer>
  <div class="wrap">
    <div>
      <a class="brand" href="../"><img src="../logo.svg" alt="">fiscal<span class="suf">-mcp</span></a>
      <div style="margin-top:10px">MIT · feito por
        <a href="https://josetorquato.dev">José Torquato</a></div>
    </div>
    <div>
      <a href="../">Landing</a> ·
      <a href="./">Todas as rejeições</a> ·
      <a href="https://pypi.org/project/fiscal-mcp/">PyPI</a> ·
      <a href="{REPO}">GitHub</a>
    </div>
  </div>
</footer>

</body>
</html>
"""


def secao(numero: str, titulo: str, corpo: str, painel: bool = False) -> str:
    classe = ' class="painel"' if painel else ""
    return f"""
<section{classe}>
  <div class="wrap">
    <div class="shead"><span class="snum">{numero}<span style="color:var(--verde)">.</span></span>
      <h2 class="stitle">{esc(titulo)}</h2></div>
{corpo}
  </div>
</section>
"""


def selos(reversivel: bool) -> str:
    if reversivel:
        marca = ('<span class="selo selo-ok">reversível — corrija o documento '
                 'e transmita de novo</span>')
    else:
        marca = ('<span class="selo selo-nao">irreversível — o documento não '
                 'vira autorizado depois</span>')
    return f'<div class="selos">{marca}<span class="selo">NF-e · SEFAZ</span></div>'


def secao_xml(dados: dict, codigo: str) -> tuple[str, str]:
    """O miolo da página: XML errado e XML corrigido, ou a falta declarada.

    Devolve (título, corpo) porque "O XML, antes e depois" mente numa rejeição
    que não é de XML — e a página inteira depende de não mentir.
    """
    exemplo = dados.get("exemplo")
    if exemplo:
        destaques = exemplo.get("destaque") or []
        partes = [f'    <div class="texto"><p>{esc(limpa(exemplo.get("contexto")))}</p></div>',
                  '    <div class="par">',
                  '      <div><p class="rotulo rotulo-r">o que foi transmitido</p>',
                  "      " + bloco(exemplo["errado"], destaques, "err"),
                  "      </div>",
                  '      <div><p class="rotulo rotulo-g">o que a SEFAZ aceita</p>',
                  "      " + bloco(exemplo["corrigido"], destaques, "ok"),
                  "      </div>",
                  "    </div>"]
        if aviso := limpa(exemplo.get("aviso")):
            partes.append(f"""    <div class="aviso">
      <h3>Antes de sair copiando</h3>
      <p>{esc(aviso)}</p>
    </div>""")
        partes.append(
            '    <p class="nota" style="margin-top:22px;color:var(--dim);font-size:12px">'
            "Exemplo mínimo e fictício. Onde aparece CNPJ ou chave de acesso, o número "
            "não é de empresa nenhuma — nem passa no próprio dígito verificador.</p>"
        )
        return "O XML, antes e depois", "\n".join(partes)

    motivo = limpa(dados.get("sem_exemplo"))
    if motivo:
        return "Por que não há XML para corrigir", f"""    <div class="falta">
      <h3>Esta rejeição não tem XML errado para mostrar</h3>
      <p>{esc(motivo)}</p>
    </div>"""

    # Sem exemplo e sem justificativa: é lacuna, e some marcada como lacuna.
    return "O XML, antes e depois", f"""    <div class="falta">
      <h3>Falta o exemplo desta rejeição</h3>
      <p>O catálogo ainda não tem XML de antes e depois para a {esc(codigo)}.
      Inventar um seria pior do que a lacuna — exemplo fiscal errado circula e vira
      verdade. Se você já levou esta rejeição e sabe qual campo resolveu,
      <a href="{NOVA_REJEICAO}{esc(codigo)}">abra uma issue</a>: o catálogo é um
      YAML, e contribuir não exige entender o projeto inteiro.</p>
    </div>"""


def secao_comandos(codigo: str, dados: dict) -> str:
    saida = json.dumps(rejeicoes.explica(codigo), ensure_ascii=False, indent=2)
    partes = [
        '    <div class="texto"><p>Tudo aqui roda na sua máquina, sem certificado '
        "e sem enviar nada para lugar nenhum.</p></div>",
        '    <div class="cmd">',
        f"      <pre><span class=\"c\"># o que a SEFAZ quis dizer</span>\n"
        f"fiscal-mcp rejeicao {esc(codigo)}\n\n{esc(saida)}</pre>",
        "    </div>",
    ]
    for item in dados.get("verificar") or []:
        partes.append(f"""    <div class="cmd">
      <pre>{esc(item["comando"])}</pre>
      <p class="nota">{esc(limpa(item.get("nota")))}</p>
    </div>""")
    return "\n".join(partes)


# ---- páginas --------------------------------------------------------------

def pagina(codigo: str, dados: dict) -> str:
    significa = limpa(dados["significa"])
    acao = limpa(dados["acao"])
    causa = limpa(dados.get("causa"))
    titulo = f"Rejeição {codigo}: {titulo_curto(significa)} · fiscal-mcp"

    # A description promete só o que a página entrega: quem não tem exemplo não
    # anuncia exemplo na busca. Descrição que mente é clique frustrado.
    if dados.get("exemplo"):
        promessa = ("O que aconteceu, o XML errado e o corrigido, e o comando que "
                    "reproduz o diagnóstico offline.")
    elif dados.get("sem_exemplo"):
        promessa = ("O que aconteceu, o que fazer, e por que não há XML a corrigir "
                    "— diagnóstico offline, sem certificado.")
    else:
        promessa = "O que aconteceu, o que fazer, e como reproduzir o diagnóstico offline."
    descricao = f"Rejeição {codigo} da SEFAZ na NF-e: {significa} {promessa}"

    if causa:
        corpo_causa = f'    <div class="texto"><p>{esc(causa)}</p></div>'
    else:
        corpo_causa = f"""    <div class="falta">
      <h3>Falta a causa em linguagem de dev</h3>
      <p>O catálogo tem o significado e a ação, mas ainda não tem a explicação de
      o que costuma produzir a {esc(codigo)} numa integração.
      <a href="{NOVA_REJEICAO}{esc(codigo)}">Conte o seu caso</a>.</p>
    </div>"""

    titulo_xml, corpo_xml = secao_xml(dados, codigo)
    partes = [
        cabecalho(titulo, descricao, f"{SITE}rejeicoes/{codigo}.html"),
        f"""
<div class="dotted">
  <div class="wrap topo">
    <p class="trilha"><a href="../">fiscal-mcp</a> / <a href="./">rejeições</a> / {esc(codigo)}</p>
    <h1>Rejeição {esc(codigo)}</h1>
    <p class="lede">{esc(significa)}</p>
    {selos(bool(dados.get("reversivel", True)))}
  </div>
</div>
""",
        secao("01", "O que aconteceu", corpo_causa),
        secao("02", titulo_xml, corpo_xml, painel=True),
        secao("03", "O que fazer", f'    <div class="texto"><p>{esc(acao)}</p></div>'),
        secao("04", "Reproduzir sem transmitir", secao_comandos(codigo, dados),
              painel=True),
        secao("05", "A redação exata varia", f"""    <div class="texto">
      <p>A mensagem que chega da SEFAZ muda de UF para UF e de versão para versão do
      Manual de Orientação do Contribuinte — o que não muda é o código. O texto acima
      é o significado consolidado no catálogo do fiscal-mcp, não a transcrição
      literal de uma resposta.</p>
      <p>Se a sua veio diferente, ou se o campo que resolveu foi outro,
      <a href="{NOVA_REJEICAO}{esc(codigo)}">abra uma issue</a> — o catálogo é um
      <a href="{REPO}/blob/main/regras/rejeicoes.yaml">YAML de umas poucas linhas</a>,
      e é assim que ele fica melhor.</p>
      <p><a href="./">← todas as rejeições catalogadas</a></p>
    </div>"""),
        RODAPE,
    ]
    return "".join(partes)


def indice(catalogo: dict[str, dict]) -> str:
    titulo = "Rejeições da SEFAZ na NF-e: código, causa e o XML corrigido · fiscal-mcp"
    descricao = (
        "Catálogo de códigos de rejeição da NF-e explicados para quem integra: o que "
        "aconteceu, qual campo do XML mudar, e o comando que reproduz o diagnóstico "
        "offline."
    )

    linhas = []
    for codigo, dados in catalogo.items():
        marca = ("reversível" if dados.get("reversivel", True) else "irreversível")
        classe = "" if dados.get("reversivel", True) else ' style="color:var(--alerta)"'
        tem = "sim" if dados.get("exemplo") else "—"
        linhas.append(
            f"        <tr><td><a href=\"{esc(codigo)}.html\">{esc(codigo)}</a></td>"
            f"<td>{esc(limpa(dados['significa']))}</td>"
            f"<td{classe}>{marca}</td><td>{tem}</td></tr>"
        )

    tabela = "\n".join(linhas)
    com_exemplo = sum(1 for d in catalogo.values() if d.get("exemplo"))

    corpo_lista = f"""    <div class="tw">
    <table class="indice">
      <thead><tr><th>código</th><th>o que significa</th><th>reversível</th>
        <th>XML de exemplo</th></tr></thead>
      <tbody>
{tabela}
      </tbody>
    </table>
    </div>"""

    return "".join([
        cabecalho(titulo, descricao, f"{SITE}rejeicoes/"),
        f"""
<div class="dotted">
  <div class="wrap topo">
    <p class="trilha"><a href="../">fiscal-mcp</a> / rejeições</p>
    <h1>Rejeição da SEFAZ, explicada para quem integra</h1>
    <p class="lede">
      Uma página por código: o que de fato aconteceu, qual campo do XML mudar, e o
      comando que reproduz o diagnóstico na sua máquina — sem certificado, sem
      cadastro e sem transmitir nada.
    </p>
    <div class="selos"><span class="selo">{len(catalogo)} códigos catalogados</span>
      <span class="selo">{com_exemplo} com XML de antes e depois</span></div>
  </div>
</div>
""",
        secao("01", "O catálogo", corpo_lista, painel=True),
        secao("02", "Por que estas páginas existem", f"""    <div class="texto">
      <p>Rejeição chega tarde, custa uma transmissão e vem com mensagem críptica.
      Quem integra não quer saber o que a legislação diz — quer saber qual campo
      mudar e como reproduzir o erro antes de gastar outra transmissão.</p>
      <p>As páginas são geradas a partir do
      <a href="{REPO}/blob/main/regras/rejeicoes.yaml">mesmo catálogo</a> que a
      ferramenta <code>explicar_rejeicao</code> usa. Catálogo e documentação não
      divergem porque são a mesma coisa.</p>
      <p>O catálogo cobre as rejeições mais frequentes em integração nova, e está
      longe de ser a lista completa. Onde falta exemplo, a página diz que falta:
      inventar XML fiscal errado é pior do que a lacuna.</p>
    </div>
    <div class="aviso">
      <h3>O que estas páginas não são</h3>
      <ul>
        <li>Não são a transcrição literal da mensagem da SEFAZ — a redação muda por
          UF e por versão do Manual de Orientação do Contribuinte. O que não muda é
          o código.</li>
        <li>Não substituem o Manual de Orientação do Contribuinte nem a validação da
          própria SEFAZ.</li>
        <li>Levou um código que não está aqui?
          <a href="{NOVA_REJEICAO}">Abra uma issue</a> — é a contribuição mais
          barata que existe no projeto.</li>
      </ul>
    </div>"""),
        RODAPE,
    ])


# ---- geração --------------------------------------------------------------

def gerar() -> dict[str, str]:
    """Devolve {nome do arquivo: HTML}. Função pura — quem escreve é o main."""
    catalogo = {c: rejeicoes.catalogo()[c]
                for c in sorted(rejeicoes.catalogo(), key=lambda c: int(c))}
    paginas = {f"{codigo}.html": pagina(codigo, dados)
               for codigo, dados in catalogo.items()}
    paginas["index.html"] = indice(catalogo)
    return paginas


def main() -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)
    paginas = gerar()
    for nome, conteudo in sorted(paginas.items()):
        # newline="\n" para a saída não depender do sistema operacional de quem
        # rodou o script — senão "determinístico" vale só dentro de uma máquina.
        (SAIDA / nome).write_text(conteudo, encoding="utf-8", newline="\n")
    print(f"{len(paginas)} páginas em {SAIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
