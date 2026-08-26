"""Testes do monitor de fontes oficiais.

**Nenhum destes testes toca a rede.** O monitor existe justamente porque site de
terceiro cai e muda de formato — se a suíte dependesse do Portal da NF-e estar
no ar, o build de quem usa o pacote quebraria por causa de manutenção da SEFAZ.
Toda checagem aqui roda contra HTML guardado em `tests/dados/`, capturado da
fonte real e com a origem declarada no cabeçalho de cada arquivo.

O outro contrato que estes testes guardam é o de que o monitor **alerta um
humano e para por aí**: ele não interpreta o documento, e a issue que ele abre
precisa ser útil sozinha — com o que mudou, onde, quando e o que decidir. Issue
sem checklist é fechada sem ação, que é o mesmo que não ter monitor.
"""

from __future__ import annotations

import hashlib
import json
import socket
import sys
import urllib.error
from datetime import date
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parent.parent
DADOS = Path(__file__).resolve().parent / "dados"
sys.path.insert(0, str(RAIZ / "scripts"))

import monitor_fontes as monitor  # noqa: E402

HOJE = date(2026, 8, 25)

SECOES = {"Documentos vigentes": "vigentes", "Documentos não vigentes": "nao_vigentes"}

PORTAL = (DADOS / "portal-notas-tecnicas.html").read_text(encoding="utf-8")
PORTAL_REMONTADO = (DADOS / "portal-notas-tecnicas-remontado.html").read_text(encoding="utf-8")
SVRS = (DADOS / "svrs-classificacao-tributaria.html").read_text(encoding="utf-8")
SVRS_MUDOU = (DADOS / "svrs-classificacao-tributaria-mudou.html").read_text(encoding="utf-8")


def servindo(pagina: str):
    """Um `baixador` que devolve sempre a mesma página, sem abrir socket."""
    return lambda _url: pagina


def caindo(erro: Exception):
    def baixador(_url):
        raise erro
    return baixador


# --------------------------------------------------------------------------- #
# leitura da página de notas técnicas
# --------------------------------------------------------------------------- #

def test_le_as_duas_secoes_do_portal():
    achados = monitor.titulos_por_secao(PORTAL, SECOES)
    assert len(achados["vigentes"]) == 5
    assert len(achados["nao_vigentes"]) == 3
    assert "Nota Técnica 2025.002 v.1.51 - Publicada em 04/08/2026" in achados["vigentes"]


def test_titulo_com_espaco_nao_separavel_normaliza():
    """O portal alterna `Nota Técnica` e `Nota&nbsp;Técnica` na mesma página.

    Sem normalizar, o mesmo documento entraria como novo toda semana e o monitor
    viraria a coisa que ninguém lê.
    """
    achados = monitor.titulos_por_secao(PORTAL, SECOES)
    assert ("Nota Técnica 2025.001. v.1.03 - Corrigido - Publicada em 29/09/2025"
            in achados["vigentes"])
    assert all(" " not in t for lista in achados.values() for t in lista)


def test_pagina_remontada_nao_vira_lista_vazia():
    """Concluir "nada mudou" de uma página que o monitor não sabe mais ler é a
    falha mais cara possível: ele fica cego exatamente quando a fonte se mexe."""
    with pytest.raises(monitor.FormatoInesperado):
        monitor.titulos_por_secao(PORTAL_REMONTADO, SECOES)


def test_secao_nao_declarada_no_yaml_e_achado():
    with pytest.raises(monitor.FormatoInesperado, match="não declarada"):
        monitor.titulos_por_secao(PORTAL, {"Documentos vigentes": "vigentes"})


def test_secao_que_sumiu_da_pagina_e_achado():
    secoes = {**SECOES, "Documentos revogados": "revogados"}
    with pytest.raises(monitor.FormatoInesperado, match="sumiu"):
        monitor.titulos_por_secao(PORTAL, secoes)


