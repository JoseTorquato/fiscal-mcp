"""Testes do anonimizador.

Aqui a lição do repositório vira o seu contrário útil: **vazar dado pessoal é
pior que não ter a ferramenta**. Por isso a maior parte destes testes não
verifica que a saída ficou bonita — verifica que o original não sobrou nela, e
que o que faz a regra fiscal funcionar continua no lugar.

    python -m pytest tests/test_anonimizar.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lxml import etree  # noqa: E402

from anonimizar import (  # noqa: E402
    RAZAO_HOMOLOGACAO,
    Resultado,
    anonimiza,
    cnpj_ficticio,
    cpf_ficticio,
    main,
    procura_residuos,
)
from fiscal_mcp.chave import calcula_dv  # noqa: E402
from fiscal_mcp.validador import valida_nfe, valida_nfse  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
EXEMPLOS = sorted((RAIZ / "exemplos").glob("*.xml"))

CHAVE = "35260811222333000181550010000098761876543216"
CHAVE_REFERENCIADA = "35260722333444000155550010000011111111122221"
CNPJ_EMITENTE = "11222333000181"
CPF_DESTINATARIO = "52998224725"

# NF-e sintética com tudo que o anonimizador precisa encarar de uma vez:
# protocolo, assinatura, referência a outra nota, CPF de pessoa física,
# observações livres, IBS/CBS e alíquotas. Dados fictícios.
NOTA = f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- exportado por sistema-x para cliente Padaria do Joao -->
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe versao="4.00" Id="NFe{CHAVE}">
      <ide>
        <cUF>35</cUF>
        <cNF>87654321</cNF>
        <natOp>Venda de mercadoria</natOp>
        <mod>55</mod>
        <serie>1</serie>
        <nNF>9876</nNF>
        <dhEmi>2026-08-14T09:30:00-03:00</dhEmi>
        <tpNF>1</tpNF>
        <idDest>2</idDest>
        <cMunFG>3550308</cMunFG>
        <NFref><refNFe>{CHAVE_REFERENCIADA}</refNFe></NFref>
        <tpImp>1</tpImp>
        <tpEmis>1</tpEmis>
        <cDV>6</cDV>
        <tpAmb>1</tpAmb>
        <finNFe>1</finNFe>
        <indFinal>1</indFinal>
        <indPres>1</indPres>
        <procEmi>0</procEmi>
        <verProc>sistema-x 3.2</verProc>
      </ide>
      <emit>
        <CNPJ>{CNPJ_EMITENTE}</CNPJ>
        <xNome>Padaria do Joao Comercio de Alimentos Ltda</xNome>
        <xFant>Padaria do Joao</xFant>
        <enderEmit>
          <xLgr>Rua Doutor Placido Silveira</xLgr>
          <nro>1478</nro>
          <xCpl>Loja 3 fundos</xCpl>
          <xBairro>Vila Madalena</xBairro>
          <cMun>3550308</cMun>
          <xMun>Sao Paulo</xMun>
          <UF>SP</UF>
          <CEP>05435020</CEP>
          <fone>1155667788</fone>
        </enderEmit>
        <IE>114532198776</IE>
        <IM>91827364</IM>
        <CNAE>1091101</CNAE>
        <CRT>3</CRT>
      </emit>
      <dest>
        <CPF>{CPF_DESTINATARIO}</CPF>
        <xNome>Maria Aparecida de Souza</xNome>
        <enderDest>
          <xLgr>Avenida Brigadeiro Faria Lima</xLgr>
          <nro>2277</nro>
          <xBairro>Jardim Paulistano</xBairro>
          <cMun>3550308</cMun>
          <xMun>Sao Paulo</xMun>
          <UF>SP</UF>
          <CEP>01452000</CEP>
          <fone>11987654321</fone>
        </enderDest>
        <indIEDest>9</indIEDest>
        <email>maria.souza@provedor.com.br</email>
      </dest>
      <det nItem="1">
        <prod>
          <cProd>PAO01</cProd>
          <xProd>Pao frances para Maria Aparecida</xProd>
          <NCM>19059090</NCM>
          <CFOP>5102</CFOP>
          <uCom>KG</uCom>
          <qCom>3.0000</qCom>
          <vUnCom>20.00</vUnCom>
          <vProd>60.00</vProd>
          <indTot>1</indTot>
        </prod>
        <imposto>
          <ICMS>
            <ICMS00>
              <orig>0</orig>
              <CST>00</CST>
              <modBC>3</modBC>
              <vBC>60.00</vBC>
              <pICMS>18.00</pICMS>
              <vICMS>10.80</vICMS>
            </ICMS00>
          </ICMS>
          <IBSCBS>
            <CST>000</CST>
            <cClassTrib>000001</cClassTrib>
            <gIBSCBS>
              <vBC>60.00</vBC>
              <gIBSUF><pIBS>0.0500</pIBS><vIBSUF>0.03</vIBSUF></gIBSUF>
              <gCBS><pCBS>0.9000</pCBS><vCBS>0.54</vCBS></gCBS>
            </gIBSCBS>
          </IBSCBS>
        </imposto>
      </det>
      <total>
        <ICMSTot>
          <vProd>60.00</vProd>
          <vDesc>0.00</vDesc>
          <vFrete>0.00</vFrete>
          <vICMS>10.80</vICMS>
          <vNF>60.00</vNF>
        </ICMSTot>
      </total>
      <infAdic>
        <infCpl>Pedido 4471 do cliente Maria Aparecida de Souza, tel 11987654321</infCpl>
        <obsCont xCampo="ClienteFiel">
          <xTexto>Maria Aparecida de Souza, cadastro 8821</xTexto>
        </obsCont>
      </infAdic>
      <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        <SignedInfo><Reference URI="#NFe{CHAVE}"/></SignedInfo>
        <SignatureValue>Zm9vYmFyYmF6</SignatureValue>
        <KeyInfo><X509Data><X509Certificate>MIIF...</X509Certificate></X509Data></KeyInfo>
      </Signature>
    </infNFe>
  </NFe>
  <protNFe versao="4.00">
    <infProt>
      <chNFe>{CHAVE}</chNFe>
      <nProt>135260011122233</nProt>
      <digVal>abc123==</digVal>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da NF-e</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>
"""


