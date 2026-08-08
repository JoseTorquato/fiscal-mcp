# ADR-0008 — Validar a hipótese de manutenção antes de escrever código de produção

- **Data:** 06/08/2026
- **Status:** aceita

## Contexto

Todo o modelo depende de uma única hipótese ([spec 04](../spec/04-manutencao.md)):

> *"Eu pago para nunca mais manter essa integração."*

Se ela for falsa, nada salva o projeto — nem cobertura, nem preço, nem canal. E
integração fiscal direta é cara de construir: certificado, assinatura, SOAP,
homologação instável. É o tipo de esforço que consome meses antes de produzir
qualquer sinal de mercado.

Há um risco de processo aqui, e ele é pessoal: construir é mais divertido que
conversar com cliente. Um projeto de tempo parcial pode facilmente virar seis
meses de código sem nenhuma validação.

## Decisão

**Nenhum código de integração com SEFAZ antes de 6 de 10 conversas confirmarem a
disposição a pagar** — com valor nomeado pelo interlocutor, não sugerido por nós.

A fase 0 do [ROADMAP](../../ROADMAP.md) é conversa, não código. O que se pode
construir antes disso: apenas o suficiente para tornar a conversa concreta —
protótipo de leitura sem efeito fiscal, ou o desenho da superfície de ferramentas.

## Justificativa

**O custo do erro é assimétrico.** Validar custa dez conversas. Construir errado
custa meses de noite e fim de semana.

**A pergunta certa é sobre manutenção, não sobre a ferramenta.** "Você usaria um
MCP de NF-e?" quase sempre recebe sim educado. "Quanto você gastou no último ano
mantendo integração fiscal?" recebe número — e número é sinal.

**Existe plano B com esforço marginal quase zero.** Se a disposição a pagar não
existir, o pivô é publicar os servidores abertos como contribuição ao
ecossistema, capturar autoridade e seguir para a próxima frente — perdendo dias,
não meses.

## Roteiro mínimo da conversa

1. Como vocês emitem nota hoje?
2. Quanto tempo alguém do time gastou com fiscal nos últimos 12 meses?
3. O que aconteceu quando saiu a mudança de IBS/CBS deste ano?
4. Se existisse uma camada mantida por outra pessoa, com compromisso de prazo
   para nota técnica, isso valeria quanto por mês?
5. Quem assinaria essa decisão aí dentro?

A pergunta 5 é a que separa interesse de compra.

## Consequências

- Atrasa o início do código, o que é desconfortável e é o ponto.
- Exige prospecção ativa, que é a parte menos agradável — e por isso precisa
  estar escrita como decisão, não como intenção.
- As conversas geram, de brinde, a lista de UFs e municípios prioritários.

## Critério de falseamento

Se após 10 conversas **menos de 6** confirmarem disposição a pagar com valor
nomeado, a hipótese está falseada. Não se prossegue para a fase 2 "para ver se
melhora depois de pronto".
