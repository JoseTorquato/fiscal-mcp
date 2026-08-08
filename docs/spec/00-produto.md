# Spec 00 — Produto

## Em uma frase

Servidores MCP mantidos que expõem o fiscal brasileiro como ferramentas de
agente, para que um dev não precise aprender SEFAZ para emitir uma nota.

## Quem sofre a dor, em ordem de intensidade

| Quem | Dor | Disposição a pagar |
|---|---|---|
| **ERP pequeno e médio** | tem 1–2 pessoas cuidando de fiscal e elas viram gargalo a cada nota técnica | alta — é custo de sobrevivência |
| **Contabilidade digital** | precisa ler SPED e conferir nota de centenas de clientes | alta |
| **Software house** | pegou projeto com "só emitir nota" no escopo e descobriu o buraco | alta e urgente |
| **Time interno de e-commerce** | quer automatizar conferência fiscal | média |
| **Dev construindo agente** | quer dar ferramenta fiscal ao agente | média, mas é o canal de descoberta |

O comprador econômico não é o dev — é quem paga o dev. Mas **a descoberta passa
pelo dev**, e é por isso que a camada aberta existe.

## O gatilho de 2026

Diferente de um produto de "boa prática", este tem prazo legal. Desde 03/08/2026,
documentos fiscais do regime regular precisam trazer os campos de IBS e CBS, e
notas sem eles podem ser rejeitadas. Durante 2026 vale alíquota-teste (0,1% IBS +
0,9% CBS) sem recolhimento — é transição assistida, mas o leiaute **já mudou**.

Consequência prática: todo emissor do país tem trabalho de adaptação agora. Quem
oferecer a camada pronta pega a onda; quem chegar em 2028 chega depois da briga.

**Isto é o forcing function.** É a diferença entre vitamina e analgésico.

## O que o produto entrega

### Camada aberta (MIT)

Servidores MCP instaláveis, rodando na infra de quem usa:

- ferramentas nomeadas por intenção de negócio, não por endpoint de webservice;
- validação local antes de bater na SEFAZ (rejeição custa tempo);
- erros traduzidos: código de rejeição da SEFAZ vira mensagem acionável;
- ambiente de homologação como padrão — produção exige opt-in explícito.

### Camada de serviço (paga)

O que a camada aberta **não** resolve sozinha:

- **manutenção contra nota técnica** — o servidor continua funcionando depois que
  a SEFAZ muda o leiaute, porque alguém acompanha e atualiza;
- **cobertura municipal de NFS-e** — adapters mantidos, que é trabalho contínuo e
  chato por definição;
- **gestão de certificado** com controles adequados, para quem não quer resolver
  isso sozinho;
- **observabilidade e SLA** — saber que a SEFAZ do estado caiu antes do cliente
  ligar.

A fronteira exata está no [ADR-0002](../adr/0002-open-core.md).

## Como se mede sucesso

**Fase de validação (antes de escrever código de produção):**
- 10 conversas com dev de ERP ou software house;
- pergunta única: *"você pagaria para nunca mais manter essa integração?"*;
- critério: **6 de 10 dizem sim e sabem dizer quanto**.

**Fase de produto:**
- tempo do `pip install` até uma nota emitida em homologação — meta: **< 15 min**;
- número de notas técnicas absorvidas sem quebrar quem já usa;
- taxa de rejeição evitada pela validação local.

## O que este produto não é

- **Não é um emissor.** Não temos interface, não guardamos a nota, não somos
  responsáveis pela obrigação fiscal do cliente.
- **Não é consultoria tributária.** Não dizemos qual CFOP usar. Erro de
  classificação fiscal é do contador; erro de integração é nosso.
- **Não é um catálogo genérico de APIs brasileiras.** Ver
  [ADR-0001](../adr/0001-escopo-vertical-fiscal.md).

Essa fronteira é de responsabilidade civil, não de posicionamento. Registrada
também em [spec 03](03-credenciais-e-certificado.md).
