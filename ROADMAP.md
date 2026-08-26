# Roadmap

Reescrito em 25/08/2026, depois de uma pesquisa de posicionamento que derrubou
três premissas da versão anterior. A decisão e o porquê estão no
[ADR-0011](docs/adr/0011-validacao-e-o-produto.md); a versão antiga continua no
histórico do git.

**O que mudou em uma frase:** a validação local deixou de ser a fatia zero e
passou a ser o produto. Emissão saiu do caminho crítico.

Cada fase tem **critério de saída**. Não se avança sem cumprir.

---

## O que este projeto é

Um validador de documento fiscal brasileiro que **roda offline, é auditável, e
você pode conferir antes de transmitir** — exposto como ferramenta de agente e
como linha de comando.

O que ele não é, e não vai ser neste horizonte: emissor, intermediário,
consultoria tributária. Ver [ADR-0011](docs/adr/0011-validacao-e-o-produto.md).

## Por que esse lugar existe

Três fatos apurados em agosto de 2026:

- Nenhum servidor MCP fiscal brasileiro faz **validação por schema XSD**. O maior
  deles anuncia e não faz.
- Nenhum oferece **garantia verificável de zero-rede**. Todos misturam consulta
  online com validação local, inclusive nas tools que chamam de offline.
- Nenhum tem **catálogo de rejeição com ação** — o mais próximo são 26 pares de
  código e texto, sem dizer o que fazer.

As três lacunas são exatamente onde este projeto já aponta. A janela é de meses,
não de anos: são falhas corrigíveis por um mantenedor ativo.

---

## Fase A — Confiança · *em andamento*

**Objetivo:** ser o validador mais fundo que existe para NF-e, e provar isso com
dado verificável em vez de alegação de README.

- [ ] Motor de regras com escopo por item e os tipos novos ([spec 05](docs/spec/05-camada-a-ibs-cbs.md))
- [ ] Tabela oficial de CST e `cClassTrib` embarcada, versionada e com procedência
- [ ] As 14 regras estruturais de IBS/CBS, cada uma com fixture que reprova e fixture que aprova
- [ ] Validação por schema XSD via `nfelib`, com mensagens traduzidas ([spec 06](docs/spec/06-validacao-xsd.md))
- [ ] Nenhuma regra em `pendente_confirmacao` — ou tem vigência, ou tem data de reavaliação, ou sai
- [ ] Teste de zero-rede cobrindo as camadas novas

**Critério de saída:** um XML de NF-e válido com IBS/CBS passa sem nenhum erro, e
um XML com `cClassTrib` incompatível com o CST é reprovado com ação acionável.
As duas coisas, no mesmo release.

**O que faz esta fase falhar:** um falso positivo em nota real. Regra que acusa
errado é desinstalada no mesmo dia e não volta. Ao primeiro relato, a regra vira
aviso — sem discussão.

---

## Fase B — Descoberta

**Objetivo:** ser encontrável por quem tem o problema no momento em que tem.

- [ ] Registry oficial de MCP, Awesome MCP Servers, claim no Glama ([spec 07](docs/spec/07-distribuicao.md))
- [ ] Dockerfile e PR no Docker MCP Catalog — o público-alvo é majoritariamente Delphi e C#, não Python
- [ ] `CHANGELOG.md` amarrado a nota técnica, com data de detecção e data de suporte
- [ ] Script de anonimização de XML + `CONTRIBUTING.md` com a regra de contribuição
- [ ] Conteúdo técnico de cauda longa, por código de rejeição, escrito para dev e não para contador
- [ ] Validador no navegador: cola o XML, recebe o laudo, sem upload

**Critério de saída:** alguém de fora valida um XML real e relata o resultado.
É o mesmo critério da antiga fase 0.5, e continua sendo o único sinal que importa
nesta etapa.

---

## Fase C — Evidência de manutenção

**Objetivo:** transformar "eu mantenho isso" de promessa em fato observável.
Esta fase é a que justifica cobrar depois.

- [ ] Teste de vigência vencida rodando em CI — falha quando alguma regra passou da data de reavaliação
- [ ] Monitor de publicação de nota técnica, abrindo tarefa quando sai documento novo
- [ ] Registro público de cada mudança fiscal absorvida
- [ ] Suíte de validação contra corpus de XMLs reais anonimizados, com resultado público

**Critério de saída:** uma mudança real de leiaute absorvida e registrada, com
data de detecção e data de suporte. Sem histórico, "manutenção" é promessa; com
histórico, é produto.

> A detecção por telemetria agregada de rejeição — o sinal mais rápido que
> existe — depende de base instalada e por isso vem depois, não antes.

---

## Fase D — Primeira receita

**Objetivo:** descobrir se alguém paga, com dinheiro e não com opinião.

A pesquisa apontou dois caminhos viáveis para uma pessoa em tempo parcial, e um
que não é:

- [ ] **Consultoria de adequação ao IBS/CBS**, usando a ferramenta como
      instrumento. Receita imediata, sem infra e sem compromisso de prazo
- [ ] **Assinatura anual estilo clube**, no formato do ACBr Pro: biblioteca
      mantida + boletim de nota técnica + canal direto. Faixa de referência:
      R$ 1.500 a R$ 3.000/ano por software house
- [ ] Contrato com fronteira de responsabilidade da [spec 03](docs/spec/03-credenciais-e-certificado.md), revisado por alguém com competência jurídica
- [ ] Enquadramento fiscal e contábil resolvido **antes** de faturar

**Critério de saída:** primeiro cliente pagando.

**Fora deste desenho, por decisão:** cobrança por documento emitido (comoditizada
em R$ 0,05–0,15/nota) e SLA de disponibilidade (invendável sem plantão e sem
balanço, e a cláusula limitativa não afasta responsabilidade civil por falha
técnica).

**Teto de preço:** R$ 799/mês. Acima disso o comprador vai ao Focus NFe Growth
(R$ 548/mês, *com* emissão) ou ao PlugNotas.

---

## Suspenso — Emissão

Não é "depois". É **suspenso, com gatilho escrito**.

O [ADR-0011](docs/adr/0011-validacao-e-o-produto.md) suspende o
[ADR-0003](docs/adr/0003-integracao-direta-com-sefaz.md) e lista quatro gatilhos
que trazem a emissão de volta — o mais importante sendo alguém pagar adiantado
por ela, com valor nomeado.

Enquanto o gatilho não disparar: nenhuma linha de assinatura, transmissão,
certificado ou webservice. Nem spike.

---

## Fora de escopo

CT-e, MDF-e, custódia de certificado ([ADR-0005](docs/adr/0005-certificado-nunca-transita.md)),
geração de SPED, adapters municipais de NFS-e (a NFS-e Nacional está
comoditizando esse fosso), interface gráfica, e qualquer integração não fiscal
([ADR-0001](docs/adr/0001-escopo-vertical-fiscal.md)).

---

## Nota sobre prazos

Sem datas. Projeto de tempo parcial paralelo a emprego integral; estimativa aqui
seria ficção. As fases têm ordem e critério de saída — a velocidade é o que for.

A única data que importa no repositório é o campo `reavaliar_em` das regras, e
essa não é negociável: é obrigação com quem usa.
