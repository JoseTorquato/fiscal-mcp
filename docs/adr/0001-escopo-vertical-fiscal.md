# ADR-0001 — Verticalizar no fiscal em vez de catálogo amplo

- **Data:** 06/08/2026
- **Status:** aceita

## Contexto

A ideia original era um catálogo amplo de servidores MCP para APIs brasileiras:
Bling, Omie, Conta Azul, Asaas, Tiny, RD Station, NF-e, Correios. Mais mercado
endereçável e integrações mais simples de escrever.

O risco identificado desde o início: **um dev competente gera um servidor MCP
para a API do Bling numa tarde usando IA.** Se o mercado enxergar o produto como
"código de integração", ninguém assina.

## Decisão

Verticalizar no fiscal — NF-e, NFS-e e SPED — abandonando o catálogo amplo.

## Justificativa

**1. A dificuldade é o fosso.** APIs REST modernas e documentadas são geráveis. O
fiscal não: exige certificado ICP-Brasil, SOAP com assinatura XML, ambientes de
homologação instáveis, leiaute que muda por nota técnica e, na NFS-e, milhares de
padrões municipais. IA gera o esqueleto; não gera a operação.

**2. Existe prazo legal.** Desde 03/08/2026 os campos de IBS e CBS são
obrigatórios nos documentos fiscais do regime regular. Isso é forcing function —
o cliente não compra quando acha bonito, compra quando tem prazo.

**3. O espaço amplo já tem dono; o vertical difícil não.** Pesquisa de
06/08/2026: o `Mcp-Brasil/mcp-brasil` tem **1.713 estrelas e 533 ferramentas**
sobre 70 APIs públicas brasileiras. Tentar ser "o MCP do Brasil" seria disputar
posição ocupada por um projeto maduro e com vantagem de tempo — briga perdida.

Mas ele cobre **leitura de dado público**, e não toca em emissão fiscal: a única
menção a NF-e é ler um campo de nota em API de compras públicas. Nas tentativas
de fiscal de verdade, o melhor projeto tem 1 estrela — um envelopa API paga de
terceiro, outro tem SEFAZ "planejado". **Ninguém entregou integração real e
ninguém encosta em NFS-e municipal.**

A fronteira é estrutural, não de esforço: dado público é `GET` sem credencial;
emitir nota é escrita com efeito jurídico, certificado ICP-Brasil e nota técnica.
Um faz o agente **saber**, o outro faz o agente **fazer**.

**4. Disposição a pagar comprovada.** O mercado de emissores e integradores
fiscais já existe e já cobra. Não é preciso criar categoria.

**5. Vertical estreito com dado próprio cria moat.** Telemetria agregada de
rejeição entre clientes é sinal que só quem opera muitos possui — e melhora com
escala.

## Consequências

**Positivas:** barreira de entrada real; comprador com verba e urgência;
posicionamento claro.

**Negativas:** mercado endereçável menor; ciclo de desenvolvimento mais longo
(certificado e homologação não se resolvem numa tarde); exige aprender domínio
fiscal de verdade; responsabilidade maior — errar integração fiscal tem
consequência para o cliente.

**Aceitas conscientemente:** o custo de aprendizado é justamente o que mantém
concorrente fora.

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Catálogo amplo | commodity gerável com IA; sem forcing function |
| Só pagamento/cobrança (Asaas, Pix) | valida mais rápido, mas APIs REST documentadas = fosso menor |
| Registry curado de MCPs brasileiros | vira diretório; não resolve dor de ninguém |
| Ser "o MCP Brasil" guarda-chuva | posição já ocupada pelo `Mcp-Brasil/mcp-brasil` (1.7k ⭐). Melhor ser complementar e ser listado por ele do que disputar de frente |

## Revisão

Reavaliar se: (a) a validação mostrar que ERPs não pagam por manutenção;
(b) alguém entregar cobertura fiscal completa e madura antes; (c) o padrão
nacional de NFS-e eliminar a complexidade municipal — o que reduziria o fosso e
tornaria o catálogo amplo relativamente mais atraente.
