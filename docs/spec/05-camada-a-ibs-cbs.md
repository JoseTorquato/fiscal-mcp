# Spec 05 — Camada A: validação estrutural de IBS/CBS

> A regra que acusa errado é pior que a regra que não existe. Um validador que
> reprova nota válida é desinstalado no mesmo dia, e não volta. Toda decisão
> deste documento sai daí.

## 1. O problema que esta spec resolve

O arquivo `regras/nfe/ibs-cbs.yaml` tem uma regra em `pendente_confirmacao` com
quatro TODOs. Três deles já têm resposta pública; o quarto tem uma resposta
inesperada.

| TODO original | Situação |
|---|---|
| nomes exatos das tags | **Resolvido.** Mapeado na §4 e disponível nos XSD que a `nfelib` empacota |
| quando o grupo é obrigatório | **Resolvido, e mudou.** Ver §2 |
| campos por item além dos totais | **Resolvido.** O grosso do leiaute é por item, não nos totais |
| versão de leiaute | **Parcialmente.** Pacote vigente é o PL 010e v1.02 (10/07/2026), que cobre a NT v1.40 — não a v1.50/1.51 |

O que continua sem confirmação em fonte primária são os **códigos numéricos de
rejeição**. Essa separação é a espinha da spec.

---

## 2. A descoberta que muda a severidade

A NT 2025.002 **v1.51**, aprovada pelo **Ato Técnico Conjunto RFB/CGIBS nº 1, de
31/07/2026**, alterou a regra **UB12-10** — a que exigiria o grupo `IBSCBS` — de
data fixa (03/08/2026) para **"implementação futura"**, sem cronograma.

Consequência direta: **a rejeição por ausência do grupo não está ativa em
produção para NF-e e NFC-e.** Uma regra que acuse erro ali hoje acusa errado.

E uma distinção que quase todo conteúdo do mercado erra, e que vale a pena o
projeto acertar em público: **isso é postergação técnica, não jurídica.** A
obrigação legal de destacar permanece, e o descumprimento afeta a dispensa de
recolhimento do art. 348 da LC 214/2025. Em 2026 a nota corretamente preenchida
*é* o mecanismo de dispensa — errar tem custo financeiro real mesmo sem rejeição.

Para CT-e, BP-e, NF3e e NFCom o regime é outro: a Rejeição 310 **está** ativa em
produção desde 03/08/2026. Como o projeto não cobre esses modelos, isso só
importa para não copiar código de rejeição errado.

---

## 3. Duas camadas, dois níveis de severidade permitidos

| | Camada A — estrutural | Camada B — código de rejeição |
|---|---|---|
| Fonte | XSD oficial + tabela CST/cClassTrib publicada pela SVRS | Seção 7 da NT (tabela de regras de validação) |
| Verificável? | Sim, o dado é baixável e versionável | Não foi confirmado em fonte primária |
| Pode ser `erro`? | **Sim** | **Não, enquanto não confirmado** |
| Escopo desta spec | Toda | Nenhuma |

**Regra de projeto:** nenhuma mensagem da ferramenta cita um número de rejeição
antes de o número ter sido lido na NT vigente. Descrever o problema sem o número
é sempre permitido e quase sempre suficiente — quem lê é um agente que precisa
saber o que fazer, não o código do erro.

> Aviso de procedência: durante a pesquisa, uma extração automatizada do PDF da
> NT produziu códigos de rejeição inexistentes (faixa 1004–1011), que foram
> descartados. Isso é exatamente o modo de falha que esta spec existe para
> impedir. Nenhum código entra no repositório sem leitura humana da fonte.

---

## 4. O leiaute, na parte que interessa

Confiança: alta. Extraído do PDF oficial da NT v1.40 hospedado no CGIBS, por
extrator automatizado. **Conferir contra o XSD antes de virar código** — o XSD é
a verdade executável e resolve ambiguidade de cardinalidade.

