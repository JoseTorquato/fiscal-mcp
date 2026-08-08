"""Testes da fatia zero.

O que mais importa aqui é a mesma lição do Cilada: **acusar errado é pior que
não acusar**. Um validador que reprova nota correta perde a confiança de quem
usa na primeira vez. Por isso metade destes testes verifica que o XML bom passa.

    python tests/test_fatia_zero.py     (ou pytest tests/)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fiscal_mcp import chave, rejeicoes  # noqa: E402
from fiscal_mcp.regras import carrega  # noqa: E402
from fiscal_mcp import nfse as mod_nfse  # noqa: E402
from fiscal_mcp.validador import explica_nfe, explica_nfse, valida_nfe, valida_nfse  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
EXEMPLO = (RAIZ / "exemplos" / "nfe-valida.xml").read_text(encoding="utf-8")
EXEMPLO_NFSE = (RAIZ / "exemplos" / "nfse-nacional.xml").read_text(encoding="utf-8")


def ids_dos_erros(resultado: dict) -> set[str]:
    return {a["id"] for a in resultado["achados"] if a["severidade"] == "erro"}


# ---- chave de acesso ------------------------------------------------------

def test_dv_muda_com_qualquer_digito():
    """Propriedade do módulo 11: alterar um dígito qualquer precisa mudar o DV."""
    base = "43260812345678000195550010000012341" + "12345678"
    dv = chave.calcula_dv(base)
    for i in range(43):
        alterado = list(base)
        alterado[i] = str((int(alterado[i]) + 1) % 10)
        assert chave.calcula_dv("".join(alterado)) != dv, f"dígito {i} não afeta o DV"


def test_chave_valida_e_decomposta():
    r = chave.analisa("43260812345678000195550010000012341123456786")
    assert r["ok"]
    assert r["uf"] == "RS"
    assert r["documento"] == "NF-e"
    assert r["numero"] == 1234
    assert r["cnpj_emitente"] == "12345678000195"


def test_chave_com_dv_errado_e_acusada():
    boa = "43260812345678000195550010000012341123456786"
    ruim = boa[:43] + ("0" if boa[43] != "0" else "1")
    r = chave.analisa(ruim)
    assert not r["ok"]
    assert any(p["campo"] == "cDV" for p in r["problemas"])


def test_chave_aceita_formatada():
    """No DANFE a chave aparece em grupos de 4 — precisa aceitar assim."""
    formatada = " ".join(re.findall(r"\d{4}", "43260812345678000195550010000012341123456786"))
    assert chave.analisa(formatada)["ok"]


def test_chave_de_tamanho_errado_nao_explode():
    r = chave.analisa("123")
    assert not r["ok"] and "erro" in r and "acao" in r


def test_uf_inexistente_e_acusada():
    base = "99" + "260812345678000195550010000012341" + "12345678"
    r = chave.analisa(base + str(chave.calcula_dv(base)))
    assert any(p["campo"] == "cUF" for p in r["problemas"])


# ---- validação: o bom precisa passar --------------------------------------

def test_xml_valido_passa_sem_erro():
    r = valida_nfe(EXEMPLO)
    assert r["ok"], f"reprovou nota correta: {ids_dos_erros(r)}"
    assert r["erros"] == 0


def test_ibs_cbs_e_aviso_nao_erro():
    """Regra pendente de confirmação não pode reprovar nota."""
    r = valida_nfe(EXEMPLO)
    ibs = [a for a in r["achados"] if a["id"].startswith("ibs-cbs")]
    assert ibs, "a regra de IBS/CBS deveria ter aparecido"
    assert all(a["severidade"] == "aviso" for a in ibs)
    assert all(a.get("status_da_regra") == "pendente_confirmacao" for a in ibs)


# ---- validação: o ruim precisa ser pego -----------------------------------

def test_total_divergente_e_pego():
    quebrado = EXEMPLO.replace("<vProd>250.00</vProd>", "<vProd>999.00</vProd>")
    r = valida_nfe(quebrado)
    assert not r["ok"]
    assert "tot-produtos-confere" in ids_dos_erros(r)


def test_nota_sem_item_e_pega():
    sem_itens = re.sub(r"<det nItem.*?</det>", "", EXEMPLO, flags=re.S)
    r = valida_nfe(sem_itens)
    assert "est-tem-item" in ids_dos_erros(r)


def test_emitente_incompleto_e_pego():
    quebrado = EXEMPLO.replace("<CNPJ>12345678000195</CNPJ>", "")
    assert "est-emitente-presente" in ids_dos_erros(valida_nfe(quebrado))


def test_cnpj_formatado_e_pego():
    """CNPJ vai só com dígitos no XML — com máscara a SEFAZ rejeita."""
    quebrado = EXEMPLO.replace("<CNPJ>12345678000195</CNPJ>",
                               "<CNPJ>12.345.678/0001-95</CNPJ>")
    assert "est-cnpj-emitente-formato" in ids_dos_erros(valida_nfe(quebrado))


def test_ambiente_invalido_e_pego():
    quebrado = EXEMPLO.replace("<tpAmb>2</tpAmb>", "<tpAmb>7</tpAmb>")
    assert "est-ambiente-declarado" in ids_dos_erros(valida_nfe(quebrado))


def test_chave_do_id_com_dv_errado_e_pega():
    quebrado = EXEMPLO.replace("Id=\"NFe43260812345678000195550010000012341123456786\"",
                               "Id=\"NFe43260812345678000195550010000012341123456780\"")
    assert any(i.startswith("chave-") for i in ids_dos_erros(valida_nfe(quebrado)))


def test_xml_malformado_nao_explode():
    r = valida_nfe("<NFe><infNFe>")
    assert not r["ok"] and "erro" in r and "acao" in r


def test_xml_que_nao_e_nfe_e_recusado():
    r = valida_nfe("<?xml version='1.0'?><pedido><id>1</id></pedido>")
    assert not r["ok"] and "infNFe" in r["erro"]


def test_nao_carrega_entidade_externa():
    """XXE: XML fiscal vem de terceiro e não pode ler arquivo do disco."""
    ataque = (
        "<?xml version='1.0'?><!DOCTYPE r [<!ENTITY x SYSTEM 'file:///etc/passwd'>]>"
        "<NFe xmlns='http://www.portalfiscal.inf.br/nfe'><infNFe Id='NFe1'>"
        "<ide><natOp>&x;</natOp></ide></infNFe></NFe>"
    )
    r = valida_nfe(ataque)  # não pode explodir
    assert "root:" not in str(r), "entidade externa foi expandida"
    assert "/bin/" not in str(r), "conteúdo de arquivo do disco vazou"


def test_comentario_no_meio_do_xml_nao_quebra():
    """Comentário e instrução de processamento têm .tag não-string no lxml."""
    com_comentario = EXEMPLO.replace(
        "<total>", "<!-- gerado pelo ERP em 08/08 --><?processa versao='1'?><total>"
    )
    r = valida_nfe(com_comentario)
    assert r["ok"], f"comentário no XML quebrou a validação: {ids_dos_erros(r)}"


def test_reconhece_nfse_em_vez_de_dizer_so_que_nao_e_nfe():
    """Erro precisa dizer QUAL documento é — descoberto ao rodar numa NFS-e real."""
    nfse = (Path(__file__).resolve().parent.parent / "exemplos" /
            "nfse-nacional-minima.xml").read_text(encoding="utf-8")
    r = valida_nfe(nfse)
    assert not r["ok"]
    assert "NFS-e" in r["erro"], f"não identificou o documento: {r['erro']}"
    assert "DANFE" not in r.get("acao", ""), "ação genérica contradiz o diagnóstico"


def test_chave_de_50_digitos_e_reconhecida_como_nfse():
    r = chave.analisa("43046062200000000000000000000000000000000000000000")
    assert not r["ok"]
    assert "NFS-e" in r.get("documento", "")
    assert r.get("uf") == "RS", "deveria derivar a UF do código do município"
    assert "completa" in r["acao"], "não pode sugerir que a chave está truncada"



# ---- NFS-e ----------------------------------------------------------------

def test_nfse_valida_passa_sem_erro():
    r = valida_nfse(EXEMPLO_NFSE)
    assert r["ok"], f"reprovou NFS-e correta: {ids_dos_erros(r)}"


def test_nfse_sem_dps_e_pega():
    """A DPS embutida é o coração da NFS-e nacional."""
    quebrada = re.sub(r"<DPS>.*?</DPS>", "", EXEMPLO_NFSE, flags=re.S)
    assert "nfse-dps-presente" in ids_dos_erros(valida_nfse(quebrada))


def test_nfse_sem_codigo_de_tributacao_e_pega():
    quebrada = EXEMPLO_NFSE.replace("<cTribNac>010101</cTribNac>", "<cTribNac></cTribNac>")
    assert "nfse-servico-descrito" in ids_dos_erros(valida_nfse(quebrada))


def test_nfse_cnpj_prestador_formatado_e_pego():
    """CNPJ do prestador com máscara: precisa ser pego pelo formato."""
    import re as _re
    # troca só o CNPJ dentro do bloco <prest>, não o do <emit>
    quebrada = _re.sub(
        r"(<prest>\s*<CNPJ>)(\d{14})(</CNPJ>)",
        r"\g<1>00.000.000/0000-00\g<3>",
        EXEMPLO_NFSE,
    )
    assert quebrada != EXEMPLO_NFSE, "a substituição não pegou o CNPJ do prestador"
    assert "nfse-cnpj-prestador-formato" in ids_dos_erros(valida_nfse(quebrada))


def test_nfe_no_validador_de_nfse_da_erro_claro():
    r = valida_nfse(EXEMPLO)
    assert not r["ok"] and "infNFSe" in r["erro"]


def test_resumo_nfse_nao_vaza_documento_do_tomador():
    r = explica_nfse(EXEMPLO_NFSE)
    assert r["tomador"]["identificado"] is True
    assert "11111111000111" not in str(r["tomador"])


def test_chave_nfse_decompoe_posicoes_confirmadas():
    """Posições verificadas contra NFS-e real: município, número, AAMM."""
    # município 4304606 (Canoas/RS), número 39, emissão 08/2026
    chave = "4304606" + "22" + "0" * 14 + "0000" + "000000039" + "2608" + "0" * 10
    r = mod_nfse.analisa_chave(chave)
    assert r["ok"], r.get("problemas")
    assert r["codigo_municipio"] == "4304606"
    assert r["uf"] == "RS"
    assert r["numero"] == 39
    assert r["emissao"] == "08/2026"


def test_chave_nfse_com_mes_impossivel_e_acusada():
    """Mês 60 passava sem reclamação — achado ao rodar numa chave sintética."""
    chave = "4304606" + "22" + "0" * 14 + "0000" + "000000001" + "2660" + "0" * 10
    r = mod_nfse.analisa_chave(chave)
    assert not r["ok"]
    assert any(p["campo"] == "AAMM" for p in r["problemas"])


def test_chave_nfse_nao_finge_verificar_digito():
    """Honestidade: sem algoritmo confirmado, não se promete verificação."""
    chave = "4304606" + "22" + "0" * 14 + "0000" + "000000001" + "2608" + "0" * 10
    r = mod_nfse.analisa_chave(chave)
    assert "dígito verificador" in r["nota"]



# ---- resumo ---------------------------------------------------------------

def test_resumo_nao_vaza_documento_do_destinatario():
    """Minimização: o resumo indica que há destinatário, sem devolver CNPJ/CPF."""
    r = explica_nfe(EXEMPLO)
    assert r["destinatario"]["identificado"] is True
    assert "98765432000188" not in str(r["destinatario"])


def test_resumo_traz_o_essencial():
    r = explica_nfe(EXEMPLO)
    assert r["quantidade_itens"] == 2
    assert r["totais"]["nota"] == "250.00"
    assert r["identificacao"]["ambiente"] == "homologacao"
    assert r["autorizada"] is False


# ---- rejeições ------------------------------------------------------------

def test_explica_rejeicao_por_codigo():
    r = rejeicoes.explica("539")
    assert r["ok"] and "acao" in r and "duplicidade" in r["significa"].lower()


def test_explica_rejeicao_dentro_da_mensagem():
    r = rejeicoes.explica("Rejeicao: 204 - Duplicidade de NF-e")
    assert r["ok"] and r["codigo"] == "204"


def test_rejeicao_denegada_marcada_como_irreversivel():
    assert rejeicoes.explica("301")["reversivel"] is False


def test_codigo_desconhecido_orienta_em_vez_de_falhar():
    r = rejeicoes.explica("777")
    assert not r["ok"] and "acao" in r


# ---- integridade do corpus ------------------------------------------------

def test_regras_carregam_sem_id_duplicado():
    regras = carrega()
    ids = [r.id for r in regras]
    assert len(ids) == len(set(ids))
    assert len(regras) >= 8


def test_toda_regra_tem_mensagem_e_acao():
    for r in carrega():
        assert r.mensagem, f"{r.id} sem mensagem"
        assert r.acao, f"{r.id} sem ação — erro sem ação é inútil para um agente"


def test_regex_das_regras_compilam():
    for r in carrega():
        if r.padrao:
            re.compile(r.padrao)





# ---- camada MCP -----------------------------------------------------------

def _mcp():
    """Importa o servidor só quando o SDK está presente."""
    try:
        from fiscal_mcp.servidor import mcp
    except ModuleNotFoundError:  # SDK não instalado: núcleo continua testável
        return None
    return mcp


def test_servidor_expoe_as_ferramentas_da_fatia_zero():
    import asyncio
    mcp = _mcp()
    if mcp is None:
        return
    nomes = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"validar_nfe", "explicar_nfe", "explicar_rejeicao",
            "validar_chave_acesso"} <= nomes


def test_nenhuma_ferramenta_tem_efeito_colateral():
    """Fatia zero: tudo precisa estar declarado como leitura pura no protocolo.

    Se um dia entrar aqui uma ferramenta que emite, este teste falha — e é
    exatamente o alarme que se quer (ADR-0010).
    """
    import asyncio
    mcp = _mcp()
    if mcp is None:
        return
    for t in asyncio.run(mcp.list_tools()):
        assert t.annotations is not None, f"{t.name} sem anotação"
        assert t.annotations.read_only_hint is True, f"{t.name} não é somente leitura"
        assert t.annotations.destructive_hint is False, f"{t.name} marcada como destrutiva"


def test_chamada_real_pelo_protocolo():
    import asyncio
    import json as _json
    mcp = _mcp()
    if mcp is None:
        return
    r = asyncio.run(mcp.call_tool(
        "validar_chave_acesso",
        {"chave": "43260812345678000195550010000012341123456786"},
    ))
    dados = _json.loads(r.content[0].text)
    assert dados["ok"] and dados["uf"] == "RS" and dados["numero"] == 1234


if __name__ == "__main__":
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
