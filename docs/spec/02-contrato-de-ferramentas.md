# Spec 02 — Contrato das ferramentas MCP

O agente não lê documentação. O contrato da ferramenta **é** a documentação —
nome, descrição e schema são o que ele usa para decidir. Ferramenta mal nomeada
vira agente que chama a coisa errada com dinheiro real.

## Princípios

### 1. Nomear por intenção, não por webservice

```
✅ emitir_nfe            ❌ NfeAutorizacao4
✅ consultar_situacao    ❌ NfeConsultaProtocolo4
✅ cancelar_nfe          ❌ RecepcaoEvento(tpEvento=110111)
```

O agente sabe o que quer fazer, não como a SEFAZ chama.

### 2. Uma ferramenta, uma decisão

Se a descrição precisa de "se X então Y, senão Z", são duas ferramentas. Agente
erra em condicional dentro de descrição.

### 3. O perigo tem que estar no nome e na descrição

Toda ferramenta declara, na primeira linha da descrição, se é reversível e se
tem efeito fiscal:

```
emitir_nfe
  ⚠️ IRREVERSÍVEL EM PRODUÇÃO. Emite NF-e com efeito fiscal e jurídico.
  Em homologação, sem efeito.

consultar_situacao
  Somente leitura. Sem efeito fiscal.
```

### 4. Erro é conteúdo, não exceção

O retorno de erro precisa dizer **o que fazer**, porque quem lê é um agente que
vai tentar de novo:

```json
{
  "ok": false,
  "codigo": "539",
  "mensagem_sefaz": "Rejeicao: Duplicidade de NF-e com diferenca na chave de acesso",
  "significa": "Já existe nota autorizada com esse número e série para este CNPJ.",
  "acao": "Consulte a nota existente com consultar_nfe antes de reemitir. NÃO reemita com o mesmo número.",
  "reversivel": true
}
```

Sem esse campo `acao`, o agente reemite — e duplica nota fiscal.

## Convenções

### Ambiente

Toda ferramenta com efeito fiscal recebe `ambiente` explícito
(`homologacao` | `producao`), sem padrão implícito de produção. O servidor
recusa `producao` se a variável de ambiente correspondente não estiver ligada.

### Confirmação para o irreversível

Operações destrutivas exigem um segundo parâmetro que o agente precisa preencher
deliberadamente:

```
cancelar_nfe(chave, justificativa, confirmo_cancelamento=true)
inutilizar_numeracao(serie, faixa, confirmo_inutilizacao=true)
```

Não é segurança de verdade — é atrito proposital contra chamada acidental.

### Idempotência

Emissão aceita `chave_idempotencia` fornecida por quem chama. Duas chamadas com a
mesma chave devolvem o mesmo resultado em vez de emitir duas notas. Sem a chave,
a ferramenta avisa na descrição que não é idempotente.

### Tamanho de resposta

XML de NF-e é grande e estoura contexto de agente à toa. O padrão é devolver
**resumo estruturado**; o XML completo só sob pedido explícito
(`incluir_xml=true`) ou por referência a um arquivo.

## Superfície inicial — NF-e

| Ferramenta | Efeito | Descrição curta |
|---|---|---|
| `validar_nfe` | nenhum | valida localmente sem enviar; devolve pendências |
| `emitir_nfe` | ⚠️ irreversível em produção | valida, assina, transmite, aguarda autorização |
| `consultar_nfe` | leitura | situação por chave de acesso |
| `cancelar_nfe` | ⚠️ irreversível | cancela dentro do prazo legal; exige justificativa |
| `corrigir_nfe` | fiscal | carta de correção (CC-e) |
| `inutilizar_numeracao` | ⚠️ irreversível | inutiliza faixa não usada |
| `consultar_status_servico` | leitura | a SEFAZ do estado está no ar? |
| `baixar_danfe` | leitura | PDF do DANFE |

`consultar_status_servico` parece trivial e não é: quando a SEFAZ cai, o agente
precisa saber que o problema não é dele, senão fica em loop de retry.

## Superfície inicial — NFS-e

Mesma forma, com uma diferença: o município é parâmetro obrigatório e a
capacidade varia. A ferramenta declara o que aquele município suporta em vez de
falhar no meio:

```
consultar_capacidade_municipio(codigo_ibge)
  → { padrao: "nacional" | "abrasf_2.04" | "proprio",
      suporta: ["emitir", "consultar", "cancelar"],
      homologacao_disponivel: true|false,
      observacoes: "..." }
```

Ver [ADR-0006](../adr/0006-estrategia-nfse-municipal.md).

## Superfície inicial — SPED

Só leitura na primeira fase. Gerar SPED é responsabilidade contábil e o risco de
errar é grande demais para começar por aí.

| Ferramenta | Descrição |
|---|---|
| `ler_sped` | interpreta arquivo e devolve estrutura navegável |
| `validar_sped` | confere leiaute e regras de totalização |
| `resumir_sped` | totais por bloco, para o agente conseguir raciocinar sem carregar o arquivo inteiro |
