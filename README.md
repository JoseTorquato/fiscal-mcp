<!-- mcp-name: io.github.josetorquato/fiscal-mcp -->

<img src="https://raw.githubusercontent.com/JoseTorquato/fiscal-mcp/main/docs/logo.svg" width="72" alt="fiscal-mcp">

# fiscal-mcp

**Documento fiscal brasileiro como ferramenta de agente.** Valide NF-e e NFS-e
antes de transmitir — sem certificado, sem cadastro, sem enviar nada para lugar
nenhum.

[![MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-22C55E)](https://github.com/JoseTorquato/fiscal-mcp/blob/main/LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-22C55E)](https://github.com/JoseTorquato/fiscal-mcp/blob/main/pyproject.toml)
[![189 testes](https://img.shields.io/badge/testes-189-22C55E)](https://github.com/JoseTorquato/fiscal-mcp/blob/main/tests/)

```bash
pip install "fiscal-mcp[xsd]"
fiscal-mcp validar nota.xml
```

```
  [erro] ibs-cclasstrib-prefixo-cst
      cClassTrib não corresponde ao CST do item
      item 2: imposto/IBSCBS/cClassTrib = '000123' não começa por
              imposto/IBSCBS/CST = '200'
      → Os três primeiros dígitos do cClassTrib são o CST do item. Este é o erro
        mais comum ao ligar o módulo de IBS/CBS num ERP.

  [erro] schema-elemento-fora-de-ordem
      cEAN apareceu onde o leiaute espera xProd
      item 1, linha 62 do XML
      → O schema da NF-e exige a sequência exata do leiaute — trocar a ordem
        reprova mesmo com todos os campos presentes.

  2 erro(s), 0 aviso(s)
```

Três camadas, num laudo só: **schema XSD oficial**, **regras fiscais** e **chave
de acesso**. Tudo local — o processo não abre socket, e há teste que prova.

---

## Por que existe

Rejeição da SEFAZ chega tarde, custa uma transmissão e vem com mensagem
críptica. Boa parte dos motivos é aritmética simples ou campo fora de formato —
coisa que dá para pegar **antes** de enviar, na sua própria máquina.

E agora tem prazo: desde **3 de agosto de 2026**, documentos fiscais do regime
regular precisam trazer os campos de IBS e CBS, e notas sem eles podem ser
rejeitadas ([CGIBS](https://www.cgibs.gov.br/novo-marco-da-reforma-tributaria-inicia-em-03-de-agosto-com-preenchimento-obrigatorio-dos-campos-relativos-ao-ibs-e-a-cbs)).

Enquanto isso, um agente de IA consegue mexer no seu Notion e no seu GitHub, mas
não sabe ler uma nota fiscal.

## O que ele faz

| Ferramenta | O que faz |
|---|---|
| `validar_nfe` | schema XSD oficial, regras fiscais (IBS/CBS incluso), totais e chave — com **o que fazer** em cada achado |
| `explicar_nfe` | resumo estruturado do XML, em vez do documento inteiro |
| `validar_nfse` | NFS-e do padrão nacional: estrutura, DPS embutida, prestador, serviço |
| `explicar_nfse` | resumo estruturado da NFS-e |
| `explicar_rejeicao` | código da SEFAZ → significado → ação, e se é reversível |
| `validar_chave_acesso` | decompõe os 44 dígitos da NF-e e confere o dígito verificador |
| `validar_chave_nfse` | decompõe os 50 dígitos da NFS-e nacional |
| `listar_rejeicoes_conhecidas` | o que o catálogo cobre |

**Nenhuma delas assina, transmite, emite ou cancela documento.** Não existe
caminho, nesta versão, para causar efeito fiscal — e um teste verifica isso a
cada mudança.

## Como usar

### Na linha de comando

```bash
fiscal-mcp validar nota.xml          # NF-e ou NFS-e, ele descobre sozinho
fiscal-mcp validar nota.xml --json   # para script e CI
fiscal-mcp validar nota.xml --sem-schema
fiscal-mcp explicar nota.xml         # resumo estruturado
fiscal-mcp chave 4326081234...       # 44 dígitos (NF-e) ou 50 (NFS-e)
fiscal-mcp rejeicao 539              # traduz o código da SEFAZ
fiscal-mcp rejeicao                  # lista o catálogo
fiscal-mcp tabelas                   # qual tabela oficial está embarcada
```

Sai com código 1 quando encontra erro, então serve direto em CI.

### Como servidor MCP

```bash
pip install "fiscal-mcp[servidor,xsd]"
```

Copie e cole no seu cliente. **Claude Code:**

```bash
claude mcp add fiscal -- fiscal-mcp-servidor
```

**Claude Desktop** (`claude_desktop_config.json`), **Cursor**
(`.cursor/mcp.json`), **VS Code** e a maioria dos outros:

```json
{
  "mcpServers": {
    "fiscal": { "command": "fiscal-mcp-servidor" }
  }
}
```

**Sem instalar Python** — útil para quem trabalha com ERP em Delphi ou C#:

```json
{
  "mcpServers": {
    "fiscal": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/josetorquato/fiscal-mcp"]
    }
  }
}
```

Aí é só perguntar ao agente: *"esse XML está pronto para transmitir?"*

## O que ele não faz

Escrito antes das perguntas, porque prometer demais é o jeito mais rápido de
perder a confiança de quem trabalha com fiscal:

- **Não emite, não assina, não transmite.** Sem certificado digital envolvido.
- **Passar aqui não garante autorização.** É validação local: pega o erro
  previsível, não substitui a SEFAZ.
- **A validação por schema exige o extra `[xsd]`.** Sem ele, o laudo diz que
  essa camada não rodou — nunca finge que rodou.
- **NFS-e só no padrão nacional.** Município com padrão próprio não é
  reconhecido ([ADR-0006](https://github.com/JoseTorquato/fiscal-mcp/blob/main/docs/adr/0006-estrategia-nfse-municipal.md)).
- **Não verifica dígito verificador de NFS-e** — o algoritmo não foi
  confirmado, e chutar produziria acusação falsa.
- **Não valida assinatura digital.** Documento não assinado nunca passa no XSD
  oficial; o laudo diz isso como informação, não como erro.
- **Não dá conselho tributário.** CFOP, CST e alíquota são do seu contador.

### Estado da validação, por documento

| | Camadas | Regras | Testado contra |
|---|---|---|---|
| NF-e / NFC-e | schema XSD + regras + chave | 28 | XML sintético **e 17 amostras de formato real** da `nfelib` |
| NFS-e nacional | regras + chave | 10 | ✅ uma nota autorizada de verdade |

⚠️ **A NF-e ainda não passou por uma nota real de contribuinte.** As 17 amostras
são públicas e MIT, com estrutura de documento real — 15 passam com zero erros, e
as duas que não passam são explicáveis: uma é inválida no XSD oficial de
propósito, a outra tem valores de preenchimento incoerentes entre si (`vIBS = 0`
com `vIBSUF = 16`). **Nenhuma regra de tabela acusa nenhuma delas**, e há teste
que trava isso.

Das 28 regras de NF-e, **17 são da Camada A de IBS/CBS**: CST e `cClassTrib`
conferidos contra a **tabela oficial embarcada** da SVRS — 18 CST e 164
classificações, versionadas no repositório com URL de origem, data e sha256
([procedência](https://github.com/JoseTorquato/fiscal-mcp/blob/main/regras/tabelas/PROCEDENCIA.md)).
Mais aritmética por item, exclusividade de regime, presença condicional e as
alíquotas de transição de 2026.

`fiscal-mcp tabelas` diz qual versão da tabela está embarcada. Quem valida contra
tabela precisa saber contra qual.

A regra de IBS/CBS emite **aviso**, não erro: a NT 2025.002 v1.51 reclassificou
a regra de rejeição correspondente (UB12-10) como *implementação futura*, então
a nota não é recusada por isso hoje. Ela carrega data de reavaliação, e um teste
falha quando essa data passa. Acusar errado é pior que não acusar.

**Tem um XML real que pode compartilhar?** É a contribuição mais valiosa
possível agora — abra uma issue com os dados trocados por fictícios.

## Escrever uma regra

Regras são dados, não código. Absorver uma nota técnica deveria ser editar um
YAML — e é:

```yaml
- id: tot-produtos-confere
  tipo: soma_itens
  severidade: erro          # erro | aviso | informacao
  campo_item: prod/vProd
  campo_total: total/ICMSTot/vProd
  tolerancia: "0.01"
  mensagem: O total de produtos não bate com a soma dos itens
  acao: >
    Some o vProd de cada item e compare com total/ICMSTot/vProd.
```

Tipos disponíveis: `existe`, `nao_vazio`, `valor_em`, `formato`, `soma_itens`,
`condicional`.

**Escopo.** Por padrão a regra roda uma vez, na raiz da nota. Com `escopo: item`
ela roda uma vez por item, com os caminhos relativos ao `det` — e o achado diz
qual item, pelo `nItem`:

```yaml
- id: ibs-grupo-ausente
  tipo: existe
  escopo: item              # documento (padrão) | item
  campo: imposto/IBSCBS
```

**Caminho absoluto.** Num `escopo: item`, o caminho que começa com `/` vale a
partir da raiz da nota. É o que permite uma regra olhar o item e algo fora dele
ao mesmo tempo:

```yaml
- id: ibs-totais-presentes
  tipo: condicional
  escopo: item
  quando_campo: imposto/IBSCBS/CST     # relativo ao item
  campo: /total/IBSCBSTot              # a partir da raiz
```

**Vigência.** Regra que ainda não estabilizou declara quando será reavaliada.
Não é comentário: um teste falha quando a data passa, e é assim que a manutenção
deixa de depender de memória.

```yaml
  vigencia:
    reavaliar_em: "2026-09-01"
    fonte: "Ato Técnico Conjunto RFB/CGIBS nº 1, de 31/07/2026"
```

**Todo achado precisa de `acao`.** Quem lê é um agente que vai tentar de novo —
erro sem ação vira loop de retry ou nota duplicada. Um teste falha se alguma
regra não tiver.

## Contribuir

O que mais ajuda, em ordem:

1. **XML real anonimizado** — principalmente NF-e, e municípios de NFS-e
   diferentes.
2. **Código de rejeição que você levou** e não está no catálogo.
3. **Regra nova** em `regras/`, com as duas fixtures.
4. **Leitura da seção 7 da NT 2025.002-RTC v1.51** — o leiaute de IBS/CBS já
   está mapeado; o que falta confirmar em fonte primária são os códigos de
   rejeição, e nenhum entra aqui sem leitura humana.

Antes de abrir PR, leia o [CONTRIBUTING](https://github.com/JoseTorquato/fiscal-mcp/blob/main/CONTRIBUTING.md).
Há uma regra sem exceção: **PR com dado fiscal real identificável é fechado sem
merge.**

## Como isso vai crescer

O produto é a **validação**: o validador mais fundo que existe para NF-e, que
roda offline e que você pode conferir antes de transmitir. Emissão está
**suspensa, com gatilho escrito** — ver
[ADR-0011](https://github.com/JoseTorquato/fiscal-mcp/blob/main/docs/adr/0011-validacao-e-o-produto.md).
O que vem depois, e por que nesta ordem, está escrito:

| Documento | Para quê |
|---|---|
| [ROADMAP.md](https://github.com/JoseTorquato/fiscal-mcp/blob/main/ROADMAP.md) | as fases e o critério de saída de cada uma |
| [BACKLOG.md](https://github.com/JoseTorquato/fiscal-mcp/blob/main/BACKLOG.md) | as tarefas, priorizadas |
| [docs/adr/](https://github.com/JoseTorquato/fiscal-mcp/blob/main/docs/adr/) | as decisões e por que foram tomadas assim |
| [docs/spec/](https://github.com/JoseTorquato/fiscal-mcp/blob/main/docs/spec/) | o produto em detalhe |

Três decisões que explicam o resto:

- **[ADR-0011](https://github.com/JoseTorquato/fiscal-mcp/blob/main/docs/adr/0011-validacao-e-o-produto.md)** — validação é o
  produto; emissão sai do caminho crítico e só volta se um gatilho nomeado
  disparar.
- **[ADR-0008](https://github.com/JoseTorquato/fiscal-mcp/blob/main/docs/adr/0008-validar-antes-de-construir.md)** — não escrevo
  integração com SEFAZ antes de saber que existe quem pague pela manutenção.
- **[ADR-0005](https://github.com/JoseTorquato/fiscal-mcp/blob/main/docs/adr/0005-certificado-nunca-transita.md)** — certificado
  digital de cliente não passa pela minha infra. O A1 é a identidade jurídica da
  empresa.

## Licença

MIT — código e regras.

---

Feito por [José Torquato](https://josetorquato.dev), que também mantém o
[Cilada](https://josetorquato.dev/cilada/).
