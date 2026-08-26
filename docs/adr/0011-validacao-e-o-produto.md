# ADR-0011 — Validação é o produto; emissão sai do caminho crítico

- **Data:** 25/08/2026
- **Status:** aceita · refina [0008](0008-validar-antes-de-construir.md) · suspende [0003](0003-integracao-direta-com-sefaz.md)

## Contexto

O [ROADMAP](../../ROADMAP.md) original trata a validação local como **fatia zero**
— algo que existe para tornar as conversas de validação concretas — e a emissão
de NF-e como o produto de verdade, a partir da fase 1.

Uma pesquisa de posicionamento em quatro frentes, feita em 25/08/2026, mudou
três premissas nas quais essa ordem se apoiava.

### 1. Emissão deixou de ser terreno livre

O [ADR-0003](0003-integracao-direta-com-sefaz.md) e a fase 1 do roadmap tratam a
emissão direta como risco técnico a ser eliminado por um spike: *"isso é viável
para uma pessoa?"*. A resposta já está publicada, por terceiros:

- **`saviski/nfse-nacional-mcp`** faz assinatura XMLDSig RSA-SHA256, sessão mTLS
  e `POST` direto ao Sistema Nacional de NFS-e, em 2.737 linhas de Python.
- **`codespar/mcp-dev-latam`** publicou, num único monorepo MIT, quatro
  servidores MCP de emissão sobre Nuvem Fiscal, Focus NFe, NFE.io e Conta Azul.
- **BrasilNFe** vende emissão de NF-e, NFC-e, NFS-e, CT-e, MDF-e e DC-e por MCP,
  hospedado, a partir de R$ 49,90/mês com emissão ilimitada.

O risco que sobrou na emissão não é técnico. É econômico — competir a R$ 0,05 a
R$ 0,15 por nota contra quem tem escala de infra — e é de responsabilidade civil:
credenciamento obrigatório de software house em cinco estados (CE, ES, PA, PR,
SC) para NFC-e, e responsabilização por falha técnica que **não é afastada
automaticamente por cláusula contratual limitativa**.

### 2. O nicho de validação offline está ocupado só na aparência

O maior concorrente, `DeHor-Labs/mcp-fiscal-brasil`, é sério: 44 tools reais,
15,4 mil linhas, CI completo, presença em todos os catálogos. Mas a auditoria de
código encontrou três lacunas centrais:

- **Não há validação XSD.** O README anuncia; o código admite que não faz.
- **As "tabelas offline" têm 138 NCMs** num SQLite de 57 KB. A TIPI tem ~10.515.
  CNAE, CEP, CNPJ, Simples, MEI, IBGE e BCB são chamadas HTTP.
- **A tool de validação principal não é offline** — faz uma consulta à Receita
  no meio para checar o CNPJ do emitente.

Ninguém entrega hoje validação de schema real, nem garantia verificável de
zero-rede, nem catálogo de rejeição com ação.

### 3. Dois pilares da camada paga estão sendo destruídos por fatores externos

A [spec 00](../spec/00-produto.md) lista quatro pilares para a camada paga.
Dois não sobrevivem ao exame:

- **Cobertura municipal de NFS-e** — a NFS-e Nacional, obrigatória desde
  01/01/2026, substitui 5.500+ sistemas municipais por um leiaute único. O maior
  fosso do setor está sendo estatizado.
- **SLA** — é produto de seguro: exige plantão e balanço. Prometer e não cumprir,
  em projeto de tempo parcial, é exposição civil sem contrapartida.

## Decisão

**A validação local é o produto, não a fatia zero.** Concretamente:

1. **Nenhum trabalho de emissão, assinatura, transmissão ou certificado** —
   incluindo o spike da fase 1 — até que o gatilho de revisão abaixo dispare.
   O [ADR-0003](0003-integracao-direta-com-sefaz.md) fica **suspenso**, não
   revogado: a decisão de integrar direto continua correta *se* houver emissão.
2. **O eixo de investimento passa a ser profundidade de validação**: schema XSD
   oficial, regras estruturais de IBS/CBS derivadas de tabela publicada, e
   catálogo de rejeições com ação.
3. **A garantia de zero-rede vira característica declarada e testada**, não
   consequência acidental de ainda não ter integração.
4. **A cobertura municipal de NFS-e sai da proposta de valor paga.** O que fica é
   o padrão nacional.