def arvore(xml: str) -> etree._Element:
    return etree.fromstring(xml.encode("utf-8"))


def textos(xml: str, tag: str) -> list[str]:
    """Todos os textos de uma tag, sem depender do namespace declarado."""
    return [
        (e.text or "").strip()
        for e in arvore(xml).iter()
        if isinstance(e.tag, str) and e.tag.split("}")[-1] == tag
    ]


def um(xml: str, tag: str) -> str:
    achados = textos(xml, tag)
    assert achados, f"<{tag}> não encontrada na saída"
    return achados[0]


def dv_documento_confere(documento: str) -> bool:
    """Confere o DV de CPF ou CNPJ pelo algoritmo, não contra string fixa."""
    tamanho = len(documento)
    assert tamanho in (11, 14), f"documento com {tamanho} dígitos"
    peso_maximo = 11 if tamanho == 11 else 9
    corpo = documento[:-2]
    for esperado in documento[-2:]:
        soma = 0
        peso = 2
        for digito in reversed(corpo):
            soma += int(digito) * peso
            peso = 2 if peso == peso_maximo else peso + 1
        resto = soma % 11
        if esperado != ("0" if resto < 2 else str(11 - resto)):
            return False
        corpo += esperado
    return True


# ---- os documentos fictícios são documentos válidos -----------------------

def test_geradores_produzem_dv_valido():
    for n in range(1, 60):
        assert dv_documento_confere(cnpj_ficticio(n))
        assert dv_documento_confere(cpf_ficticio(n))


