# ADR-0009 — Nome: `fiscal-mcp`

- **Data:** 06/08/2026
- **Status:** aceita

## Contexto

O nome vai para o pacote no PyPI, o repositório, os registries MCP e todos os
documentos. Trocar depois quebra instalação de quem já usa.

Referência de estilo pedida: `cep-promise`, do Filipe Deschamps — **domínio
primeiro, primitiva técnica depois**, descritivo e sem metáfora. Descartadas as
opções com metáfora (Tomada, Balcão), que combinariam com o Cilada tonalmente mas
não com o público comprador — ERP e contabilidade não procuram por metáfora.

Restou decidir entre `fiscal-mcp` (sufixo) e `mcp-fiscal` (prefixo). Ambos livres
no PyPI e no npm em 06/08/2026.

## Decisão

**`fiscal-mcp`.**

## Justificativa

**1. É a convenção dominante, medida.** Entre repositórios MCP com mais de 50
estrelas, o padrão sufixo vence por **16 a 8**. Entre os mais adotados a
tendência é mais forte ainda:

| Repositório | Estrelas | Padrão |
|---|---|---|
| `playwright-mcp` | 35,9k | sufixo |
| `github-mcp-server` | 32,0k | sufixo |
| `pal-mcp-server` | 11,7k | sufixo |
| `firecrawl-mcp-server` | 7,2k | sufixo |
| `whatsapp-mcp` | 6,1k | sufixo |
| `notion-mcp-server` | 4,6k | sufixo |
| `mcp-server-cloudflare` | 4,0k | prefixo |

O prefixo `mcp-server-*` é a convenção **oficial da Anthropic** para os servidores
de referência dela. Terceiros que cresceram usam sufixo — porque quem procura
pesquisa pelo domínio ("notion", "playwright", "fiscal"), não pelo protocolo.

**2. Casa com a referência pedida.** Mesmo padrão de `cep-promise`.

**3. Separa do vizinho.** `mcp-brasil` já existe com 1,7k estrelas
([ADR-0001](0001-escopo-vertical-fiscal.md)). Um `mcp-fiscal` ficaria colado a ele
em qualquer listagem e sugeriria ser irmão ou fork. `fiscal-mcp` deixa claro que
é outra coisa.

## Consequências

- Em português falado continuaremos dizendo "o MCP fiscal", que é o inverso do
  nome do pacote. Não é problema: nome de pacote otimiza descoberta, não fala.
- `fiscal-mcp-server` fica reservado como nome de repositório caso um dia a
  distinção entre pacote e servidor importe.
- Registrar o nome no PyPI cedo, mesmo sem publicar código, evita perder para
  homônimo.

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| `mcp-fiscal` | convenção minoritária; confunde com `mcp-brasil` |
| `sefaz-mcp` | estreito demais: NFS-e é municipal e SPED é Receita, não SEFAZ |
| `Tomada`, `Balcão` | metáfora não é como o comprador procura |
| `mcp-br`, `brasil-mcp` | disputa direta com posição já ocupada |
| `nfe-promise` | derivativo demais da referência |
