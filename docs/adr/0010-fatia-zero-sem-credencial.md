# ADR-0010 — Fatia zero: construir o que não exige credencial nem tem efeito fiscal

- **Data:** 08/08/2026
- **Status:** aceita
- **Refina:** [ADR-0008](0008-validar-antes-de-construir.md)

## Contexto

O [ADR-0008](0008-validar-antes-de-construir.md) proibiu código de produção antes
de validar a disposição a pagar. A intenção era certa — evitar meses gastos em
integração cara antes de qualquer sinal de mercado.

Mas ele tratou "código" como bloco único, e isso produziu um efeito perverso: a
única coisa a mostrar seria especificação. Especificação atrai curiosidade, não
conversa. Quem tem a dor não marca reunião com quem tem um plano; marca com quem
demonstrou que resolve.

Pior: **as dez conversas da fase 0 ficam muito mais difíceis sem nada nas mãos.**
"Você pagaria por isso?" recebe sim educado. "Rodei isto no seu XML e achei três
problemas" recebe conversa de verdade.

## Decisão

Dividir o que antes era um bloco só:

| Tipo | Exige credencial? | Efeito fiscal? | Custo | Gate |
|---|---|---|---|---|
| **Fatia zero** | não | nenhum | dias | **liberada agora** |
| Integração SEFAZ | certificado A1/A3 | sim, jurídico | meses | **continua atrás do gate do ADR-0008** |

A fatia zero é tudo que roda **offline, sem certificado e sem transmitir nada**:

- `validar_nfe` — valida XML contra schema e regras conhecidas, **incluindo o
  grupo de IBS e CBS**, e devolve pendências acionáveis;
- `explicar_nfe` — interpreta um XML e devolve estrutura resumida que cabe em
  contexto de agente, em vez de despejar o XML inteiro;
- `explicar_rejeicao` — código de rejeição da SEFAZ → o que significa → o que
  fazer, com o campo `acao` do [spec 02](../spec/02-contrato-de-ferramentas.md);
- `validar_chave_acesso` — composição e dígito verificador.

Nenhuma delas emite, cancela, assina ou fala com a SEFAZ. **Não há como causar
dano fiscal com essa superfície.**

## Justificativa

**1. Resolve uma dor que existe hoje e tem prazo.** Desde 03/08/2026 os campos de
IBS e CBS são obrigatórios e notas sem eles podem ser rejeitadas. Todo emissor do
país está conferindo XML agora. *"Seu XML está pronto para o IBS/CBS?"* é a
pergunta do momento — e responder a ela não exige certificado nenhum.

**2. É o instrumento de validação, não uma fuga dele.** Quem instala um validador
de XML fiscal **é exatamente o perfil** das dez conversas da fase 0. A ferramenta
qualifica o interlocutor antes da conversa começar.

**3. Custo compatível com o risco.** Dias, não meses. Se a hipótese de
manutenção for falsa, o que se perde é pequeno — e o validador ainda serve como
contribuição aberta ao ecossistema, que era o plano B do ADR-0008.

**4. Prova competência sem prometer.** Validador que funciona demonstra domínio do
leiaute. Isso é o que faz alguém acreditar que você aguenta a integração inteira.

**5. Reduz o risco técnico do que vem depois.** Entender o schema a fundo é
pré-requisito da emissão. A fatia zero não é desvio do caminho: é o primeiro
trecho dele.

## O que continua proibido antes do gate

- assinatura com certificado;
- qualquer transmissão para SEFAZ ou prefeitura, mesmo em homologação;
- `emitir_nfe`, `cancelar_nfe`, `corrigir_nfe`, `inutilizar_numeracao`;
- qualquer promessa de manutenção com prazo.

O gate do ADR-0008 permanece **idêntico**: 6 de 10 conversas com valor nomeado.

## Consequências

- O roadmap ganha uma fase entre a 0 e a 1. A validação passa a acontecer **com**
  a fatia zero na mão, não antes dela.
- Cria expectativa: quem instalar o validador vai perguntar quando sai a emissão.
  A resposta honesta — "quando eu souber que alguém paga pela manutenção" — é
  aceitável e, de quebra, é a própria pergunta da validação.
- Risco real: a fatia zero é agradável de construir e pode virar desculpa para
  adiar as conversas. **Mitigação: a fase 0 e a fatia zero correm em paralelo, e
  a fase 0 não pode terminar depois.**

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Manter o ADR-0008 como estava | landing sem produto não gera conversa; o gate vira paralisia |
| Construir a emissão logo | é exatamente o risco que o ADR-0008 existe para evitar |
| Mock de emissão que finge funcionar | desonesto, e destrói a credibilidade que é o ativo principal |
| Só um validador web, sem MCP | perde o canal de descoberta (registries) e não demonstra a tese |
