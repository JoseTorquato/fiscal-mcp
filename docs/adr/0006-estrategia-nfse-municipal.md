# ADR-0006 — NFS-e: padrão nacional primeiro, municípios por demanda

- **Data:** 06/08/2026
- **Status:** aceita

## Contexto

A NFS-e é competência municipal. São milhares de municípios e, historicamente,
cada um define seu padrão — schema, autenticação, ambiente de homologação. Existe
um padrão nacional em implantação, com adesão crescente porém parcial.

É simultaneamente a maior dor do escopo e o maior sumidouro de esforço: tentar
cobrir tudo é garantia de nunca entregar nada.

## Decisão

Ordem de ataque:

1. **Padrão nacional de NFS-e** — cobre o maior número de municípios com um
   adapter só, e a tendência é crescer.
2. **Municípios de maior volume econômico**, por demanda real de quem chegar.
3. **Padrões municipais comuns** (famílias derivadas do modelo ABRASF), que
   cobrem vários municípios com um adapter parametrizado.
4. **Município específico**, apenas quando houver cliente pagando — nunca por
   completude.

A ferramenta `consultar_capacidade_municipio` declara honestamente o que é
suportado, em vez de falhar no meio da operação.

## Justificativa

**Cobertura total é armadilha.** Um desenvolvedor solo perseguindo milhares de
prefeituras nunca lança. Cobertura honesta e crescente é melhor que promessa
quebrada.

**Declarar incapacidade é feature.** Para um agente, "este município não é
suportado, use o caminho X" é infinitamente melhor que erro obscuro no meio de
uma emissão.

**A demanda ordena melhor que a intuição.** Quais municípios importam é resposta
que o mercado dá, não que se adivinha.

**A cobertura ampla é exatamente o que se vende** ([ADR-0002](0002-open-core.md)):
manter dezenas de adapters municipais é trabalho contínuo e chato — o tipo de
coisa que ninguém quer fazer e todo mundo precisa.

## Consequências

- O produto nasce com cobertura parcial declarada. Precisa estar no README, sem
  eufemismo.
- Exige mecanismo de "pedir um município" que vira sinal de priorização — e
  também de qualificação comercial.
- Se o padrão nacional atingir adesão universal, este ADR perde razão de ser e o
  fosso da NFS-e diminui. Isso está registrado como gatilho de revisão em
  [ADR-0001](0001-escopo-vertical-fiscal.md).

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Cobrir os N maiores municípios antes de lançar | atrasa demais; prioriza por palpite |
| Só padrão nacional, ignorar o resto | deixa de fora quem mais sofre hoje |
| Envelopar intermediário só para NFS-e | contradiz [ADR-0003](0003-integracao-direta-com-sefaz.md); avaliável como contingência |