```
det/imposto/
└─ IBSCBS                        UB12 · 0-1
   ├─ CST                        UB13 · 1-1 · 3 dígitos
   ├─ cClassTrib                 UB14 · 1-1 · 6 dígitos
   ├─ indDoacao                  UB14a · 0-1
   └─ (xs:choice UB14k · no máximo um)
      ├─ gIBSCBS                 UB15 — tributação normal
      │  ├─ vBC
      │  ├─ gIBSUF  → pIBSUF, [gDif], [gDevTrib], [gRed], vIBSUF
      │  ├─ gIBSMun → pIBSMun, [gDif], [gDevTrib], [gRed], vIBSMun
      │  ├─ vIBS                 UB54a = vIBSUF + vIBSMun
      │  ├─ gCBS    → pCBS, [gDif], [gDevTrib], [gRed], [gALCZFMCBS], vCBS
      │  ├─ [gTribRegular]       UB68
      │  └─ [gTribCompraGov]     UB82a
      ├─ gIBSCBSMono             UB84 — monofasia
      ├─ gTransfCred             UB106
      └─ gAjusteCompet           UB112 · competApur AAAA-MM

total/
└─ IBSCBSTot                     W34 · 0-1
   ├─ vBCIBSCBS
   ├─ gIBS → gIBSUF(vIBSUF), gIBSMun(vIBSMun), vIBS, vCredPres, vCredPresCondSus
   ├─ gCBS → vCBS, vCredPres, vCredPresCondSus
   └─ vNFTot                     W60
```

### Armadilhas confirmadas

- **`gIBSCredPres` não fica direto sob `gIBSCBS`.** Está aninhado em
  `gCredPresOper` (UB120), dentro do choice UB119. Quebra XPath ingênuo.
- **`vTotDFe` não existe.** Uma fonte secundária cita essa tag nos totais; não
  aparece no leiaute oficial. O total geral é `vNFTot`.
- **`pISEspec` e `adRemIS`** apareceram fundidos num campo só na extração
  (`pISEspecadRemIS`). Não implementar regra de Imposto Seletivo sobre isso sem
  conferir no XSD.

---

## 5. Mudanças necessárias no motor de regras

Estas são as mudanças estruturais. Nenhuma regra fiscal nova pode ser escrita
antes delas, sob pena de virar código em vez de dado — o oposto da tese do
projeto ([spec 04](04-manutencao.md)).

### 5.1 Escopo por item

Hoje toda regra roda uma vez, na raiz `infNFe`. O grosso do IBS/CBS é por item.

**Contrato:** campo opcional `escopo: documento | item`, padrão `documento`.
Quando `item`, o executor roda uma vez por `det` e os caminhos são relativos ao
`det`.

**Critério de aceite:**
- Uma regra com `escopo: item` numa nota de 3 itens é avaliada 3 vezes.
- O detalhe do achado começa por `item 2:` (usando o atributo `nItem`, não o
  índice — nota com numeração não sequencial existe).
- Um mesmo `id` de regra pode gerar mais de um achado; o resumo conta achados,
  não regras.
- Regra sem `escopo` continua se comportando exatamente como hoje. Os 41 testes
  atuais passam sem alteração.

### 5.2 Tipos novos

| Tipo | Para que serve | Campos | Detalhe esperado |
|---|---|---|---|
| `prefixo_de` | L-02 | `campo`, `campo_referencia`, `tamanho` | `cClassTrib = '000123' não começa por CST = '200'` |
| `em_tabela` | L-01, L-03, L-04 | `campo`, `tabela`, `coluna`, `filtro` (opcional) | `CST = '999' não existe na tabela cst-ibs-cbs v2026-08` |
| `soma_campos` | L-06 | `campo_total`, `campos`, `tolerancia` | `vIBS = 10.00, vIBSUF + vIBSMun = 9.50, diferença de 0.50` |
| `exclusivo` | L-08 | `campos` | `presentes ao mesmo tempo: gIBSCBS, gIBSCBSMono` |
| `subgrupos_por_indicador` | L-05 | `campo_chave`, `tabela`, `mapa` | `cClassTrib = '200008' exige gRed, que está ausente` |
| `valor_numerico_em` | L-14 | `campo`, `valores`, `tolerancia` | `pIBSUF = 0.1500, esperado 0.1000` |

