# Changelog

Este arquivo não é higiene de repositório. É a evidência de que a manutenção
acontece — o que um dev de ERP realmente avalia antes de adotar uma dependência
fiscal. Ver [spec 04](docs/spec/04-manutencao.md).

Cada mudança fiscal registra quatro coisas:

**o que mudou** · **qual documento oficial determinou** · **o que mudou no
código** · **desde quando é obrigatório**

O par **data de detecção / data de suporte** é o que separa "eu mantenho isso"
de um fato observável. Sem histórico, manutenção é promessa; com histórico, é
produto.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

---

## 0.2.0 — 2026-08-25

Primeira versão com a Camada A de IBS/CBS e validação por schema XSD.

### Absorvido da legislação

- **NT 2025.002-RTC v1.51** — a regra de validação **UB12-10**, que exigiria o
  grupo `IBSCBS` nos itens, foi reclassificada de data fixa (03/08/2026) para
  **implementação futura**, sem cronograma. A rejeição por ausência do grupo
  **não está ativa em produção** para NF-e e NFC-e.

  A regra `ibs-grupo-ausente` continua como **aviso**, com o texto corrigido: a
  versão anterior afirmava que a nota "pode ser rejeitada", o que deixou de ser
  verdade. A postergação é técnica, não jurídica — o destaque continua
  legalmente obrigatório e condiciona a dispensa de recolhimento do art. 348 da
  LC 214/2025.

  Detectado em **25/08/2026**, suportado em **0.2.0**.
  Fonte: Ato Técnico Conjunto RFB/CGIBS nº 1, de 31/07/2026.

- **Tabela de Classificação Tributária (SVRS)**, publicação de **22/06/2026** —
  18 CST e 164 `cClassTrib` embarcados com procedência e sha256, em
  [`regras/tabelas/`](regras/tabelas/PROCEDENCIA.md). O CI nunca baixa: a
  atualização é ato deliberado, com PR e nova procedência.

  Detectado em **25/08/2026**, suportado em **0.2.0**.

### Adicionado

- **Validação por schema XSD oficial** (extra `[xsd]`), com as mensagens do
  `lxml` traduzidas para português acionável. A saída declara o pacote de
  schemas em uso no campo `leiaute_validado_contra`.
- **18 regras da Camada A de IBS/CBS**: CST e `cClassTrib` contra a tabela
  oficial, aritmética por item, exclusividade de regime, presença condicional e
  alíquotas de transição de 2026.
- **`escopo: item`** no motor de regras — regra avaliada uma vez por item, com o
  achado identificando o item pelo `nItem`.
- **Seis tipos novos de regra**: `prefixo_de`, `em_tabela`,
  `subgrupos_por_indicador`, `soma_campos`, `exclusivo` e `valor_numerico_em`.
- **Bloco `vigencia`** nas regras, com `reavaliar_em` obrigatório em data
  concreta. Um teste falha quando a data passa, e ele roda semanalmente em CI —
  é o que impede a manutenção de depender de memória.
- **`fiscal-mcp tabelas`** mostra qual versão da tabela oficial está embarcada.
  Quem valida contra tabela precisa saber contra qual.
- `Dockerfile` e `server.json`.

### Corrigido pela leitura do XSD oficial

O XSD é a verdade executável, e conferir contra ele corrigiu três coisas que a
leitura do leiaute em PDF tinha deixado erradas:

- `gCredPresIBSZFM` fica sob `IBSCBS`, **não** sob `gIBSCBS/gCBS`.
- Existe um **segundo choice** no grupo, não documentado na nota que consultamos:
  `gCredPresOper` e `gCredPresIBSZFM` são mutuamente exclusivos. Virou a regra
  `ibs-credito-presumido-exclusivo`.
- A validação de `cClassTrib` por modelo de documento usa os indicadores `IndNfe`
  e `IndNfce` da tabela oficial, que existem por classificação.

### Corrigido antes de sair

