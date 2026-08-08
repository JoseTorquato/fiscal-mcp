# Spec 01 — Arquitetura

## Visão geral

```
    ┌─────────────┐
    │   agente    │  Claude, Cursor, n8n, código próprio
    └──────┬──────┘
           │ protocolo MCP (stdio ou HTTP)
    ┌──────▼───────────────────────────────────┐
    │  servidor fiscal-mcp                      │
    │                                           │
    │  ferramentas ── validação ── tradução     │
    │       │            local      de erro     │
    │       ▼                                   │
    │  ┌─────────────────────────────────┐      │
    │  │ adaptador do documento          │      │
    │  │  nfe/ nfse/ sped/               │      │
    │  └──────────────┬──────────────────┘      │
    │                 │                          │
    │  ┌──────────────▼──────────────────┐      │
    │  │ transporte assinado             │      │
    │  │  certificado + SOAP/REST + retry│      │
    │  └──────────────┬──────────────────┘      │
    └─────────────────┼──────────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        ▼                            ▼
   SEFAZ estadual            prefeitura / NFS-e nacional
   (NF-e, NFC-e)             (NFS-e)
```

## Camadas, e por que estão separadas

### 1. Ferramentas MCP

A superfície que o agente enxerga. Nomeadas por **intenção de negócio**
(`emitir_nfe`, `consultar_situacao`), nunca por operação de webservice
(`NfeAutorizacao4`). Contrato detalhado em
[spec 02](02-contrato-de-ferramentas.md).

### 2. Validação local

Roda **antes** de qualquer chamada externa. Existe por três razões:

- rejeição da SEFAZ é lenta e consome janela de emissão;
- a mensagem de rejeição costuma ser críptica;
- um agente que erra rápido e barato itera melhor.

Cobre schema XSD, regras de negócio conhecidas (dígito verificador, coerência de
totais, campos obrigatórios do grupo IBS/CBS) e coisas que a SEFAZ rejeitaria.

### 3. Adaptador do documento

Onde mora o conhecimento de cada documento fiscal. É a camada que **mais muda**,
porque é onde nota técnica bate. Isolada de propósito: mudança de leiaute não
pode obrigar a mexer em transporte nem em ferramenta.

### 4. Transporte assinado

Certificado digital, assinatura XML, SOAP ou REST conforme o webservice, retry e
timeout. Não conhece regra fiscal — só sabe assinar e falar. Isolar aqui permite
testar a assinatura sem envolver SEFAZ.

## Modelo de implantação

Três formas, na ordem em que serão suportadas:

| Modo | Onde roda | Certificado | Para quem |
|---|---|---|---|
| **local (stdio)** | máquina do dev | do próprio dev | desenvolvimento e avaliação |
| **auto-hospedado (HTTP)** | infra do cliente | do cliente, na infra dele | produção de quem tem time |
| **gerenciado** | nossa infra | ver [ADR-0005](../adr/0005-certificado-nunca-transita.md) | quem não quer operar |

O modo local é o que faz o funil funcionar: instalar e emitir em homologação sem
falar com ninguém.

## Decisões que valem registrar aqui

- **Homologação é o padrão.** Apontar para produção exige variável de ambiente
  explícita e é logado. Agente emitindo nota de verdade por engano é incidente
  fiscal, não bug.
- **Toda operação é idempotente ou explicitamente não é.** Emissão de nota não é
  idempotente por natureza; a ferramenta precisa deixar isso óbvio no contrato e
  exigir chave de idempotência de quem chama.
- **Nenhuma operação irreversível sem confirmação.** Cancelamento e inutilização
  de numeração exigem parâmetro de confirmação separado. Ver
  [spec 02](02-contrato-de-ferramentas.md).
