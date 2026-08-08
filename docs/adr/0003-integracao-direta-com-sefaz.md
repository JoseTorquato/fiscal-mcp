# ADR-0003 — Integrar direto com SEFAZ, não via intermediário

- **Data:** 06/08/2026
- **Status:** aceita

## Contexto

Existem provedores que já resolvem a parte difícil e expõem REST amigável
(Nuvem Fiscal, Focus NFe, PlugNotas e outros). Envelopar um deles seria muito
mais rápido: dá para ter servidor MCP funcionando em dias.

É exatamente o que faz o concorrente mais adiantado que encontramos
(`rodrigo-do-carmo/mcp-nota-fiscal`).

## Decisão

Integrar **direto com os webservices da SEFAZ e com o padrão nacional de NFS-e**.
Não envelopar intermediário como caminho principal.

## Justificativa

**1. Envelopar intermediário não é produto, é conveniência.** Se o valor é a API
do provedor, o provedor pode lançar o próprio MCP e nos apagar num dia.

**2. O fosso está justamente no que o intermediário esconde.** Certificado,
assinatura, homologação, nota técnica — terceirizar isso é terceirizar a razão de
existir.

**3. Custo empilhado.** O cliente pagaria o provedor *e* a gente. Difícil de
justificar.

**4. Dependência de terceiro em caminho crítico.** Provedor fora do ar = nosso
produto fora do ar, sem nada a fazer.

**5. A telemetria que vira moat some.** Passando por intermediário, não vemos o
padrão de rejeição real da SEFAZ.

## Consequências

**Negativas, e são pesadas:**

- muito mais lento até a primeira emissão funcionando;
- exige aprender assinatura XML, SOAP e as particularidades de cada UF;
- homologação da SEFAZ é instável e vai custar tempo de depuração;
- superfície de manutenção maior — que é o produto, mas também é o custo.

**Positivas:** independência, margem inteira, e o conhecimento que nenhum
concorrente que envelopa terá.

## Exceção deliberada

Adapter opcional para intermediário é aceitável como **caminho de contingência**:
quem já usa provedor consegue começar sem migrar, e migra depois. Não é o
caminho principal e não recebe prioridade de manutenção.

Isso também dá um teste de mercado barato: se todo mundo escolher o adapter de
intermediário e ninguém usar o direto, a tese deste ADR está errada.

## Revisão

Reavaliar se: a integração direta se mostrar inviável para um desenvolvedor solo
dentro do prazo da fase 2 do roadmap; ou se o padrão nacional de NFS-e absorver
a complexidade municipal a ponto de o intermediário perder sentido para todos.