def test_geradores_nao_repetem():
    assert len({cnpj_ficticio(n) for n in range(1, 60)}) == 59
    assert len({cpf_ficticio(n) for n in range(1, 60)}) == 59


def test_cnpj_e_cpf_da_saida_tem_dv_valido():
    saida = anonimiza(NOTA).xml
    assert dv_documento_confere(um(saida, "CNPJ"))
    assert dv_documento_confere(um(saida, "CPF"))


# ---- determinismo, estabilidade e idempotência ----------------------------

def test_mesma_entrada_da_mesma_saida():
    assert anonimiza(NOTA).xml == anonimiza(NOTA).xml


def test_anonimizar_de_novo_nao_muda_nada():
    uma_vez = anonimiza(NOTA).xml
    assert anonimiza(uma_vez).xml == uma_vez


def test_o_mesmo_documento_vira_sempre_o_mesmo_substituto():
    """Emitente e destinatário precisam continuar sendo dois, e cada um um só."""
    saida = anonimiza(NOTA).xml
    cnpjs = textos(saida, "CNPJ")
    assert len(set(cnpjs)) == 1, "o CNPJ do emitente mudou entre ocorrências"
    assert um(saida, "CNPJ") != um(saida, "CPF")
    # o CNPJ dentro da chave é o mesmo do elemento emit/CNPJ
    assert chave_da_saida(saida)[6:20] == um(saida, "CNPJ")


def test_notas_diferentes_geram_documentos_diferentes():
    """Sem isso a relação entre emitente e destinatário se perde no arquivo."""
    saida = anonimiza(NOTA).xml
    referencia = um(saida, "refNFe")
    assert referencia[6:20] != um(saida, "CNPJ")


# ---- chave de acesso ------------------------------------------------------

def chave_da_saida(xml: str) -> str:
    ident = next(
        e.get("Id")
        for e in arvore(xml).iter()
        if isinstance(e.tag, str) and e.tag.split("}")[-1] == "infNFe"
    )
    return "".join(c for c in ident if c.isdigit())


def test_chave_da_saida_tem_dv_recalculado():
    nova = chave_da_saida(anonimiza(NOTA).xml)
    assert len(nova) == 44
    assert int(nova[43]) == calcula_dv(nova[:43])


def test_chave_da_saida_casa_com_cnpj_e_numero_anonimizados():
    saida = anonimiza(NOTA).xml
    nova = chave_da_saida(saida)
    assert nova[6:20] == um(saida, "CNPJ")
    assert nova[25:34] == f"{int(um(saida, 'nNF')):09d}"
    assert nova[35:43] == um(saida, "cNF")
    assert nova[43] == um(saida, "cDV")


def test_chave_preserva_uf_data_modelo_serie_e_numero():
    nova = chave_da_saida(anonimiza(NOTA).xml)
    assert nova[0:6] == CHAVE[0:6]      # cUF + AAMM
    assert nova[20:35] == CHAVE[20:35]  # mod + serie + nNF + tpEmis


def test_chave_referenciada_tambem_e_reconstruida():
    referencia = um(anonimiza(NOTA).xml, "refNFe")
    assert referencia != CHAVE_REFERENCIADA
    assert int(referencia[43]) == calcula_dv(referencia[:43])


# ---- o que faz a regra fiscal funcionar precisa sobreviver ----------------

def test_campos_fiscais_sobrevivem_intactos():
    saida = anonimiza(NOTA).xml
    for tag, esperado in [
        ("NCM", "19059090"),
        ("CFOP", "5102"),
        ("cClassTrib", "000001"),
        ("orig", "0"),
        ("mod", "55"),
        ("serie", "1"),
        ("nNF", "9876"),
        ("tpAmb", "1"),
        ("qCom", "3.0000"),
        ("uCom", "KG"),
    ]:
        assert um(saida, tag) == esperado, tag
    assert textos(saida, "CST") == ["00", "000"]