Dois pontos de contrato que valem explicitar:

- **`em_tabela` e `subgrupos_por_indicador` leem dado versionado no repositório,
  nunca a rede.** Se a tabela não estiver embarcada, a regra não roda e emite
  `informacao` dizendo que não pôde ser avaliada — nunca `erro`.
- **`valor_numerico_em` compara `Decimal`, não string.** `0.10`, `0.1000` e
  `0.100` são o mesmo valor e nenhum deles pode gerar achado.

### 5.3 Ausência de campo nunca é erro do tipo errado

Regra que existe hoje e precisa continuar valendo para os tipos novos: se o
campo avaliado está ausente, o executor devolve `None`. A obrigatoriedade é
responsabilidade de uma regra `existe` ou `condicional` dedicada, com sua própria
severidade. Sem isso, uma nota sem grupo IBS/CBS geraria catorze achados em vez
de um.

### 5.4 Bloco de vigência substitui `status`

O campo `status: pendente_confirmacao` é honesto mas não tem saída: nada obriga
a revisitar. Trocar por:

```yaml
vigencia:
  desde: "2026-08-03"          # opcional; quando a regra passa a valer
  reavaliar_em: "2026-09-01"   # data concreta, não "quando der"
  fonte: "NT 2025.002 v1.51 · Ato Técnico Conjunto RFB/CGIBS nº 1, de 31/07/2026"
  observacao: >
    UB12-10 reclassificada como implementação futura. Reavaliar quando entrarem
    as validações de 01/09/2026 (homologação) e 05/10/2026 (produção).
```

**Critério de aceite:** um teste falha quando existe regra com `reavaliar_em` no
passado. É o gatilho que garante que a manutenção aconteça — e, quando falhar em
CI, é a evidência pública de que ela acontece ([spec 04](04-manutencao.md)).

---

## 6. As 14 regras

Nomenclatura: `ibs-` no id, grupo `ibs-cbs`. Todas com `acao` obrigatória, como
já exige o teste existente.

| # | id | Tipo | Escopo | Severidade | O que valida |
|---|---|---|---|---|---|
| L-01 | `ibs-cst-existe` | `em_tabela` | item | erro | `CST` está na tabela dos 18 códigos |
| L-02 | `ibs-cclasstrib-prefixo-cst` | `prefixo_de` | item | erro | `cClassTrib` tem 6 dígitos e os 3 primeiros são o `CST` |
| L-03 | `ibs-cclasstrib-existe` | `em_tabela` | item | erro | `cClassTrib` está na tabela oficial |
| L-04 | `ibs-cclasstrib-modelo` | `em_tabela` | item | erro | `cClassTrib` permitido no modelo (55 vs 65) |
| L-05 | `ibs-subgrupos-obrigatorios` | `subgrupos_por_indicador` | item | erro | Subgrupos exigidos ou vedados pelos indicadores da tabela |
| L-06 | `ibs-vibs-soma-uf-mun` | `soma_campos` | item | erro | `vIBS` = `vIBSUF` + `vIBSMun` |
| L-07 | `ibs-totais-conferem` | `soma_itens` | documento | erro | Totais W batem com a soma dos itens |
| L-08 | `ibs-grupo-exclusivo` | `exclusivo` | item | erro | No máximo um ramo do choice UB14k |
| L-09 | `ibs-cst-620-exige-mono` | `condicional` | item | erro | `CST` 620 exige `gIBSCBSMono` |
| L-10 | `ibs-totais-presentes` | `condicional` | documento | erro | Item com `IBSCBS` exige `IBSCBSTot` |
| L-11 | `ibs-competapur-formato` | `formato` | item | erro | `competApur` casa `^\d{4}-(0[1-9]\|1[0-2])$` |
| L-12 | `ibs-escala-decimal` | `formato` | item | **aviso** | Valores 13v2, alíquotas 3v2-4, quantidades 11v0-4 |
| L-13 | `ibs-enums` | `valor_em` | item | erro | `tpCredPresIBSZFM` ∈ {0..4}; `tpALCZFMCBS` ∈ {1,2} |
| L-14 | `ibs-aliquotas-2026` | `valor_numerico_em` | item | **aviso** | `pIBSUF` = 0,10 e `pCBS` = 0,90 |