# --------------------------------------------------------------------------- #
# fonte do tipo lista de documentos
# --------------------------------------------------------------------------- #

def fonte_de_documentos(conhecidos: dict) -> dict:
    return {
        "id": "notas-tecnicas-nfe",
        "nome": "Notas Técnicas do Portal da NF-e",
        "tipo": "lista_de_documentos",
        "url": "https://exemplo.invalido/notas",
        "secoes": SECOES,
        "documentos_conhecidos": conhecidos,
    }


def tudo_conhecido() -> dict:
    achados = monitor.titulos_por_secao(PORTAL, SECOES)
    return {"conferido_em": "2026-08-25", **achados}


def test_nada_muda_quando_todos_os_documentos_ja_sao_conhecidos():
    resultado = monitor.confere_lista_de_documentos(
        fonte_de_documentos(tudo_conhecido()), servindo(PORTAL))
    assert resultado["situacao"] == monitor.SEM_MUDANCA
    assert resultado["achados"] == []
    assert resultado["documentos_no_ar"] == 8


def test_documento_novo_e_o_sinal_principal():
    conhecidos = tudo_conhecido()
    conhecidos["vigentes"] = [t for t in conhecidos["vigentes"] if "2026.007" not in t]

    resultado = monitor.confere_lista_de_documentos(
        fonte_de_documentos(conhecidos), servindo(PORTAL))
    assert resultado["situacao"] == monitor.MUDOU
    assert resultado["achados"] == [
        "documento novo em `vigentes`: Nota Técnica 2026.007 v.1.00 - Publicada em 04/08/2026"
    ]


def test_documento_que_sai_de_vigencia_tambem_e_achado():
    conhecidos = tudo_conhecido()
    saiu = conhecidos["nao_vigentes"][0]
    conhecidos["nao_vigentes"] = conhecidos["nao_vigentes"][1:]
    conhecidos["vigentes"] = conhecidos["vigentes"] + [saiu]

    resultado = monitor.confere_lista_de_documentos(
        fonte_de_documentos(conhecidos), servindo(PORTAL))
    assert resultado["situacao"] == monitor.MUDOU
    assert resultado["achados"] == [f"mudou de `vigentes` para `nao_vigentes`: {saiu}"]


def test_documento_que_some_da_pagina_e_achado():
    fantasma = "Nota Técnica 2099.001 - Publicada em 01/01/2099"
    conhecidos = tudo_conhecido()
    conhecidos["vigentes"] = conhecidos["vigentes"] + [fantasma]

    resultado = monitor.confere_lista_de_documentos(
        fonte_de_documentos(conhecidos), servindo(PORTAL))
    assert resultado["situacao"] == monitor.MUDOU
    assert resultado["achados"] == [f"sumiu de `vigentes`: {fantasma}"]


def test_lista_vazia_faz_tudo_ser_novo_e_nao_quebra():
    """O estado inicial, antes da primeira semeadura, precisa ser legível."""
    resultado = monitor.confere_lista_de_documentos(
        fonte_de_documentos({"vigentes": [], "nao_vigentes": []}), servindo(PORTAL))
    assert resultado["situacao"] == monitor.MUDOU
    assert len(resultado["achados"]) == 8


def test_fonte_fora_do_ar_nao_vira_nada_mudou():
    resultado = monitor.confere_lista_de_documentos(
        fonte_de_documentos(tudo_conhecido()),
        caindo(urllib.error.URLError("conexão recusada")))
    assert resultado["situacao"] == monitor.INDISPONIVEL
    assert "URLError" in resultado["achados"][0]


def test_portal_remontado_vira_formato_inesperado():
    resultado = monitor.confere_lista_de_documentos(
        fonte_de_documentos(tudo_conhecido()), servindo(PORTAL_REMONTADO))
    assert resultado["situacao"] == monitor.FORMATO_INESPERADO


# --------------------------------------------------------------------------- #
# fonte do tipo tabela
# --------------------------------------------------------------------------- #

