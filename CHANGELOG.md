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
As entradas nascem como fragmentos em `changelog.d/` e são juntadas aqui no PR
de release (`scriv collect`) — ver CONTRIBUTING.md.

<!-- scriv-insert-here -->

## 0.3.1 — 2026-11-24

### Absorvido da legislação

- **Alíquotas de transição do IBS e da CBS, por ano de emissão.**
  - **O que mudou:** as regras de alíquota comparavam só o percentual e, a
    partir de 01/01/2027, avisariam toda nota correta. Agora cada uma vale só
    para a nota emitida no seu período, pela data local de `ide/dhEmi`; nota sem
    data legível não recebe aviso de alíquota.

    - **IBS 2026** (`ibs-aliquota-uf-2026`): 0,1% na alíquota estadual
      (`pIBSUF`), **LC 214/2025, art. 343**. Sai a ressalva "repartição entre
      estado e município não confirmada": o art. 343 a resolve.
    - **IBS 2027–2028** (regras novas `ibs-aliquota-uf-2027-2028` e
      `ibs-aliquota-mun-2027-2028`): 0,05% estadual e 0,05% municipal, **art.
      344**.
    - **CBS 2026** (`ibs-aliquota-cbs-2026`): 0,9%, **art. 346**.
    - **CBS 2027 em diante não tem regra.** O art. 347 fixa a alíquota em
      referência menos 0,1 p.p., e a referência depende de resolução do Senado
      ainda não publicada (prazo informado de 15/12/2026, não confirmado). A
      regra de 2026 reavalia nessa data.

    Todas continuam **aviso**. Combustíveis do regime específico (arts. 172–180):
    o art. 347 os exclui da CBS de transição; o art. 344, parágrafo único, III,
    não os exclui do IBS de 2027–2028, apenas aplica os 0,05% sobre o valor da
    operação. Eles vão em `gIBSCBSMono`, então estas regras não os conferem.

    Borda conhecida, sem mudança de código: o ano é o do `dhEmi` como o emissor o
    escreveu, sem converter fuso (`dhEmi` em UTC perto da meia-noite cai no ano
    seguinte), e a lei fala de fato gerador, não de emissão (devolução em
    janeiro/2027 de operação de 2026 pode receber aviso).
  - **Documento oficial:** [LC 214/2025](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm),
    arts. 343, 344, 346 e 347, de 16/01/2025.
  - **O que mudou no código:** novo bloco `emissao: {de, ate}` no motor de regras (qualquer tipo),
    validado no carregamento; regras e testes em `regras/nfe/ibs-cbs.yaml` e
    `tests/test_ibs_cbs.py`.
  - **Desde quando vale:** **01/01/2026** (2026) e **01/01/2027** (2027–2028). Lido em **24/11/2026**.

### Alterado

- **O changelog passa a nascer em fragmentos, um por PR.**
  - **O que mudou:** quem contribui deixa um arquivo em `changelog.d/` em vez
    de editar o `CHANGELOG.md`, e acaba o conflito em "Não publicado" entre PRs
    abertos ao mesmo tempo. Quem lê o CHANGELOG vê o formato mudar a partir da
    próxima versão: cada item deixa de ser um parágrafo corrido e passa a ter
    uma sublista com os quatro rótulos (o que mudou, documento oficial, o que
    mudou no código, desde quando vale).
  - **Documento oficial:** não se aplica (mudança de processo, não fiscal).
  - **O que mudou no código:** configuração do scriv em `pyproject.toml`
    (`[tool.scriv]`), modelo em `changelog.d/_modelo.md.j2`, marcador de
    inserção no `CHANGELOG.md`, `tests/test_changelog_d.py` cobrando
    os quatro campos de cada item, e a seção "Changelog" no CONTRIBUTING.md.
  - **Desde quando vale:** não se aplica — vale para os PRs abertos a partir
    deste.