def test_aliquotas_e_valores_sobrevivem_intactos():
    saida = anonimiza(NOTA).xml
    assert textos(saida, "pICMS") == ["18.00"]
    assert textos(saida, "pIBS") == ["0.0500"]
    assert textos(saida, "pCBS") == ["0.9000"]
    assert textos(saida, "vProd") == ["60.00", "60.00"]
    assert textos(saida, "vNF") == ["60.00"]
    assert textos(saida, "vICMS") == ["10.80", "10.80"]


def test_geografia_sobrevive_porque_manda_em_regra_fiscal():
    saida = anonimiza(NOTA).xml
    assert set(textos(saida, "UF")) == {"SP"}
    assert set(textos(saida, "cMun")) == {"3550308"}
    assert set(textos(saida, "xMun")) == {"Sao Paulo"}


def test_ordem_dos_elementos_e_preservada():
    """O leiaute da NF-e é ordenado; trocar a ordem reprovaria no XSD.

    A saída só pode ter *removido* elementos: a sequência de tags dela precisa
    ser uma subsequência da original, na mesma ordem.
    """
    def nomes(xml):
        return [
            e.tag.split("}")[-1]
            for e in arvore(xml).iter()
            if isinstance(e.tag, str)
        ]

    antes, depois = iter(nomes(NOTA)), nomes(anonimiza(NOTA).xml)
    assert all(nome in antes for nome in depois), "a ordem dos elementos mudou"


def test_saida_continua_sendo_xml_valido():
    assert arvore(anonimiza(NOTA).xml) is not None


# ---- o que identifica alguém precisa sumir --------------------------------

def test_assinatura_e_protocolo_somem():
    saida = anonimiza(NOTA).xml
    presentes = {
        e.tag.split("}")[-1] for e in arvore(saida).iter() if isinstance(e.tag, str)
    }
    assert "Signature" not in presentes
    assert "protNFe" not in presentes
    assert "X509Certificate" not in presentes
    assert "nProt" not in presentes


def test_comentario_some_porque_carrega_nome_de_cliente():
    assert "Padaria do Joao" not in anonimiza(NOTA).xml


def test_nomes_viram_generico_numerado():
    saida = anonimiza(NOTA).xml
    assert re.fullmatch(r"Empresa \d+ Ltda", um(saida, "xNome"))
    assert "Maria Aparecida" not in saida


def test_endereco_contato_e_inscricoes_saem():
    saida = anonimiza(NOTA).xml
    for sobra in ["Placido Silveira", "Vila Madalena", "Loja 3 fundos", "05435020",
                  "1155667788", "maria.souza@provedor.com.br", "114532198776",
                  "91827364", "1091101", "Faria Lima", "01452000", "11987654321"]:
        assert sobra not in saida, sobra


def test_texto_livre_sai_inclusive_o_rotulo_da_observacao():
    saida = anonimiza(NOTA).xml
    assert "Pedido 4471" not in saida
    assert "cadastro 8821" not in saida
    assert "ClienteFiel" not in saida


def test_descricao_do_produto_sai_mas_continua_distinguindo_itens():
    saida = anonimiza(NOTA).xml
    assert "Pao frances" not in saida
    assert re.fullmatch(r"Produto \d+", um(saida, "xProd"))


def test_razao_social_de_homologacao_e_preservada():
    """É texto de norma, não identificação — e é o que a regra verifica."""
    exemplo = (RAIZ / "exemplos" / "nfe-valida.xml").read_text(encoding="utf-8")
    saida = anonimiza(exemplo).xml
    assert any(n.upper().startswith(RAZAO_HOMOLOGACAO) for n in textos(saida, "xNome"))


# ---- a rede de segurança --------------------------------------------------

def test_conferir_nao_acusa_saida_limpa():
    assert procura_residuos(anonimiza(NOTA)) == []