PROCEDENCIA_MODELO = """# Procedência das tabelas

## `cst-cclasstrib.json`

| | |
|---|---|
| **Origem** | Portal da Conformidade Fácil (SVRS) |
| **sha256** | `{sha}` |
"""


def fonte_de_tabela(tmp_path: Path, pagina_versionada: str = SVRS) -> tuple[dict, Path]:
    """Monta uma raiz de repositório de mentira, coerente com a página dada.

    A tabela versionada é gerada com o mesmo `normaliza` do script de download —
    é justamente a reutilização que se quer provar.
    """
    tabela = monitor.baixar_tabelas.normaliza(
        monitor.baixar_tabelas.extrai_json(pagina_versionada))
    texto = json.dumps(tabela, ensure_ascii=False, indent=2, sort_keys=False) + "\n"

    destino = tmp_path / "regras" / "tabelas"
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / "cst-cclasstrib.json"
    arquivo.write_text(texto, encoding="utf-8", newline="\n")
    sha = hashlib.sha256(arquivo.read_bytes()).hexdigest()
    (destino / "PROCEDENCIA.md").write_text(
        PROCEDENCIA_MODELO.format(sha=sha), encoding="utf-8", newline="\n")

    fonte = {
        "id": "tabela-classificacao-tributaria",
        "nome": "Tabela de Classificação Tributária (CST × cClassTrib) — SVRS",
        "tipo": "tabela",
        "url": "https://exemplo.invalido/tabela",
        "arquivo": "regras/tabelas/cst-cclasstrib.json",
        "procedencia": "regras/tabelas/PROCEDENCIA.md",
    }
    return fonte, arquivo


def test_tabela_igual_a_versionada_nao_alerta(tmp_path):
    fonte, _ = fonte_de_tabela(tmp_path)
    resultado = monitor.confere_tabela(fonte, tmp_path, servindo(SVRS))
    assert resultado["situacao"] == monitor.SEM_MUDANCA
    assert resultado["achados"] == []


def test_tabela_que_mudou_diz_o_que_mudou(tmp_path):
    """A issue precisa poupar o humano de refazer o trabalho do monitor."""
    fonte, _ = fonte_de_tabela(tmp_path)
    resultado = monitor.confere_tabela(fonte, tmp_path, servindo(SVRS_MUDOU))
    assert resultado["situacao"] == monitor.MUDOU

    achados = "\n".join(resultado["achados"])
    assert "publicação declarada pela fonte: 2026-06-22 → 2026-08-10" in achados
    assert "cClassTrib novo (1): 000003" in achados
    assert "cClassTrib alterado (1): 200001" in achados


def test_arquivo_editado_a_mao_e_alertado_antes_de_olhar_a_fonte(tmp_path):
    """sha256 divergente = alguém mexeu em dado oficial à mão. Comparar contra a
    fonte a partir daí só produziria confusão."""
    fonte, arquivo = fonte_de_tabela(tmp_path)
    arquivo.write_text(arquivo.read_text(encoding="utf-8").replace("000001", "000009"),
                       encoding="utf-8", newline="\n")

    def nunca(_url):
        raise AssertionError("não devia ter ido à rede com a procedência divergente")

    resultado = monitor.confere_tabela(fonte, tmp_path, nunca)
    assert resultado["situacao"] == monitor.PROCEDENCIA_DIVERGENTE


def test_tabela_ausente_e_alertada(tmp_path):
    fonte, arquivo = fonte_de_tabela(tmp_path)
    arquivo.unlink()
    resultado = monitor.confere_tabela(fonte, tmp_path, servindo(SVRS))
    assert resultado["situacao"] == monitor.PROCEDENCIA_DIVERGENTE


