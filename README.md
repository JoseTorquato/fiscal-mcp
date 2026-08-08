# fiscal-mcp

**Servidores MCP para o fiscal brasileiro.** NF-e, NFS-e e SPED expostos como
ferramentas que um agente de IA consegue usar — com certificado digital,
homologação e as notas técnicas da SEFAZ tratadas por baixo.

> ⚠️ **Status: especificação.** Ainda não há código. Este repositório contém a
> visão de produto, as decisões de arquitetura (ADRs) e o backlog. Se você chegou
> aqui procurando algo instalável, ainda não é hoje.

---

## O problema

Integrar com o fiscal brasileiro é caro e ninguém quer fazer. Não porque é
intelectualmente difícil, mas porque é **hostil e instável**:

- A NF-e tem leiaute definido por notas técnicas que mudam com prazo curto.
- A NFS-e é municipal: são milhares de prefeituras, cada uma com schema,
  autenticação e ambiente de homologação próprios. O padrão nacional existe e
  avança, mas a adoção é parcial.
- Autenticação depende de **certificado digital ICP-Brasil** — A1 em arquivo,
  A3 em token físico.
- Homologação e produção são ambientes separados, e o de homologação cai.

E agora tem prazo: desde **3 de agosto de 2026** o preenchimento dos campos de
IBS e CBS é obrigatório nos documentos fiscais do regime regular, e notas sem
eles podem ser rejeitadas ([CGIBS](https://www.cgibs.gov.br/novo-marco-da-reforma-tributaria-inicia-em-03-de-agosto-com-preenchimento-obrigatorio-dos-campos-relativos-ao-ibs-e-a-cbs)).

Enquanto isso, o ecossistema MCP explodiu — e não tem camada Brasil. Um agente
consegue mexer no seu Notion, no seu GitHub e no seu Slack, mas não consegue
consultar uma nota fiscal.

## A tese

O código de uma integração é commodity: um dev competente gera o esqueleto de um
servidor MCP numa tarde usando IA. **O que não se gera com IA é a manutenção** —
acompanhar nota técnica, sobreviver a mudança de leiaute, saber que a SEFAZ do
estado X responde diferente da do estado Y, e ter isso testado contra homologação
todo dia.

Por isso o produto não é o servidor. É o servidor **mantido**.

## O que existe hoje no ecossistema

Pesquisa de 06/08/2026 — três projetos tocam o tema:

| Projeto | Estrelas | Abordagem |
|---|---|---|
| `rodrigo-do-carmo/mcp-nota-fiscal` | 1 | wrapper de API paga de terceiro |
| `cmendezs/mcp-nfe-br` | 0 | validação de CPF/CNPJ; integração SEFAZ *planejada* |
| `davi713albano-coder/mcp-server-brasil` | 0 | APIs simples (CNPJ, CEP, cotação) |

**Ninguém entregou integração real com SEFAZ.** Ninguém encosta em NFS-e
municipal. A parte difícil continua aberta — e é exatamente ela que vale.

## Escopo

Vertical fiscal, nesta ordem:

```
nfe/     NF-e e NFC-e (modelos 55 e 65) — emissão, consulta, cancelamento, CC-e
nfse/    NFS-e — padrão nacional primeiro, adapters municipais depois
sped/    EFD ICMS/IPI, EFD-Contribuições, ECD, ECF — leitura e validação
```

Fora de escopo por enquanto: CT-e, MDF-e, e qualquer coisa que não seja fiscal.
A tentação de virar "catálogo de integrações brasileiras" está registrada e
recusada no [ADR-0001](docs/adr/0001-escopo-vertical-fiscal.md).

## Como ler este repositório

| Documento | Para quê |
|---|---|
| [ROADMAP.md](ROADMAP.md) | as fases e o critério de saída de cada uma |
| [BACKLOG.md](BACKLOG.md) | as tarefas, priorizadas |
| [docs/spec/](docs/spec/) | o que o produto é, em detalhe |
| [docs/adr/](docs/adr/) | as decisões e por que foram tomadas assim |

Comece por [docs/spec/00-produto.md](docs/spec/00-produto.md).

## Licença

MIT para os servidores. O serviço hospedado é separado — ver
[ADR-0002](docs/adr/0002-open-core.md).

---

Feito por [José Torquato](https://josetorquato.dev).