- **`ibs-competapur-formato` tinha falso positivo.** O padrão exigia `AAAA-MM`
  puro; o tipo real no XSD é `xs:gYearMonth`, que admite sufixo de fuso —
  `2026-08Z` e `2026-08+03:00` são válidos e seriam reprovados. Encontrado ao
  conferir se o schema tornava a regra redundante.

  A regra ficou (é a única cobertura sem o extra `[xsd]`) com o padrão alinhado
  ao tipo. Ela não verifica o `minInclusive 2025-01` que o schema verifica:
  **pegar menos é aceitável, acusar errado não é.**

  Das duas regras de `formato` escritas a partir da leitura do leiaute, as duas
  estavam erradas. A lição virou anotação na [spec 06](docs/spec/06-validacao-xsd.md).

### Removido

- **Regra de escala decimal (`ibs-escala-decimal`)** — não só era redundante com
  o XSD, **estava errada**. O padrão real do tipo `TDec1302RTC` aceita `0`
  sozinho; a regra escrita à mão exigia sempre duas casas e teria reprovado
  `<vIBS>0</vIBS>`, que é válido. Escala decimal passou a ser responsabilidade da
  camada de schema.

- **Regra de domínio de `tpALCZFMCBS`** — o elemento não existe no pacote de
  schemas oficial, e o domínio `{1, 2}` veio de extração automatizada de PDF, sem
  confirmação em fonte primária. Volta quando aparecer num pacote de schema, com
  o domínio lido do XSD.

- **Campo `status: pendente_confirmacao`** nas regras, substituído pelo bloco
  `vigencia`. Era honesto e não tinha saída: nada obrigava a revisitar. YAML que
  ainda use `status` falha o carregamento com a instrução de migração.

### Sobre severidade

Duas regras nascem como **aviso** de propósito, e a razão está em cada uma:

- `ibs-subgrupos-obrigatorios` depende de o mapa entre indicador da tabela e
  caminho XML estar certo. Vira erro só depois de rodar contra três XMLs reais
  distintos sem falso positivo — a promoção será registrada aqui.
- `ibs-aliquota-uf-2026` e `ibs-aliquota-cbs-2026`: a repartição dos 0,1% entre
  parcela estadual e municipal não está confirmada em fonte oficial. Enquanto a
  dúvida existir, a regra não reprova.

### Validação contra documento real

Em **26/08/2026**, depois da publicação da 0.2.0, o validador foi rodado em duas
NF-e reais **autorizadas pela SEFAZ em ambiente de produção**:

- **nota com o grupo IBS/CBS preenchido** (emitida em 26/08/2026): zero achados,
  de qualquer severidade, nas 28 regras e no XSD oficial;
- **nota anterior ao grupo** (emitida em 09/04/2026): zero erros e um aviso —
  `ibs-grupo-ausente`, com o texto da postergação.

Que as regras não estavam dormentes foi verificado por contraprova sobre o mesmo
documento: corrompendo o `cClassTrib`, três regras disparam; corrompendo o `CST`,
duas.

**Ainda não coberto por nota real:** monofasia (CST 620), redução de alíquota,
crédito presumido, ajuste de competência e nota com mais de um item. A regra
`ibs-subgrupos-obrigatorios` continua como aviso — a promoção a erro exige três
XMLs reais distintos sem falso positivo, e há um.

### Nota sobre códigos de rejeição

Nenhuma mensagem deste projeto cita um código numérico de rejeição, e há teste
que garante isso. Durante a pesquisa, uma extração automatizada do PDF da nota
técnica produziu códigos inexistentes (faixa 1004–1011), que foram descartados.
Citar um número errado é pior que não citar número nenhum.

---

## 0.1.0 — 2026-08-10

Primeira versão pública. Validação local de NF-e, NFC-e e NFS-e do padrão
nacional, catálogo de rejeições, análise de chave de acesso, CLI e servidor MCP.