def test_conferir_acusa_cnpj_injetado_de_volta():
    resultado = anonimiza(NOTA)
    sujo = resultado.xml.replace(
        um(resultado.xml, "CNPJ"), CNPJ_EMITENTE
    )
    achados = procura_residuos(resultado, sujo)
    assert achados, "o resíduo de CNPJ passou batido"
    assert any("cnpj" in a for a in achados)


def test_conferir_acusa_cpf_escondido_dentro_de_outro_numero():
    """O jeito como documento vaza de verdade: dentro de chave não reconstruída."""
    resultado = anonimiza(NOTA)
    sujo = resultado.xml.replace("<nProt>", "").replace(
        "<cProd>PAO01</cProd>", f"<cProd>000{CPF_DESTINATARIO}000</cProd>"
    )
    assert any("cpf" in a for a in procura_residuos(resultado, sujo))


def test_conferir_acusa_nome_injetado_de_volta():
    resultado = anonimiza(NOTA)
    original = "Padaria do Joao Comercio de Alimentos Ltda"
    sujo = resultado.xml.replace("Empresa 1 Ltda", original)
    assert any("nome" in a for a in procura_residuos(resultado, sujo))


def test_relatorio_nunca_reimprime_o_original_inteiro():
    """O relatório vai para log e para issue; reimprimir o dado derruba o script."""
    from anonimizar import relatorio

    linhas = "\n".join(relatorio(anonimiza(NOTA)))
    assert CNPJ_EMITENTE not in linhas
    assert CPF_DESTINATARIO not in linhas
    assert "Maria Aparecida de Souza" not in linhas


def test_tag_de_texto_livre_desconhecida_gera_aviso():
    """Melhor barulhento que vazando: o que não sabemos tratar precisa gritar."""
    com_tag_nova = NOTA.replace(
        "<verProc>sistema-x 3.2</verProc>",
        "<verProc>sistema-x 3.2</verProc><xPed>Compra da Maria</xPed>",
    )
    avisos = anonimiza(com_tag_nova).avisos
    assert any("xPed" in a for a in avisos)


def test_documento_formatado_que_escapou_gera_aviso():
    com_cpf_solto = NOTA.replace(
        "<verProc>sistema-x 3.2</verProc>", "<verProc>emissor 529.982.247-25</verProc>"
    )
    assert any("CPF/CNPJ" in a for a in anonimiza(com_cpf_solto).avisos)


# ---- a saída ainda precisa passar na validação ----------------------------

def test_exemplos_anonimizados_validam_igual_ao_original():
    """Anonimizar não pode inventar nem esconder achado: o laudo tem de bater."""
    assert EXEMPLOS, "nenhum XML em exemplos/"
    for caminho in EXEMPLOS:
        bruto = caminho.read_text(encoding="utf-8")
        valida = valida_nfse if "nfse" in caminho.name else valida_nfe
        antes, depois = valida(bruto), valida(anonimiza(bruto).xml)
        assert antes["erros"] == depois["erros"], caminho.name
        assert sorted(a["id"] for a in antes["achados"]) == sorted(
            a["id"] for a in depois["achados"]
        ), caminho.name


def test_nota_completa_anonimizada_nao_ganha_erro_novo():
    """A invariante que importa: anonimizar nunca INTRODUZ achado.

    Não é "o laudo fica idêntico". Remover o protocolo desembrulha o `nfeProc`,
    o que legitimamente faz um achado de schema desaparecer. O que não pode
    acontecer é o contrário — alguém contribuir um XML anonimizado e a
    ferramenta acusar um problema que o original não tinha.
    """
    antes, depois = valida_nfe(NOTA), valida_nfe(anonimiza(NOTA).xml)
    assert depois["erros"] <= antes["erros"]
    novos = {a["id"] for a in depois["achados"]} - {a["id"] for a in antes["achados"]}
    assert not novos, f"a anonimização introduziu achados: {novos}"