def test_portal_da_svrs_sem_os_dados_nao_derruba_o_monitor(tmp_path):
    """`extrai_json` encerra o processo quando não acha `dadosOriginais` — ótimo
    para o script de download, inaceitável para quem precisa reportar."""
    fonte, _ = fonte_de_tabela(tmp_path)
    resultado = monitor.confere_tabela(fonte, tmp_path, servindo("<html>manutenção</html>"))
    assert resultado["situacao"] == monitor.FORMATO_INESPERADO


def test_svrs_fora_do_ar_nao_vira_nada_mudou(tmp_path):
    fonte, _ = fonte_de_tabela(tmp_path)
    resultado = monitor.confere_tabela(fonte, tmp_path, caindo(TimeoutError("tempo esgotado")))
    assert resultado["situacao"] == monitor.INDISPONIVEL


def test_normalizacao_da_tabela_e_a_do_script_de_download(tmp_path):
    """Reuso, não cópia: os campos que o script descarta precisam sair aqui também."""
    _, arquivo = fonte_de_tabela(tmp_path)
    tabela = json.loads(arquivo.read_text(encoding="utf-8"))

    descartados = set(tabela["campos_descartados"])
    assert {"CstNavigation", "Anexos", "CtrDthInc", "NroAnexo"} <= descartados
    for grupo in tabela["cst"]:
        assert not descartados & set(grupo)
        for linha in grupo["ClassificacoesTributarias"]:
            assert not descartados & set(linha)
            assert linha["DthPublicacao"] == "2026-06-22", "data truncada para AAAA-MM-DD"


# --------------------------------------------------------------------------- #
# o relatório e a issue
# --------------------------------------------------------------------------- #

def relatorio_com_documento_novo(tmp_path) -> dict:
    conhecidos = tudo_conhecido()
    conhecidos["vigentes"] = [t for t in conhecidos["vigentes"] if "2026.007" not in t]
    fonte_tabela, _ = fonte_de_tabela(tmp_path)
    return monitor.verifica(
        [fonte_tabela, fonte_de_documentos(conhecidos)],
        raiz=tmp_path,
        baixador=lambda url: SVRS if "tabela" in url else PORTAL,
        hoje=HOJE,
    )


def test_relatorio_separa_o_que_precisa_de_humano(tmp_path):
    relatorio = relatorio_com_documento_novo(tmp_path)
    assert relatorio["precisa_de_humano"] is True
    assert relatorio["detectado_em"] == "2026-08-25"
    assert [f["situacao"] for f in relatorio["fontes"]] == [
        monitor.SEM_MUDANCA, monitor.MUDOU]
    assert len(relatorio["alertas"]) == 1, "fonte sem mudança não vira issue"


def test_a_issue_e_util_sozinha(tmp_path):
    """Sem o que mudou, onde, quando e o que decidir, a issue é ruído."""
    alerta = relatorio_com_documento_novo(tmp_path)["alertas"][0]
    corpo = alerta["corpo"]

    assert "Nota Técnica 2026.007 v.1.00" in corpo, "o que mudou"
    assert "https://exemplo.invalido/notas" in corpo, "a URL da fonte"
    assert "25/08/2026" in corpo, "a data de detecção"
    assert corpo.count("- [ ] ") >= 4, "o checklist do que o humano precisa decidir"
    assert "CHANGELOG" in corpo and "PROCEDENCIA" in corpo
    assert alerta["marcador"] in corpo, "o marcador viaja no corpo, senão não há dedupe"


def test_a_issue_diz_que_quem_le_a_nota_tecnica_e_gente(tmp_path):
    """O contrato do C2, escrito onde o leitor da issue vai ver."""
    corpo = relatorio_com_documento_novo(tmp_path)["alertas"][0]["corpo"]
    assert "sem extração" in corpo
    assert "não interpreta conteúdo" in corpo


def test_marcador_e_estavel_para_o_mesmo_achado(tmp_path):
    primeiro = relatorio_com_documento_novo(tmp_path)["alertas"][0]["marcador"]
    segundo = relatorio_com_documento_novo(tmp_path)["alertas"][0]["marcador"]
    assert primeiro == segundo, "achado igual precisa cair na mesma issue, não abrir outra"


