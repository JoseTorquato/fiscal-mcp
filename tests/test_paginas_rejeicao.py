"""Testes das páginas de rejeição geradas em docs/rejeicoes/.

Duas preocupações, e as duas são de confiança:

1. **As páginas versionadas estão em dia com o catálogo.** O GitHub Pages serve
   arquivo estático — não há build no servidor. Se o HTML no repositório divergir
   do YAML, o site mente e ninguém percebe.

2. **Nenhum exemplo carrega documento que pareça real.** Um CNPJ que passa no
   dígito verificador dentro de uma página sobre erro fiscal é um convite a ser
   copiado. Aqui todo CNPJ e CPF precisa falhar no próprio dígito — quem copiar,
   não emite nada por engano.

    python -m pytest tests/test_paginas_rejeicao.py
"""

from __future__ import annotations

import importlib.util
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from fiscal_mcp import rejeicoes  # noqa: E402

PAGINAS = RAIZ / "docs" / "rejeicoes"


def _carrega_gerador():
    caminho = RAIZ / "scripts" / "gerar_paginas_rejeicao.py"
    spec = importlib.util.spec_from_file_location("gerar_paginas_rejeicao", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


gerador = _carrega_gerador()
CATALOGO = rejeicoes.catalogo()
TODAS = {p.name: p.read_text(encoding="utf-8") for p in sorted(PAGINAS.glob("*.html"))}


# ---- cobertura ------------------------------------------------------------

def test_toda_rejeicao_do_catalogo_tem_pagina():
    for codigo in CATALOGO:
        assert f"{codigo}.html" in TODAS, f"rejeição {codigo} sem página gerada"


def test_indice_lista_todas_as_rejeicoes():
    indice = TODAS["index.html"]
    for codigo in CATALOGO:
        assert f'href="{codigo}.html"' in indice, f"{codigo} fora do índice"


def test_nao_ha_pagina_orfa():
    """Rejeição removida do catálogo não pode deixar página para trás."""
    esperadas = {f"{c}.html" for c in CATALOGO} | {"index.html"}
    assert set(TODAS) == esperadas


# ---- determinismo e sincronia ---------------------------------------------

def test_geracao_e_determinista():
    assert gerador.gerar() == gerador.gerar()


def test_paginas_versionadas_estao_em_dia():
    """O que está no repositório é o que o script gera — byte a byte."""
    for nome, conteudo in gerador.gerar().items():
        assert nome in TODAS, f"{nome} não foi gerado no repositório"
        assert TODAS[nome] == conteudo, (
            f"{nome} está desatualizada: rode "
            "python scripts/gerar_paginas_rejeicao.py"
        )


def test_saida_nao_depende_do_sistema_operacional():
    """Escrita com newline='\\n': nada de \\r\\n vindo do Windows."""
    for pagina in PAGINAS.glob("*.html"):
        assert b"\r\n" not in pagina.read_bytes(), f"{pagina.name} com quebra de linha CRLF"


# ---- conteúdo obrigatório -------------------------------------------------

def test_pagina_traz_codigo_significado_e_acao():
    for codigo, dados in CATALOGO.items():
        html = TODAS[f"{codigo}.html"]
        assert f"Rejeição {codigo}" in html
        assert " ".join(dados["significa"].split()) in html
        assert " ".join(dados["acao"].split()) in html


def test_pagina_traz_o_comando_de_diagnostico():
    for codigo in CATALOGO:
        assert f"fiscal-mcp rejeicao {codigo}" in TODAS[f"{codigo}.html"]


def test_pagina_diz_se_a_rejeicao_e_reversivel():
    for codigo, dados in CATALOGO.items():
        html = TODAS[f"{codigo}.html"]
        if dados.get("reversivel", True):
            assert "selo-ok" in html and "reversível" in html
        else:
            assert "selo-nao" in html and "irreversível" in html


def test_exemplo_mostra_errado_e_corrigido_com_destaque():
    with_exemplo = [c for c, d in CATALOGO.items() if d.get("exemplo")]
    assert with_exemplo, "nenhuma rejeição com exemplo — o catálogo regrediu"
    for codigo in with_exemplo:
        html = TODAS[f"{codigo}.html"]
        assert "o que foi transmitido" in html
        assert "o que a SEFAZ aceita" in html
        assert 'class="hl err"' in html, f"{codigo} sem destaque no XML errado"
        assert 'class="hl ok"' in html, f"{codigo} sem destaque no XML corrigido"


def test_sem_exemplo_a_pagina_marca_a_falta():
    """Página incompleta é aceitável; página que finge estar completa não é."""
    for codigo, dados in CATALOGO.items():
        if dados.get("exemplo"):
            continue
        html = TODAS[f"{codigo}.html"]
        assert 'class="falta"' in html, f"{codigo} não marca a ausência de exemplo"
        if not dados.get("sem_exemplo"):
            assert "issues/new" in html, f"{codigo} não convida a contribuir"


def test_pagina_volta_para_a_landing_e_para_o_repositorio():
    for nome, html in TODAS.items():
        assert 'href="../"' in html, f"{nome} sem volta para a landing"
        assert "github.com/JoseTorquato/fiscal-mcp" in html, f"{nome} sem link do repo"


# ---- encontrável ----------------------------------------------------------

def test_metadados_de_busca_em_toda_pagina():
    for nome, html in TODAS.items():
        assert re.search(r"<title>.{10,}</title>", html), f"{nome} sem título"
        assert re.search(r'<meta name="description" content=".{40,}">', html), \
            f"{nome} sem description"
        alvo = "" if nome == "index.html" else nome
        esperado = ('<link rel="canonical" '
                    f'href="https://josetorquato.dev/fiscal-mcp/rejeicoes/{alvo}">')
        assert esperado in html, f"{nome} sem canonical correto"


def test_titulo_cabe_na_aba():
    for nome, html in TODAS.items():
        titulo = re.search(r"<title>(.*?)</title>", html).group(1)
        assert len(titulo) <= 90, f"{nome} com título de {len(titulo)} caracteres"


def test_conteudo_nao_depende_de_javascript():
    for nome, html in TODAS.items():
        assert "<script" not in html.lower(), f"{nome} depende de script"
        assert "http://" not in html, f"{nome} com recurso em http puro"


def test_nao_carrega_recurso_externo():
    """Sem CDN: a página precisa abrir igual daqui a cinco anos."""
    externos = re.findall(r'(?:src|href)="(https?://[^"]+)"', "\n".join(TODAS.values()))
    for url in externos:
        assert not url.endswith((".css", ".js", ".woff", ".woff2")), \
            f"recurso externo embutido: {url}"


# ---- nenhum documento que pareça real -------------------------------------

def _dv_cnpj(base12: str) -> str:
    """Módulo 11 do CNPJ — mesma família do DV da chave (fiscal_mcp.chave)."""
    def digito(numeros: list[int], pesos: list[int]) -> int:
        resto = sum(n * p for n, p in zip(numeros, pesos)) % 11
        return 0 if resto < 2 else 11 - resto

    d = [int(c) for c in base12]
    d1 = digito(d, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = digito(d + [d1], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return f"{d1}{d2}"


def _dv_cpf(base9: str) -> str:
    d = [int(c) for c in base9]
    resto = (sum(x * (10 - i) for i, x in enumerate(d)) * 10) % 11
    d1 = 0 if resto == 10 else resto
    resto = (sum(x * (11 - i) for i, x in enumerate(d + [d1])) * 10) % 11
    d2 = 0 if resto == 10 else resto
    return f"{d1}{d2}"


def _documentos_na_pagina(html: str) -> list[str]:
    """Todo candidato a CNPJ/CPF: solto, com máscara, ou dentro de uma chave."""
    achados = []
    for corrida in re.findall(r"\d+", html):
        if len(corrida) in (11, 14):
            achados.append(corrida)
        if len(corrida) == 44:
            # posições 7 a 20 da chave de acesso são o CNPJ do emitente
            achados.append(corrida[6:20])
    for mascarado in re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", html):
        achados.append(re.sub(r"\D", "", mascarado))
    for mascarado in re.findall(r"\d{3}\.\d{3}\.\d{3}-\d{2}", html):
        achados.append(re.sub(r"\D", "", mascarado))
    return achados


def test_nenhum_cnpj_ou_cpf_passa_no_digito_verificador():
    encontrados = 0
    for nome, html in TODAS.items():
        for documento in _documentos_na_pagina(html):
            encontrados += 1
            if len(documento) == 14:
                assert _dv_cnpj(documento[:12]) != documento[12:], (
                    f"{nome} tem o CNPJ {documento}, que passa no dígito "
                    "verificador — exemplo precisa ser obviamente fictício"
                )
            else:
                assert _dv_cpf(documento[:9]) != documento[9:], (
                    f"{nome} tem o CPF {documento}, que passa no dígito verificador"
                )
    assert encontrados, "nenhum documento examinado — a extração parou de funcionar"


def test_o_teste_de_documento_reconhece_um_valido():
    """Sem isto, o teste acima passaria mesmo se a extração quebrasse."""
    assert _dv_cnpj("123456780001") == "95"
    assert _dv_cpf("123456789") == "09"
    assert "12345678000195" in _documentos_na_pagina("<p>12345678000195</p>")
    assert "12345678000100" in _documentos_na_pagina(
        "43260812345678000100550010000012341123456783")


# ---- HTML bem formado -----------------------------------------------------

VAZIAS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
          "meta", "param", "source", "track", "wbr"}


class _Equilibrio(HTMLParser):
    """Confere abre/fecha. Falta uma <div> e o resto da página vai junto."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pilha: list[str] = []
        self.erros: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VAZIAS:
            self.pilha.append(tag)

    def handle_endtag(self, tag):
        if tag in VAZIAS:
            return
        if not self.pilha:
            self.erros.append(f"</{tag}> sem abertura")
        elif self.pilha[-1] != tag:
            self.erros.append(f"</{tag}> fecha depois de <{self.pilha[-1]}>")
        else:
            self.pilha.pop()


def test_html_bem_formado():
    for nome, html in TODAS.items():
        parser = _Equilibrio()
        parser.feed(html)
        parser.close()
        assert not parser.erros, f"{nome}: {parser.erros[:3]}"
        assert not parser.pilha, f"{nome}: tags abertas sem fechar: {parser.pilha}"


def test_estrutura_minima_de_documento():
    for nome, html in TODAS.items():
        assert html.startswith("<!doctype html>\n<html lang=\"pt-BR\">"), nome
        assert html.count("<h1") == 1, f"{nome} precisa de exatamente um h1"
        assert '<meta name="viewport"' in html, f"{nome} sem viewport"
        assert '<link rel="stylesheet" href="../estilo.css">' in html, nome
        assert html.rstrip().endswith("</html>"), nome


def test_toda_classe_usada_tem_estilo():
    """Classe sem regra no CSS é seção que some — e ninguém percebe olhando o HTML."""
    estilo = (RAIZ / "docs" / "estilo.css").read_text(encoding="utf-8")
    usadas = set()
    for atributo in re.findall(r'class="([^"]+)"', "\n".join(TODAS.values())):
        usadas.update(atributo.split())
    for classe in sorted(usadas):
        assert f".{classe}" in estilo, f"classe {classe} usada sem estilo definido"


def test_estilo_compartilhado_com_a_landing_existe():
    """As páginas apontam para ../estilo.css — e a landing usa o mesmo arquivo."""
    estilo = (RAIZ / "docs" / "estilo.css").read_text(encoding="utf-8")
    assert "--verde:#22C55E" in estilo
    landing = (RAIZ / "docs" / "index.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="estilo.css">' in landing
    assert 'href="rejeicoes/"' in landing, "a landing não leva às páginas de rejeição"


if __name__ == "__main__":
    # Mesmo runner do test_fatia_zero.py: a CI roda os testes sem instalar
    # pytest, e não vale trocar uma dependência de produção por uma de teste.
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok    {nome}")
            except AssertionError as e:
                falhas += 1
                print(f"  FALHA {nome}: {e}")
            except Exception as e:  # noqa: BLE001
                falhas += 1
                print(f"  ERRO  {nome}: {type(e).__name__}: {e}")
    print(f"\n  {falhas} falha(s)\n")
    raise SystemExit(1 if falhas else 0)