5. **SLA sai da proposta até existir equipe.** O que se pode prometer sozinho é
   um registro público de mudanças absorvidas, com data de detecção e data de
   suporte — evidência observável, não compromisso de disponibilidade.

## Justificativa

**O gate do [ADR-0008](0008-validar-antes-de-construir.md) continua valendo, e
esta decisão o reforça.** Aquele ADR proíbe construir integração antes de provar
disposição a pagar. A pesquisa mostrou algo mais forte: a disposição a pagar
existe e já está provada — o ACBr Pro cobra R$ 1.500/ano de software houses por
exatamente essa promessa, e a TecnoSpeed tem 4.100+ software houses integradas.
O que não está provado é que alguém pagaria **a este projeto** em vez de a eles.
Emissão não responde essa pergunta; profundidade de validação, sim.

**A vantagem defensável é acúmulo, não feature.** O catálogo de rejeições com
`significa` + `acao` + `reversivel` é a única coisa aqui que não se copia numa
tarde, porque cresce com uso real. Emissão, ao contrário, é problema resolvido
por três atores e comoditizado a R$ 0,10/nota.

**Regras como dados continua sendo a tese estrutural correta**, e ela se aplica
melhor à validação que à emissão. O concorrente codifica regras em Python: cada
nota técnica é um release. Aqui, é um arquivo YAML.

**O custo de reverter é baixo.** Se o gatilho disparar, a emissão volta ao
roadmap com a camada de validação pronta — que é, de qualquer forma, o que
deveria rodar antes de qualquer transmissão.

## Alternativas descartadas

**Seguir o roadmap original e fazer o spike de emissão.** Descartada: gasta o
recurso mais escasso do projeto — fim de semana de uma pessoa — para responder
uma pergunta que três repositórios públicos já responderam.

**Embrulhar um provedor (Nuvem Fiscal, Focus NFe) em vez de integrar direto.**
Descartada: quatro wrappers desses já existem, num único monorepo de um dev só.
É a definição de commodity, e ainda transfere o lock-in e o custo ao usuário.

**Manter emissão como meta declarada, sem trabalhar nela.** Descartada por
honestidade: prometer emissão no README enquanto ela não vem é o mesmo pecado
que o concorrente comete ao anunciar validação XSD que não existe. Se não vai
ser feito neste horizonte, sai do README.

## Consequências

- **A promessa pública do projeto encolhe e fica mais nítida.** README, ROADMAP e
  spec 00 precisam ser reescritos. O que se perde em ambição se ganha em ser
  verificável — que é a moeda deste nicho.
- **A camada paga fica sem produto óbvio no curto prazo.** É desconfortável e é
  correto: a pesquisa mostra que o caminho de receita mais viável para dev solo
  em tempo parcial é consultoria de adequação e assinatura anual estilo clube,
  não API por documento. Nenhum dos dois exige emissão.
- **Perde-se a chance de ser "o MCP que emite".** Aceito. Esse lugar tem dono, e
  o dono cobra R$ 49,90/mês com infra e suporte 24/7.
- **Ganha-se um lugar mais estreito e mais defensável:** o validador em que se
  confia antes de transmitir — inclusive por quem emite pelos outros.

## Gatilho de revisão

Esta decisão volta à mesa se **qualquer uma** ocorrer:

1. **Três ou mais interlocutores distintos** pedirem emissão espontaneamente
   durante as conversas de validação — não respondendo a uma pergunta sobre
   emissão, mas trazendo o assunto.
2. **Alguém pagar adiantado** por emissão, com valor nomeado por ele.
3. **A camada de validação atingir seu teto**: as regras estruturais e o schema
   estarem completos, com um registro de manutenção de pelo menos seis meses, e
   o projeto continuar sem tração. Aí o problema não era o produto ser raso.
4. **O PyNFe ou um provedor grande lançar MCP oficial de validação.** Nesse
   cenário a diferenciação por validação evapora e todo o posicionamento precisa
   ser repensado — não só a emissão.

## Nota sobre o que não muda

O [ADR-0005](0005-certificado-nunca-transita.md) (não custodiar certificado) e o
[ADR-0007](0007-homologacao-por-padrao.md) (homologação por padrão) continuam
válidos e passam a ser, por ora, hipotéticos. Ficam escritos porque o dia em que
a emissão voltar, voltam com ela — e a tentação de furá-los vem justamente no
momento de fechar o primeiro contrato.
