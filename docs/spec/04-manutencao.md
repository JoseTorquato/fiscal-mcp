# Spec 04 — Manutenção: o produto de verdade

> Se o cliente não pagar por isto, não paga por nada — porque o resto ele gera
> com IA numa tarde. Este documento descreve a única coisa difícil de copiar.

## A hipótese que precisa ser verdadeira

> *"Eu pago para nunca mais manter essa integração."*

Se for falsa, o negócio não existe e o pivô é outro. Por isso a validação
(ver [ROADMAP](../../ROADMAP.md), fase 0) pergunta exatamente isso, antes de
qualquer código de produção.

## Por que o fiscal brasileiro quebra

| Fonte de quebra | Frequência | Aviso prévio |
|---|---|---|
| Nota técnica da SEFAZ (novo campo, nova regra) | várias por ano | semanas a meses |
| Mudança de leiaute por reforma tributária | em curso desde 2026 | definido em ato |
| Prefeitura mudando padrão de NFS-e | imprevisível | frequentemente nenhum |
| Webservice fora do ar | semanal | nenhum |
| Certificado do cliente vencendo | anual | previsível, mas ignorado |

O IBS/CBS é o caso vivo: campos obrigatórios desde 03/08/2026. Quem tinha
integração pronta teve que mexer.

## Detecção — as três camadas

### 1. Monitor de fonte oficial

Vigia os portais e publicações que anunciam mudança (Portal da NF-e, notas
técnicas, atos do Comitê Gestor do IBS). Quando aparece documento novo,
abre tarefa. **É deliberadamente um alerta para humano, não automação** — nota
técnica precisa ser lida e interpretada, e errar isso é pior que não ter.

### 2. Suíte contra homologação, diária

O sinal mais confiável de que algo mudou é a homologação começar a rejeitar o
que aceitava ontem. Roda todo dia contra os ambientes de homologação:

- emissão de nota completa por UF suportada;
- consulta, cancelamento e CC-e;
- comparação com o resultado esperado.

Falha nova = ou a SEFAZ mudou, ou quebramos. As duas exigem ação hoje.

### 3. Telemetria de quem usa

Erro que aparece em vários clientes ao mesmo tempo é mudança externa, não bug de
um. Padrão de rejeição agregado é o detector mais rápido que existe — e só quem
opera muitos clientes tem esse sinal. **É vantagem que cresce com a base.**

## Compromisso público

O que a camada paga promete, e que precisa ser realista antes de virar contrato:

| Evento | Compromisso |
|---|---|
| Nota técnica publicada | análise e plano em até 5 dias úteis |
| Mudança obrigatória com prazo | suporte disponível **antes** do prazo legal |
| Webservice fora do ar | detecção em até 15 min, status público |
| Quebra que impede emissão | correção priorizada acima de tudo |

Números a calibrar com dados reais antes de virar SLA assinado. Prometer
resposta que não se cumpre é pior que não prometer.

## Compatibilidade

Leiaute fiscal muda por imposição externa — não dá para "não atualizar". Então:

- **versão do documento fiscal é explícita** na ferramenta, nunca implícita;
- quando um leiaute novo entra, o anterior continua suportado enquanto a SEFAZ
  aceitar, e o servidor **avisa** que está usando o antigo;
- mudança que quebra compatibilidade sobe a major e vem com guia de migração.

## Registro de mudanças

Cada mudança fiscal absorvida vira uma entrada com: o que mudou, qual documento
oficial determinou, o que precisou mudar no código, e a partir de quando é
obrigatório.

Esse registro é ativo comercial: é a prova de que a manutenção acontece. Quem
compra manutenção quer ver histórico, não promessa.