def test_achado_diferente_e_issue_diferente():
    conhecidos = tudo_conhecido()
    um = monitor.alerta({**fonte_de_documentos(conhecidos),
                         "situacao": monitor.MUDOU, "achados": ["documento novo: A"]}, HOJE)
    outro = monitor.alerta({**fonte_de_documentos(conhecidos),
                            "situacao": monitor.MUDOU, "achados": ["documento novo: B"]}, HOJE)
    assert um["marcador"] != outro["marcador"]


def test_fonte_fora_do_ar_tem_marcador_fixo():
    """Cada timeout traz uma mensagem diferente. Se o marcador dependesse dela,
    o monitor abriria uma issue nova por semana e ninguém leria mais nenhuma."""
    base = fonte_de_documentos(tudo_conhecido())
    um = monitor.alerta({**base, "situacao": monitor.INDISPONIVEL,
                         "achados": ["TimeoutError: 30s"]}, HOJE)
    outro = monitor.alerta({**base, "situacao": monitor.INDISPONIVEL,
                            "achados": ["URLError: [Errno 111]"]}, HOJE)
    assert um["marcador"] == outro["marcador"]
    assert um["marcador"] == "monitor-fontes/notas-tecnicas-nfe/indisponivel"


def test_todas_as_situacoes_tem_checklist():
    """Situação nova sem checklist quebraria a geração da issue em produção —
    e produção aqui é uma vez por semana, de madrugada, sem ninguém olhando."""
    for situacao in (monitor.MUDOU, monitor.INDISPONIVEL,
                     monitor.FORMATO_INESPERADO, monitor.PROCEDENCIA_DIVERGENTE):
        assert monitor.CHECKLISTS[situacao] and monitor.TITULOS[situacao]


def test_tipo_de_fonte_desconhecido_alerta_em_vez_de_explodir(tmp_path):
    relatorio = monitor.verifica(
        [{"id": "x", "nome": "Fonte torta", "tipo": "planilha", "url": "https://x.invalido"}],
        raiz=tmp_path, baixador=servindo(""), hoje=HOJE)
    assert relatorio["fontes"][0]["situacao"] == monitor.FORMATO_INESPERADO


# --------------------------------------------------------------------------- #
# semeadura de regras/fontes.yaml
# --------------------------------------------------------------------------- #

def test_semeadura_preserva_os_comentarios_do_arquivo(tmp_path):
    """Dado versionado sem o porquê é dado morto. Reescrever o YAML com
    `safe_dump` seria mais curto e apagaria todo comentário do arquivo."""
    caminho = tmp_path / "fontes.yaml"
    caminho.write_text((RAIZ / "regras" / "fontes.yaml").read_text(encoding="utf-8"),
                       encoding="utf-8", newline="\n")

    monitor.semeia(caminho, tmp_path, servindo(PORTAL), HOJE)

    texto = caminho.read_text(encoding="utf-8")
    assert "# Fontes oficiais monitoradas" in texto
    assert "# O monitor não interpreta nada do que encontra." in texto

    dados = yaml.safe_load(texto)
    conhecidos = dados["fontes"][1]["documentos_conhecidos"]
    assert conhecidos["conferido_em"] == date(2026, 8, 25)
    assert len(conhecidos["vigentes"]) == 5 and len(conhecidos["nao_vigentes"]) == 3


def test_semear_e_depois_conferir_nao_acha_nada(tmp_path):
    """O ciclo completo: semeou o que estava no ar, a conferida seguinte cala."""
    caminho = tmp_path / "fontes.yaml"
    caminho.write_text((RAIZ / "regras" / "fontes.yaml").read_text(encoding="utf-8"),
                       encoding="utf-8", newline="\n")
    monitor.semeia(caminho, tmp_path, servindo(PORTAL), HOJE)

    fonte = monitor.carrega_fontes(caminho)[1]
    resultado = monitor.confere_lista_de_documentos(fonte, servindo(PORTAL))
    assert resultado["situacao"] == monitor.SEM_MUDANCA


