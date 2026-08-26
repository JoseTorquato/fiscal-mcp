# Decisões de arquitetura (ADRs)

Cada ADR registra uma decisão com o contexto em que foi tomada, a justificativa,
as consequências aceitas e — quando existe — o gatilho que obriga a revisá-la.

O objetivo não é burocracia: é impedir que uma decisão pensada seja revertida por
esquecimento seis meses depois, e deixar claro **o que precisaria mudar no mundo**
para cada uma deixar de valer.

| # | Decisão | Status |
|---|---|---|
| [0001](0001-escopo-vertical-fiscal.md) | Verticalizar no fiscal em vez de catálogo amplo | aceita |
| [0002](0002-open-core.md) | Open core: servidor aberto, manutenção e operação pagas | aceita |
| [0003](0003-integracao-direta-com-sefaz.md) | Integrar direto com SEFAZ, não via intermediário | **suspensa por 0011** |
| [0004](0004-python-e-sdk-oficial-mcp.md) | Python com o SDK oficial de MCP | aceita |
| [0005](0005-certificado-nunca-transita.md) | Não custodiar certificado digital de cliente | aceita |
| [0006](0006-estrategia-nfse-municipal.md) | NFS-e: padrão nacional primeiro, municípios por demanda | aceita |
| [0007](0007-homologacao-por-padrao.md) | Homologação por padrão; produção exige opt-in explícito | aceita |
| [0008](0008-validar-antes-de-construir.md) | Validar a hipótese antes de escrever código de produção | aceita |
| [0009](0009-nome-do-projeto.md) | Nome: `fiscal-mcp` | aceita |
| [0010](0010-fatia-zero-sem-credencial.md) | Fatia zero: construir o que não exige credencial nem tem efeito fiscal | aceita · refina 0008 |
| [0011](0011-validacao-e-o-produto.md) | Validação é o produto; emissão sai do caminho crítico | aceita · refina 0008 · suspende 0003 |

## As quatro que mais doem se forem ignoradas

- **[0008](0008-validar-antes-de-construir.md)** — o gate contra gastar meses
  codando sem sinal de mercado. É a mais fácil de furar, porque codar é mais
  divertido que prospectar.
- **[0005](0005-certificado-nunca-transita.md)** — custodiar certificado alheio
  sem estrutura é assumir risco desproporcional. A tentação vem disfarçada de
  "só esse cliente, para fechar o contrato".
- **[0007](0007-homologacao-por-padrao.md)** — quem opera o servidor é um agente
  de IA, e erro aqui é documento fiscal indevido, não linha errada no banco.
- **[0011](0011-validacao-e-o-produto.md)** — mantém a emissão fora do caminho
  crítico. É a que vai ser furada primeiro, porque emitir uma nota é mais
  emocionante que escrever a décima quarta regra de validação.

## Como escrever um ADR novo

Copie a estrutura de qualquer um: contexto, decisão, justificativa,
consequências (inclusive as negativas aceitas), alternativas descartadas com o
motivo, e gatilho de revisão. Numere em sequência. **ADR não se edita depois de
aceito** — se a decisão mudar, escreva um novo que supera o anterior e marque o
antigo como substituído.
