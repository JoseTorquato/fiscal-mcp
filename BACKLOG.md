# Backlog

Tarefas agrupadas por fase do [ROADMAP](ROADMAP.md). Cada uma tem **critério de
pronto** — sem isso, tarefa de projeto pessoal nunca termina, só é abandonada.

Tamanhos: **P** cabe em uma sessão de ~1h · **M** algumas sessões · **G** exige
um fim de semana ou é incerta demais para estimar.

---

## Fase 0 — Validação · *nenhum código de produção*

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| V1 | Montar lista de 20 alvos (ERP, contabilidade digital, software house) com nome, contato e origem | P | planilha com 20 linhas preenchidas |
| V2 | Escrever a mensagem de abordagem — curta, sem pitch, pedindo 15 min | P | texto pronto e enviado para os 5 primeiros |
| V3 | Rodar 10 conversas com o roteiro do ADR-0008 | G | 10 registros preenchidos |
| V4 | Consolidar: gasto anual, dor do IBS/CBS, valor nomeado, quem assina | P | tabela comparativa + veredito da hipótese |
| V5 | Derivar ordem de prioridade de UFs e municípios das conversas | P | lista ordenada com justificativa |

> **Gate.** V4 decide se existe fase 1. Ver critério de falseamento no ADR-0008.

---

## Fase 1 — Spike técnico

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| T1 | Obter certificado A1 de teste e entender o formato | P | certificado carregado e dados lidos |
| T2 | Assinar XML de NF-e e validar a assinatura localmente | M | assinatura válida por validador independente |
| T3 | Levantar o webservice de homologação da UF escolhida | P | endpoint respondendo a consulta de status |
| T4 | Montar XML mínimo de NF-e modelo 55 válido no schema | M | XSD valida sem erro |
| T5 | Incluir o grupo de IBS/CBS conforme leiaute vigente | M | campos presentes e aceitos |
| T6 | Transmitir e obter autorização em homologação | G | protocolo de autorização recebido |
| T7 | Consultar e cancelar a nota emitida | M | evento de cancelamento autorizado |
| T8 | Documentar o passo a passo e o que foi mais difícil | P | documento que outra pessoa consegue seguir |

> T6 é o marco que decide a viabilidade do ADR-0003. Se travar por mais de duas
> semanas de trabalho efetivo, reabrir a decisão de usar intermediário.

---

## Fase 2 — Primeiro servidor útil

### Núcleo

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| S1 | Estrutura do pacote e servidor MCP mínimo respondendo | P | agente lista as ferramentas |
| S2 | Separar as camadas do spec 01 (ferramenta / validação / adapter / transporte) | M | trocar de UF não toca em ferramenta |
| S3 | `consultar_status_servico` | P | responde para as UFs suportadas |
| S4 | `validar_nfe` — validação local, sem rede | M | aponta pendências com mensagem acionável |
| S5 | `emitir_nfe` com guarda de ambiente do ADR-0007 | G | emite em homologação; recusa produção sem a variável |
| S6 | `consultar_nfe` | M | devolve resumo estruturado, XML sob pedido |
| S7 | `cancelar_nfe` com confirmação explícita | M | recusa sem `confirmo_cancelamento` |
| S8 | `corrigir_nfe` (CC-e) | M | evento autorizado em homologação |
| S9 | Chave de idempotência na emissão | M | duas chamadas iguais não emitem duas notas |

### Qualidade de erro

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| E1 | Catálogo dos códigos de rejeição mais comuns | M | tabela código → significado → ação |
| E2 | Tradução de erro com campo `acao` | M | erro devolvido é acionável por agente |
| E3 | Distinguir "SEFAZ fora do ar" de "seu documento está errado" | M | dois caminhos de erro distintos |

### Distribuição

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| D1 | README com o caminho de 15 minutos | M | três pessoas de fora conseguem sem perguntar |
| D2 | Publicar no PyPI | P | `pip install fiscal-mcp` funciona |
| D3 | Registrar nos registries MCP | P | aparece na busca |
| D4 | Exemplo de configuração para cliente MCP popular | P | copiar, colar, funcionar |
| D5 | Falar com o mantenedor do `Mcp-Brasil/mcp-brasil` propondo complementaridade e listagem mútua | P | conversa feita; resposta registrada |

---

## Fase 3 — Provar a manutenção

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| M1 | Suíte de emissão contra homologação, rodando diariamente | M | resultado publicado, histórico visível |
| M2 | Alerta quando a suíte muda de comportamento | P | notificação chega ao autor |
| M3 | Monitor de publicação de nota técnica | M | abre tarefa quando sai documento novo |
| M4 | Registro público de mudanças fiscais absorvidas | P | primeira entrada publicada |
| M5 | Página de status dos webservices por UF | M | status atualizado automaticamente |

---

## Fase 4 — Receita

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| R1 | Detalhar a fronteira paga em nível operacional | M | documento sem ambiguidade sobre o que é pago |
| R2 | Serviço que entrega cobertura sem embarcar no pacote | G | pacote aberto consulta; nada sensível distribuído |
| R3 | Calibrar compromissos de prazo com dados da fase 3 | P | números que se sustentam |
| R4 | Contrato com fronteira de responsabilidade da spec 03 | M | revisado por alguém com competência jurídica |
| R5 | Enquadramento fiscal e contábil da operação | M | resolvido antes de faturar |

---

## Fase 5 — Ampliação

| # | Tarefa | Tam. |
|---|---|---|
| N1 | `consultar_capacidade_municipio` | M |
| N2 | Adapter do padrão nacional de NFS-e | G |
| N3 | Adapters municipais por demanda | G |
| N4 | `ler_sped` e `resumir_sped` | G |
| N5 | Telemetria agregada de rejeição | M |

---

## Dívidas e riscos conhecidos

| Item | Risco | Mitigação |
|---|---|---|
| Homologação da SEFAZ instável | trava desenvolvimento sem ser culpa nossa | separar erro de ambiente de erro de documento (E3) desde cedo |
| Certificado A1 de teste | precisa de um, e tem custo/burocracia | resolver em T1, antes de qualquer outra coisa técnica |
| Leiaute mudando durante a construção | retrabalho no meio da fase 2 | acompanhar nota técnica desde já, mesmo sem produto |
| Autor com emprego integral | ritmo imprevisível | tarefas P e M; nada de G fora de fim de semana |
| Vontade de codar antes de validar | meses gastos sem sinal de mercado | gate explícito no ADR-0008 |
| Concorrente entregando primeiro | perda da janela do IBS/CBS | é risco real e aceito; a defesa é profundidade, não velocidade |