### Por que L-12 e L-14 são aviso, e não erro

- **L-12** depende de interpretação de escala decimal que o XSD já faz melhor.
  Quando a Camada XSD ([spec 06](06-validacao-xsd.md)) estiver de pé, avaliar se
  esta regra deve sair do YAML por redundância.
- **L-14** tem exceções legítimas. Uma fonte secundária afirma `pIBSMun = 0,00%`
  em 2026 com preenchimento obrigatório, com os 0,1% ficando integralmente na
  parcela estadual — **não confirmado em fonte oficial**. Enquanto essa dúvida
  existir, a regra não pode reprovar. Registrar como `reavaliar_em: 2026-10-05`.

### L-05 é a mais valiosa e a mais perigosa

É a regra que ninguém mais tem: usa as colunas `ind_g*` da tabela oficial para
exigir ou vedar `gRed`, `gDif`, `gTribRegular`, `gCredPresOper`, `gIBSCBSMono`,
`gEstornoCred`, `gAjusteCompet` conforme o `cClassTrib` do item.

É também a que mais pode acusar errado, porque depende de o mapa entre coluna da
tabela e caminho XML estar certo. **Contrato de segurança:** ela entra como
`aviso` no primeiro release e só é promovida a `erro` depois de rodar contra pelo
menos três XMLs reais distintos sem falso positivo. Registrar a promoção no
changelog de manutenção.

### A regra que já existe, reescrita

A `ibs-cbs-grupo-totais-presente` continua, com o motivo corrigido:

```yaml
- id: ibs-grupo-ausente
  tipo: existe
  escopo: item
  severidade: aviso
  campo: imposto/IBSCBS
  mensagem: Grupo IBSCBS ausente no item
  referencia: >
    NT 2025.002 v1.51 · UB12-10 reclassificada como implementação futura
  vigencia:
    reavaliar_em: "2026-09-01"
    fonte: "Ato Técnico Conjunto RFB/CGIBS nº 1, de 31/07/2026"
  acao: >
    Inclua o grupo IBSCBS com CST e cClassTrib no item. A rejeição
    correspondente (regra UB12-10) foi postergada para implementação futura pela
    NT 2025.002 v1.51, então a nota não é recusada por isso hoje — mas o
    destaque continua legalmente obrigatório e condiciona a dispensa de
    recolhimento do art. 348 da LC 214/2025.
```

---

## 7. A tabela oficial embarcada

Origem: **Portal da Conformidade Fácil (SVRS)** —
`https://dfe-portal.svrs.rs.gov.br/CFF/ClassificacaoTributaria`. Exporta em CSV,
Excel e JSON, com as colunas de indicador.

### Requisitos

- Vive em `regras/tabelas/`, não em `fiscal_mcp/`. É dado, como as regras.
- Acompanhada de `regras/tabelas/PROCEDENCIA.md` com, para cada arquivo: URL de
  origem, data do download, sha256 e a versão declarada pela fonte.
- Viaja dentro do wheel, pelo mesmo mecanismo `force-include` que as regras já
  usam. Um `pip install` que entrega tabela vazia é pior que um que não entrega
  tabela nenhuma.
- Um teste confere o sha256. Divergência falha o build — se o arquivo mudou sem
  passar pela procedência, alguém editou dado oficial à mão.
- O CI **não baixa a tabela**. Indisponibilidade da SVRS não pode quebrar build
  de terceiro. A atualização é ato deliberado, com PR e nova procedência.
- `fiscal-mcp tabelas` (ou equivalente) imprime qual versão está embarcada.
  Quem depende disso precisa saber contra o quê está validando.

### Os 18 CST — duas fontes secundárias independentes concordam integralmente

`000` `010` `011` `200` `220` `221` `222` `400` `410` `510` `515` `550` `620`
`800` `810` `811` `820` `830`