- **A conferência do pacote antes de publicar virou um script só, com erro claro.**
  - **O que mudou:** nada muda para quem usa o pacote. Para quem publica: o
    workflow de publicação e o de PR conferem o wheel com o mesmo script, e
    arquivo faltando, tabela ilegível ou tabela com código trocado saem como
    `::error::` com a causa, em vez de exceção crua.
  - **Documento oficial:** não se aplica (mudança de CI, não fiscal).
  - **O que mudou no código:** `scripts/conferir_pacote.py`, usado por
    `publicar.yml` e pelo job `instalacao-limpa` do `testes.yml` (sai o
    `== 173` fixo); actions `checkout` v7, `setup-python` v7,
    `upload-artifact` v7 e `download-artifact` v8, em Node 24; espelho
    `.docker-mcp-registry` no commit da v0.3.0; `tests/test_conferir_pacote.py`.
  - **Desde quando vale:** não se aplica — próxima versão.

### Corrigido

- **cClassTrib inexistente gerava dois erros, um deles com mensagem falsa.**
  - **O que mudou:** um código que não está na tabela oficial agora gera só
    `ibs-cclasstrib-existe`. Antes gerava também `ibs-cclasstrib-modelo`, cuja
    ação dizia "este código existe, mas não para o modelo desta nota".
  - **Documento oficial:** não se aplica (correção de mensagem; nenhuma regra
    fiscal mudou).
  - **O que mudou no código:** `fiscal_mcp/regras.py`, tipo `em_tabela`: regra
    com filtro (a de modelo) não julga mais existência, que fica com a regra
    irmã sem filtro. Testes em `tests/test_ibs_cbs.py` e
    `tests/test_tipos_de_regra.py`. Varredura dos 173 códigos da tabela em NF-e
    e NFC-e: nenhum achado mudou para código existente.
  - **Desde quando vale:** não se aplica — próxima versão.

---

## 0.3.0 — 2026-11-24

### Absorvido da legislação

