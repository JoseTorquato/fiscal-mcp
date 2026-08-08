# Roadmap

Cada fase tem **critério de saída**. Não se avança sem cumprir — especialmente
da fase 0 para a 1, que é onde a vontade de codar costuma atropelar a validação
([ADR-0008](docs/adr/0008-validar-antes-de-construir.md)).

O contexto de mercado é favorável e tem prazo: a obrigatoriedade dos campos de
IBS e CBS começou em **03/08/2026**, e 2026 é ano de transição assistida. A
janela de atenção do mercado é agora.

---

## Fase 0 — Validar a hipótese · *nenhum código de produção*

**Objetivo:** descobrir se existe disposição a pagar por manutenção.

- [ ] Listar 20 alvos: ERPs pequenos e médios, contabilidades digitais, software
      houses com projeto fiscal
- [ ] 10 conversas usando o roteiro do [ADR-0008](docs/adr/0008-validar-antes-de-construir.md)
- [ ] Registrar, por conversa: gasto anual com fiscal, o que doeu no IBS/CBS,
      valor nomeado, quem assina
- [ ] Consolidar UFs e municípios citados — vira ordem de prioridade

**Critério de saída:** 6 de 10 confirmam disposição a pagar **com valor nomeado
pelo interlocutor**.

**Se falhar:** publicar o que houver como contribuição aberta, capturar
autoridade, e voltar para as outras frentes. Perda: dias.

---

## Fase 0.5 — Fatia zero · *roda em paralelo com a fase 0*

**Objetivo:** ter algo que funciona hoje, sem certificado e sem efeito fiscal —
tanto para valer por si só quanto para tornar as dez conversas concretas
([ADR-0010](docs/adr/0010-fatia-zero-sem-credencial.md)).

- [ ] `validar_nfe` — schema e regras, **incluindo o grupo IBS/CBS**
- [ ] `explicar_nfe` — XML em estrutura resumida, que cabe em contexto de agente
- [ ] `explicar_rejeicao` — código → significado → ação
- [ ] `validar_chave_acesso`
- [ ] Publicar no PyPI e nos registries
- [ ] Landing com a pergunta da validação, não com promessa de produto

**Critério de saída:** alguém de fora valida um XML real e relata o resultado.

**Regra:** esta fase **não pode terminar depois da fase 0**. Se as conversas
pararem porque construir é mais agradável, o gate do
[ADR-0008](docs/adr/0008-validar-antes-de-construir.md) foi furado na prática,
ainda que não no papel.

---

## Fase 1 — Provar que a parte difícil é possível · *spike técnico*

**Objetivo:** eliminar o risco técnico antes de prometer qualquer coisa. Não é
produto — é resposta à pergunta "isso é viável para uma pessoa?".

- [ ] Assinar XML de NF-e com certificado A1 e validar a assinatura
- [ ] Emitir uma NF-e modelo 55 em **homologação** de uma UF, ponta a ponta
- [ ] Incluir os campos do grupo de IBS/CBS conforme leiaute vigente
- [ ] Consultar e cancelar a nota emitida
- [ ] Medir: quanto tempo levou, e o que foi mais difícil

**Critério de saída:** nota autorizada em homologação, com o passo a passo
documentado.

**Se falhar:** reavaliar o [ADR-0003](docs/adr/0003-integracao-direta-com-sefaz.md)
— talvez o adapter de intermediário precise ser o caminho principal.

---

## Fase 2 — Primeiro servidor útil · *NF-e, aberto*

**Objetivo:** alguém que não seja o autor consegue emitir em homologação.

- [ ] Superfície de ferramentas conforme [spec 02](docs/spec/02-contrato-de-ferramentas.md)
- [ ] Validação local antes de transmitir
- [ ] Tradução dos códigos de rejeição mais comuns, com campo `acao`
- [ ] Guarda de ambiente conforme [ADR-0007](docs/adr/0007-homologacao-por-padrao.md)
- [ ] Publicar no PyPI e nos registries MCP
- [ ] README com o caminho de 15 minutos

**Critério de saída:** três pessoas de fora emitem em homologação seguindo só o
README, sem perguntar nada.

---

## Fase 3 — Provar a manutenção · *o produto de verdade*

**Objetivo:** transformar a promessa em evidência observável.

- [ ] Suíte diária contra homologação, com resultado público
- [ ] Monitor de publicação de nota técnica
- [ ] Registro público de mudanças fiscais absorvidas
- [ ] Página de status dos webservices por UF

**Critério de saída:** uma mudança real de leiaute absorvida e registrada, com
data de detecção e data de suporte.

> Esta fase é a que justifica a assinatura. Sem histórico, "manutenção" é
> promessa; com histórico, é produto.

---

## Fase 4 — Primeira receita

- [ ] Definir a fronteira paga em detalhe operacional ([ADR-0002](docs/adr/0002-open-core.md))
- [ ] Serviço que entrega cobertura mantida sem embarcar no pacote aberto
- [ ] Compromissos de prazo calibrados com dados reais da fase 3
- [ ] Contrato com a fronteira de responsabilidade da [spec 03](docs/spec/03-credenciais-e-certificado.md)
- [ ] Enquadramento fiscal e contábil resolvido **antes** de faturar

**Critério de saída:** primeiro cliente pagando.

---

## Fase 5 — NFS-e e ampliação

- [ ] Padrão nacional de NFS-e
- [ ] Adapters municipais por demanda ([ADR-0006](docs/adr/0006-estrategia-nfse-municipal.md))
- [ ] SPED em leitura
- [ ] Telemetria agregada de rejeição

---

## Fora de escopo por enquanto

CT-e, MDF-e, custódia de certificado ([ADR-0005](docs/adr/0005-certificado-nunca-transita.md)),
emissão de SPED, interface gráfica, e qualquer integração não fiscal
([ADR-0001](docs/adr/0001-escopo-vertical-fiscal.md)).

## Nota sobre prazos

Este roadmap **não tem datas**. É projeto de tempo parcial paralelo a um emprego
integral; estimativa aqui seria ficção. As fases têm ordem e critério de saída —
a velocidade é o que for.