def test_nfeproc_sem_protocolo_vira_nfe():
    """O protocolo sai, e o invólucro que o exige sai junto.

    O schema oficial exige `protNFe` dentro de `nfeProc`. Manter o invólucro
    sem o protocolo entregaria um XML que não passa no próprio XSD — e rodar no
    validador é o primeiro uso de um XML contribuído.
    """
    assert NOTA.lstrip().startswith('<?xml') and "<nfeProc" in NOTA
    saida = anonimiza(NOTA).xml
    assert "<nfeProc" not in saida
    assert "<NFe" in saida
    assert "protNFe" not in saida


# ---- linha de comando -----------------------------------------------------

def test_cli_escreve_arquivo_e_confere(tmp_path, capsys):
    entrada = tmp_path / "nota.xml"
    entrada.write_text(NOTA, encoding="utf-8")
    saida = tmp_path / "anon.xml"
    assert main([str(entrada), "-o", str(saida), "--conferir"]) == 0
    assert saida.read_text(encoding="utf-8") == anonimiza(NOTA).xml
    assert "PUBLIQUE" not in capsys.readouterr().err.upper()


def test_cli_sai_com_2_quando_o_arquivo_nao_existe(tmp_path):
    assert main([str(tmp_path / "nao-existe.xml")]) == 2


def test_cli_sai_com_2_quando_o_xml_e_malformado(tmp_path):
    ruim = tmp_path / "ruim.xml"
    ruim.write_text("<NFe><infNFe>", encoding="utf-8")
    assert main([str(ruim)]) == 2


def test_conferir_acusa_o_que_o_proprio_script_nao_soube_tratar():
    """O caso que a rede existe para pegar, montado como acontece de verdade.

    A chave da NFS-e tem leiaute não confirmado; quando o documento aparece nela
    em mais de uma posição, o script se recusa a adivinhar e avisa. O `--conferir`
    tem de transformar esse aviso em reprovação — senão o arquivo sai com o CNPJ
    real dentro do Id e ninguém percebe.
    """
    cnpj = "12121212000112"
    identificador = "4304606" + cnpj + "99" + cnpj + "9999999999999"
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse" versao="1.01">'
        f'<infNFSe Id="NFS{identificador}"><nNFSe>1</nNFSe>'
        f"<emit><CNPJ>{cnpj}</CNPJ><xNome>Prestador Real Ltda</xNome></emit>"
        "</infNFSe></NFSe>"
    )
    resultado = anonimiza(xml)
    assert any("mais de uma posição" in a for a in resultado.avisos)
    assert any("cnpj" in a for a in procura_residuos(resultado))


def test_cli_sai_com_1_quando_acha_residuo(tmp_path, capsys):
    """A rede de segurança precisa reprovar de verdade, não só avisar."""
    cnpj = "12121212000112"
    identificador = "4304606" + cnpj + "99" + cnpj + "9999999999999"
    entrada = tmp_path / "nfse.xml"
    entrada.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse" versao="1.01">'
        f'<infNFSe Id="NFS{identificador}"><nNFSe>1</nNFSe>'
        f"<emit><CNPJ>{cnpj}</CNPJ><xNome>Prestador Real Ltda</xNome></emit>"
        "</infNFSe></NFSe>",
        encoding="utf-8",
    )
    assert main([str(entrada), "-o", str(tmp_path / "anon.xml"), "--conferir"]) == 1
    assert "PUBLIQUE" in capsys.readouterr().err.upper()


def test_resultado_reconstruido_ainda_confere():
    """`procura_residuos` só depende dos mapas, então serve para conferir a mão."""
    resultado = anonimiza(NOTA)
    sujo = Resultado(
        xml=resultado.xml.replace(um(resultado.xml, "CNPJ"), CNPJ_EMITENTE),
        filas=resultado.filas,
        fixos=resultado.fixos,
        chaves=resultado.chaves,
    )
    assert procura_residuos(sujo) != []