- **Tabela de Classificação Tributária (CST × cClassTrib) atualizada.** A SVRS
  republicou a tabela duas vezes depois da versão embarcada (22/06/2026): em
  **01/10/2026** e em **30/10/2026** (maior `DthPublicacao`). Comparando o
  arquivo embarcado com o que estava no ar em 24/11/2026:

  - **9 cClassTrib novos**, todos com início de vigência em 01/01/2026:
    `000006`, `200055`, `200056` (autônomo — só NFS-e), `400003`, `400004`
    (bagagens e remessas internacionais — DIR e DUIMP), `550026` a `550029`
    (admissão temporária na ZFM, drawback, admissão temporária em
    aperfeiçoamento e ZPE — valem em NF-e).
  - **Nenhum CST ou cClassTrib removido.** Os 18 CST continuam os mesmos.
  - **164 cClassTrib alterados.** Em todos, o campo novo `TipoDoacao`: nos 164
    alterados, 124 com `0`, 38 com `2` e 2 com `1`; nos 173 da tabela nova
    (somando os 9 novos), 130 com `0`, 41 com `2` e 2 com `1`. Em 33 dos 164 há
    mudança além disso:
    - indicadores de documento: `IndNfe` (5 — passou a valer em NF-e para
      `410022` a `410025`, deixou de valer para `550002`), `IndDir` (5),
      `IndDuimp` (4), `PossuiIndDfe` (5), `IndCteos`, `IndNfabi`, `IndNfse` e
      `IndDere` (1 cada);
    - indicador de crédito: `IndPermiteCredPres` desligado em `410014`;
    - texto: `NomeClassTrib` (7), `NomeReduzido` (6), `TexRegIbs` e `TexRegCbs`
      (5 cada) — doações passam a citar amostras grátis, `410036` passa de
      "descontos incondicionais" a "descontos financeiros em nota fatura";
    - `DthPublicacao` (30), sendo 9 só com a data nova.
  - **Nenhuma vigência (`DthIniVig`/`DthFimVig`) mudou.**

  O que muda no comportamento do validador: os 9 códigos novos deixam de ser
  "cClassTrib inexistente"; em NF-e, `410022` a `410025` e `550026` a `550029`
  passam a ser aceitos; `000006`, `200055` e `200056` existem, mas são
  reprovados em NF-e por serem só de NFS-e.

  Dois efeitos viram **aviso**, não erro:

  - **`550002` em NF-e — decisão de transição.** A tabela desligou o `IndNfe`
    sem fim de vigência, e o motor não olha a data de emissão: como erro, nota
    emitida enquanto o código valia seria reprovada hoje, e não há fonte
    primária de que a SEFAZ rejeite cClassTrib × modelo em produção. Sai pela
    regra nova `ibs-cclasstrib-modelo-transicao` (aviso, reavaliar em
    14/12/2026), que diz que o código deixou de ser permitido em NF-e a partir
    da tabela publicada em 30/10/2026. O recorte vale **só em NF-e**: em NFC-e
    o `550002` nunca valeu (`IndNfce` falso nas duas tabelas) e continua erro.
    O resto da `ibs-cclasstrib-modelo` continua erro.
  - **`410014` com `gCredPresOper`.** O aviso de subgrupos deixa de exigir o
    grupo e passa a não admiti-lo: nota antiga que o traga recebe aviso novo.

  Código: `regras/tabelas/cst-cclasstrib.json` baixado de novo por
  `scripts/baixar_tabelas.py`, sha256 e contagens atualizados na
  `PROCEDENCIA.md`. O tipo `em_tabela` ganhou os recortes `somente`,
  `exceto`, `exceto_nos_modelos` e `modelos`, para um código em transição ter
  severidade própria numa regra irmã, por modelo, sem exceção escrita no motor.
  O carregamento recusa recorte mal escrito: valor que não é lista de textos
  (`"550002"` solto, `[000006]` sem aspas), código que não existe na tabela e
  modelo desconhecido. Um teste garante que todo código excluído tem uma regra
  que o avalia nos mesmos modelos. Testes travam os casos acima.

  Detectado pelo monitor de fontes em **28/09/2026** (4 alterados, ainda sem
  publicação nova), **05/10/2026** (publicação de 01/10/2026) e **12/10/2026**
  (campo `TipoDoacao` em todos os 164). A republicação de 30/10/2026 foi
  encontrada no download de **24/11/2026**. Vigência dos códigos novos declarada
  pela fonte: desde **01/01/2026**. Suportado na **próxima versão**.

  Documento oficial: **IT 2025.002 v1.71 — Tabelas de Classificação do IBS e da
  CBS** ([PDF](https://dfe-portal.svrs.rs.gov.br/DFE/DownloadArquivoEstatico/?sistema=DFE&tipoArquivo=16&nomeArquivo=IT%202025.002%20v.1.71%20-%20Tabelas%20de%20Classifica%C3%A7%C3%A3o%20do%20IBS%20e%20da%20CBS.pdf),
  30/10/2026), §07.09 (v1.70) e §07.10 (v1.71). O IT registra a desativação do
  `550002` em NF-e na sua v1.60 (§07.08, "Desativação para NFe: 550002"),
  embora o arquivo de 22/06/2026 ainda o trouxesse ativo. Dado: Tabela de Classificação Tributária do Portal da Conformidade
  Fácil (SVRS).

- **NT 2025.002-RTC v1.52 e v1.53 — UB12-10 continua sem data.** A v1.53
  ([PDF](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=BMcHSMEoepU=),
  publicada em **30/10/2026**) mantém a UB12-10 como "implementação futura para
  produção", como fazem a v1.51 e a v1.52
  ([PDF](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=HXPO8VLbh4o=),
  publicada em **01/10/2026**). A rejeição por ausência do grupo `IBSCBS`
  continua **inativa em produção**.

  As regras de validação que mudaram nas duas versões tratam de devolução e
  referenciamento: a chave pode vir no cabeçalho (`NFref`) **ou** no item
  (`DFeReferenciado`), e `nItem` passa a ser opcional. Produção em 16/11/2026,
  sem adiamento. Nenhuma regra do fiscal-mcp trata de devolução, então nada
  muda no validador por isso.

  A v1.53 também move a **produção da reformulação de monofasia da v1.50** de
  03/11/2026 para **16/11/2026**. O fiscal-mcp valida a presença do grupo de
  monofasia (`ibs-cst-620-exige-mono`) e o schema embarcado (PL 010f v1.04) já
  traz a estrutura da v1.50, então nada muda aqui por isso.

  Código: `ibs-grupo-ausente` segue como **aviso**, agora citando a v1.53. As
  quatro regras com `reavaliar_em` vencido (`ibs-grupo-ausente`,
  `ibs-subgrupos-obrigatorios`, `ibs-aliquota-uf-2026`, `ibs-aliquota-cbs-2026`)
  passam a reavaliar em **14/12/2026**, o próximo marco oficial do cronograma,
  com a justificativa escrita em cada uma. Nenhuma severidade mudou.

  A v1.52 foi detectada pelo monitor em **05/10/2026**. A v1.53 foi encontrada
  na conferência de **24/11/2026**. Obrigatório: devolução desde
  **16/11/2026**; UB12-10 sem data.

- **PL 010h v1.03 — grupo `gTribSN` (Simples Nacional).** O pacote de schemas
  ([ZIP](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=YhWikFoTxUo=),
  publicado em **13/11/2026**) implementa a NT 2026.005 v1.00
  ([PDF](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=HInG7WD5Sj8=),
  30/10/2026). Ele cria `gTribSN` dentro de `IBSCBS`, opcional e fora do choice
  de regime, e em `IBSCBSTot`. A `nfelib` publicada (3.3.0) ainda não traz esse
  pacote. Ela embarca o **PL 010f v1.04** (31/08/2026), que já cobre a
  monofasia da NT 2025.002 v1.50 — o risco "o pacote não cobre a v1.50" das
  specs 05/06 e do BACKLOG está superado.

  Código: nenhuma mudança no motor. O rebaixamento por versão já transforma
  `gTribSN` em aviso; um teste novo trava isso com o grupo no item e no total
  (zero erro, com e sem o extra `[xsd]`). A fixture foi conferida contra o XSD
  do PL 010h, onde a única queixa é a falta de assinatura.

  Obrigatório desde **14/12/2026** (era 16/11/2026), pelo aviso CGIBS/RFB de
  12/11/2026 no [Portal da Conformidade Fácil](https://dfe-portal.svrs.rs.gov.br/CFF/Avisos),
  que adiou também as NT 2026.006 e 2026.008. Detectado na conferência de
  **24/11/2026**.

- **NT 2026.008 — a regra UB16-10 foi removida.** Quem a removeu foi a v1.00
  ([PDF](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=qAoMot6VyiY=),
  01/10/2026): a UB16-10 tratava da composição da base de cálculo do IBS/CBS.
  A v1.01
  ([PDF](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=PVjdIcA/H2s=),
  30/10/2026) mantém a remoção e tira o item "composição do valor do produto
  com IBS e CBS". O fiscal-mcp não valida a base de cálculo, então nada muda. Fica
  registrado para que a Camada B **não** catalogue essa rejeição. Detectado pelo
  monitor em **05/10/2026** (v1.00). Produção adiada para **14/12/2026**.

- **Notas técnicas lidas, sem efeito no validador.** Nenhuma toca o grupo
  `IBSCBS`, CST, cClassTrib ou totais:
  - **31/08/2026:** NT 2026.006 v1.00 (vinculação ao pagamento; produção
    adiada para 14/12/2026).
  - **14/09/2026:** NT 2026.009 v1.00 (CFOP 1.949/2.949, de 09/09/2026).
  - **05/10/2026:** NT 2026.007 v1.10 (cadastros LCC-RFB e CCC; produção em
    16/11/2026) e NT 2026.010 v1.00 (DANFE da RTC, só a representação
    impressa), ambas de 01/10/2026.
  - **24/11/2026** (conferência): NT 2023.002 v1.02 (NFC-e: fim da autorização
    assíncrona e da inutilização), de 27/10/2026.

- **Notas técnicas com assunto conferido, sem impacto em IBS/CBS, conteúdo não
  lido.** O delta de cada uma em relação à versão anterior não foi lido; só o
  assunto, que não toca IBS/CBS:
  - **31/08/2026:** NT 2026.002 v1.10a (DANFE Simplificado).
  - **28/09/2026:** NT 2021.003 v1.50 (GTIN) e NT 2023.003 v1.40 (CFOP na
    NFC-e), ambas de 25/09/2026.
  - **05/10/2026:** NT 2026.002 v1.11 (DANFE Simplificado Tipo 2), de
    01/10/2026.

  Fonte: [lista de Notas Técnicas do Portal da NF-e](https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=04BIflQt1aY=).

### Fontes monitoradas

- `regras/fontes.yaml` foi semeado com as Notas Técnicas no ar em 24/11/2026.

### Alterado

- **Mínimo do extra `[xsd]` passa a `nfelib>=2.6.0`** (era `>=2.5`). A 2.6.0 é
  a primeira versão que embarca o **PL 010f v1.04**, com os XSD idênticos aos
  do ZIP oficial, e cobre a monofasia da NT 2025.002 v1.50, em produção desde
  16/11/2026. A 2.5.3, imediatamente anterior no PyPI, não declara pacote e não
  tem `gIBSMonoAdRem`: com ela, nota com a estrutura nova recebia aviso de
  "não conhecido pelo pacote" em vez de passar. Evidência no cabeçalho de
  `regras/schema/pacotes.yaml`.

### Corrigido

- **`leiaute_validado_contra` declarava o pacote de schema errado.** Com a
  `nfelib` 3.3.0 o laudo dizia `PL_005d`, mas o conteúdo embarcado é o **PL
  010f v1.04**. O nome era tirado do maior `PL_` citado no comentário do
  `leiauteNFe_v4.00.xsd`, que lista pacotes antigos e não diz qual é o vigente.

  Agora o pacote é identificado **pelo conteúdo**: o sha256 de cada XSD
  instalado é comparado com o do ZIP oficial do Portal da NF-e, registrado com
  procedência em `regras/schema/pacotes.yaml` (PL 010e v1.02, PL 010f v1.04 e PL
  010h v1.03). O que a própria `nfelib` declara (`SCHEMA_PACKAGE`, desde a
  2.6.0) serve de conferência: se divergir do conteúdo, a saída diz isso.
  Conteúdo fora do registro sai como "pacote não identificado", nunca com um
  nome adivinhado. Um teste falha se a declaração e os XSD instalados
  divergirem.

  Detectado em **24/11/2026**, na revisão da camada de schema.

---

## 0.2.1 — 2026-08-26

Correção de publicação. Nenhuma mudança de comportamento do validador.

### Corrigido

- **O identificador do servidor MCP estava com a grafia errada.** Era
  `io.github.josetorquato/fiscal-mcp`; o correto é
  `io.github.JoseTorquato/fiscal-mcp`, com a grafia exata do usuário do GitHub.

  O registry autoriza o namespace de forma **sensível a maiúsculas**, e a
  verificação de posse procura a string exata na description publicada no PyPI.
  Como a description só muda com um novo release, corrigir o README não bastava —
  daí esta versão existir.

  A trava do CI comparava o README com o `server.json` e os dois concordavam
  entre si, ambos errados. Agora ela confere também contra o dono e o nome do
  repositório, que é o que o registry realmente autoriza.

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