def test_bloco_semeado_nao_carrega_marcador_de_fim_de_documento():
    bloco = monitor.bloco_de_conhecidos({"vigentes": ["Nota Técnica 2026.001"]}, HOJE)
    assert "..." not in bloco
    assert yaml.safe_load(bloco.replace("    ", "", 1))


# --------------------------------------------------------------------------- #
# o arquivo de fontes versionado
# --------------------------------------------------------------------------- #

def test_fontes_yaml_e_legivel_e_coerente():
    fontes = monitor.carrega_fontes(RAIZ / "regras" / "fontes.yaml")
    identificadores = [f["id"] for f in fontes]
    assert len(identificadores) == len(set(identificadores))
    for fonte in fontes:
        assert fonte["tipo"] in monitor.CONFERIDORES
        assert fonte["url"].startswith("https://")
        assert fonte["nome"]


def test_fontes_yaml_aponta_para_a_procedencia_que_existe():
    for fonte in monitor.carrega_fontes(RAIZ / "regras" / "fontes.yaml"):
        if fonte["tipo"] != "tabela":
            continue
        assert (RAIZ / fonte["arquivo"]).is_file()
        assert monitor.sha_declarado(RAIZ / fonte["procedencia"])


def test_nenhum_documento_conhecido_esta_duplicado():
    """Título duplicado esconderia um documento: o segundo nunca seria "novo"."""
    for fonte in monitor.carrega_fontes(RAIZ / "regras" / "fontes.yaml"):
        if fonte["tipo"] != "lista_de_documentos":
            continue
        conhecidos = fonte["documentos_conhecidos"]
        titulos = [t for v in conhecidos.values() if isinstance(v, list) for t in v]
        assert titulos, "a lista precisa estar semeada, senão tudo é novidade"
        assert len(titulos) == len(set(titulos))
        assert set(conhecidos) - {"conferido_em"} == set(fonte["secoes"].values())


# --------------------------------------------------------------------------- #
# o monitor fora do caminho crítico
# --------------------------------------------------------------------------- #

FLUXO = RAIZ / ".github" / "workflows" / "monitor-fontes.yml"


def test_o_monitor_nao_roda_no_ci_de_push_nem_de_pr():
    """Não negociável: indisponibilidade de site de terceiro não pode quebrar o
    build de ninguém. Mesma regra da tabela (regras/tabelas/PROCEDENCIA.md)."""
    fluxo = yaml.safe_load(FLUXO.read_text(encoding="utf-8"))
    # `on:` vira `True` no YAML 1.1 do PyYAML — é a chave, não um booleano.
    gatilhos = fluxo.get("on", fluxo.get(True))
    assert set(gatilhos) == {"schedule", "workflow_dispatch"}
    assert fluxo["permissions"] == {"contents": "read", "issues": "write"}


def test_a_suite_nao_chama_o_monitor_agendado():
    testes = yaml.safe_load((RAIZ / ".github" / "workflows" / "testes.yml")
                            .read_text(encoding="utf-8"))
    passos = json.dumps(testes, ensure_ascii=False)
    assert "monitor_fontes" not in passos


def test_nenhum_teste_deste_arquivo_abriu_socket(monkeypatch):
    """Garantia de zero-rede, no mesmo espírito de test_tabelas.py."""
    def proibido(*_a, **_k):
        raise AssertionError("o monitor tentou abrir socket num teste")

    monkeypatch.setattr(socket.socket, "connect", proibido)
    monkeypatch.setattr(socket, "create_connection", proibido)

    relatorio = monitor.verifica(
        [fonte_de_documentos(tudo_conhecido())], raiz=RAIZ,
        baixador=servindo(PORTAL), hoje=HOJE)
    assert relatorio["precisa_de_humano"] is False