Conferir contra a tabela baixada antes de embarcar. Se divergir, a tabela vence.

### Formato de `cClassTrib`

Seis dígitos, `XXXYYY`, onde `XXX` é o próprio CST e `YYY` é sequencial. Essa
regra estrutural é a L-02 e não depende de tabela nenhuma — duas linhas de
código, zero dependência, e pega o erro mais relatado em produção: ERP que liga
o módulo com classificação genérica igual para todos os itens.

---

## 8. Base de cálculo: o que esta spec proíbe validar

Pelo art. 12 da LC 214/2025, a base **exclui** o próprio IBS/CBS (cálculo por
fora), o IPI, os descontos incondicionais e — transitoriamente, de 01/01/2026 a
31/12/2032 — ICMS, ISS, PIS e COFINS. **Inclui** juros, multas, encargos,
descontos condicionais, frete cobrado pelo fornecedor, seguros e taxas.

**Consequência: `vBC` não é derivável dos campos do XML.** Descontos
condicionais e incondicionais não são distinguíveis — `vDesc` é um campo só.
Qualquer regra do tipo `vBC == vProd + vFrete − vDesc` produz falso positivo.

**Fica proibido escrever regra que recompute `vBC`.** O que é verificável é a
aritmética a jusante: `vIBSUF == vBC × pIBSUF`, `vCBS == vBC × pCBS`, e os
somatórios de totais. Essas sim podem entrar — em ciclo posterior, com tolerância
calibrada contra XML real, porque arredondamento item a item é fonte conhecida
de divergência de centavos.

Uma assimetria a não assumir: na transição, IBS/CBS ficam *fora* da base do
IBS/CBS mas *entram* na base do ICMS e do ISS.

---

## 9. Testes — o contrato de qualidade

Além dos 41 testes atuais, que continuam passando sem alteração:

1. **Duas fixtures por regra.** Uma que a regra reprova e uma que ela aprova.
   Sem as duas, a regra não entra.
2. **Teste de ausência de falso positivo.** Um XML de NF-e válido e completo com
   IBS/CBS passa com zero achados de severidade `erro`. Este é o teste mais
   importante do repositório.
3. **Teste de vigência vencida.** Falha se alguma regra tem `reavaliar_em` no
   passado.
4. **Teste de procedência.** sha256 de cada tabela confere.
5. **Teste de ação.** Já existe; estender para os tipos novos.
6. **Teste de escopo.** Regra `escopo: item` numa nota de N itens é avaliada N
   vezes, e o detalhe traz o `nItem`.
7. **O teste da fatia zero continua valendo.** Nenhum caminho de código assina,
   transmite, emite ou abre socket. Os tipos novos leem dado local, e o teste
   precisa cobrir isso explicitamente.

---

## 10. O que fica de fora desta spec

- Todos os códigos numéricos de rejeição. Ver §3.
- Imposto Seletivo (`IS`, `CSTIS`, `cClassTribIS`). Os nomes `CSTIS` e
  `cClassTribIS` estão confirmados, mas o restante do grupo veio inconsistente na
  extração e o IS só entra em vigor em 2027.
- Recomputo de `vBC`. Ver §8.
- NFS-e nacional com IBS/CBS. O leiaute existe (NT SE/CGNFS-e nº 009 v1.0, de
  04/06/2026, com `gIBSCBSAjuste`, `gTribSN`, `vAjusteBC`), mas o cronograma de
  implantação não foi publicado. Ciclo posterior.

---

## 11. Documento a ler para fechar a Camada B

**NT 2025.002-RTC v1.51, seção 7 "Regras de Validação"**, colunas de regra e de
rejeição, para os grupos **UB**, **W03** e **VC**. No Portal Nacional da NF-e ou
no CGIBS. O PDF da v1.40 está em URL pública direta e o da v1.51 deve seguir o
mesmo padrão de caminho.

Enquanto essa leitura não acontecer, nenhum número de rejeição entra no
repositório. Não é excesso de cautela: é a diferença entre um validador que
software house adota e um que ela desinstala.
