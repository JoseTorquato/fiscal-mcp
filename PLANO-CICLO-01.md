# Plano — Ciclo 01

Derivado da pesquisa de 25/08/2026 (dossiê de posicionamento). Este documento é
temporário: quando o ciclo fechar, o que sobrar vira BACKLOG e o resto se apaga.

**Objetivo do ciclo:** sair de "validador honesto mas raso, invisível" para
"validador que ninguém mais tem, encontrável". Sem escrever uma linha de emissão.

**Duração alvo:** 30 dias de tempo parcial. Sem data de entrega — as tarefas têm
ordem e critério de pronto, a velocidade é o que for.

---

## O que mudou de entendimento

Três coisas que a pesquisa derrubou e que justificam este ciclo:

1. **Emissão deixou de ser terreno livre.** Três projetos já emitem — um deles
   (`saviski/nfse-nacional-mcp`) faz assinatura XMLDSig + mTLS + transmissão
   direta ao Sistema Nacional em 2.737 linhas, publicamente. O risco do
   [ADR-0003](docs/adr/0003-integracao-direta-com-sefaz.md) não é mais técnico;
   passou a ser econômico e de responsabilidade civil. Ver
   [ADR-0011](docs/adr/0011-validacao-e-o-produto.md).

2. **O nicho de validação offline está ocupado só na aparência.** O maior
   concorrente anuncia "validação XSD" e não tem XSD nenhum; a tool de validação
   principal dele faz uma chamada HTTP no meio. Ninguém entrega validação de
   schema real nem garantia verificável de zero-rede.

3. **A regra de IBS/CBS não estava travada por falta de informação.** O leiaute
   está publicado e mapeado. O que não está confirmado são os *códigos de
   rejeição* — e essa distinção separa o que pode virar erro do que não pode.

---

## Frentes, na ordem

A ordem importa. Publicar nos registries antes de fechar a Camada A significa
que o primeiro dev atraído pelo conteúdo de IBS/CBS instala a ferramenta e
encontra `pendente_confirmacao`. Isso queima a primeira impressão com o público
mais valioso, e primeira impressão de dependência fiscal não se recupera.

| # | Frente | Spec | Por que nesta posição |
|---|---|---|---|
| 1 | Camada A do IBS/CBS | [spec 05](docs/spec/05-camada-a-ibs-cbs.md) | É o valor. Sem isso, o resto divulga uma promessa vazia |
| 2 | Validação por schema XSD | [spec 06](docs/spec/06-validacao-xsd.md) | É o diferencial que ninguém tem. Depende da 1 só por ordem de atenção |
| 3 | Distribuição | [spec 07](docs/spec/07-distribuicao.md) | Três horas de trabalho, maior retorno por hora — mas só depois de haver o que mostrar |
| 4 | Reestruturação de docs | este arquivo + ADR-0011 | Roda em paralelo. É o que transforma decisão em registro |

---

## Critério de saída do ciclo

O ciclo fecha quando as quatro linhas abaixo forem verdadeiras. Não antes, e
não "quase".

- [ ] **Nenhuma regra com `status: pendente_confirmacao` no repositório.** Ou a
      regra tem vigência declarada, ou tem data de reavaliação, ou saiu.
- [ ] **`fiscal-mcp validar` aponta o grupo IBS/CBS ausente com o motivo certo** —
      citando a postergação da UB12-10 pela NT v1.51, não uma obrigatoriedade
      que hoje não rejeita.
- [ ] **Um XML de NF-e com `cClassTrib` incompatível com o CST é reprovado como
      erro**, com ação acionável, e um XML válido passa sem falso positivo.
- [ ] **`fiscal-mcp` aparece na busca do registry oficial de MCP.**

---

## Ordem de execução sugerida

Blocos de trabalho, não datas. Cada bloco cabe em uma ou duas sessões.

### Bloco 1 — Fundação da Camada A
Motor de regras ganha escopo por item e os tipos novos da [spec 05](docs/spec/05-camada-a-ibs-cbs.md).
Nenhuma regra fiscal nova ainda — só a capacidade de expressá-las.
**Pronto quando:** uma regra de teste com `escopo: item` roda em todos os `det`
e o detalhe do achado traz o `nItem`.

### Bloco 2 — Tabela oficial embarcada
Baixar CST e `cClassTrib` do Portal da Conformidade Fácil, versionar com
procedência (URL, data, sha256) e escrever o carregador.
**Pronto quando:** o repo tem a tabela, o teste confere o hash, e existe um
comando que diz qual versão da tabela está embarcada.

### Bloco 3 — As 14 regras
Escrever L-01 a L-14 em YAML, com fixture de reprovação e fixture de aprovação
para cada uma.
**Pronto quando:** todas as 14 têm os dois fixtures e o teste de "nenhum falso
positivo em nota válida" passa.

### Bloco 4 — Reescrita do `ibs-cbs.yaml` e do texto do aviso
Trocar `pendente_confirmacao` pelo bloco de vigência. Reescrever a mensagem da
regra de grupo ausente com o texto da [spec 05, §6](docs/spec/05-camada-a-ibs-cbs.md).
**Pronto quando:** o arquivo não tem mais TODO e a mensagem cita a v1.51.

### Bloco 5 — Camada XSD
`nfelib` como extra opcional, validação de schema, tradução das mensagens do
lxml para português acionável, declaração explícita do pacote PL em uso.
**Pronto quando:** um XML que viola o schema é reprovado com mensagem que diz
qual campo e o que fazer — não com o erro cru do lxml.

### Bloco 6 — Distribuição
`mcp-name` no README, release no PyPI, `server.json`, `mcp-publisher publish`,
PR no Awesome MCP Servers, claim no Glama, Dockerfile, PR no Docker MCP Catalog.
**Pronto quando:** `curl` no registry devolve o servidor.

### Bloco 7 — Docs
ADR-0011 publicado, ROADMAP e BACKLOG reescritos, `CONTRIBUTING.md` com a regra
de anonimização, README atualizado com o que passou a ser verdade.
**Pronto quando:** nenhum documento do repo descreve a estratégia antiga.

---

## O que NÃO entra neste ciclo

Escrito para não ser reaberto no meio:

- **Emissão, assinatura, transmissão, certificado.** Nem spike. Ver ADR-0011.
- **Adapter municipal de NFS-e.** A NFS-e Nacional está comoditizando esse fosso.
- **SLA, contrato, cobrança.** Nada de receita antes de haver o que sustentar.
- **Script de anonimização e validador no navegador.** São do ciclo 02 — valiosos,
  mas dependem de o núcleo estar fechado.
- **As 10 conversas.** Também ciclo 02, com o roteiro corrigido: a pergunta que
  discrimina é "topa pagar R$ 3.000 por um piloto de 60 dias?", não "você pagaria
  para não manter isso?".

---

## Riscos deste ciclo, e o que fazer

| Risco | Sinal de que aconteceu | Resposta |
|---|---|---|
| Falso positivo em nota real | Alguém reporta que a ferramenta acusou errado | Regra vira aviso no mesmo dia, sem discussão. É a única falha que destrói confiança de forma irreversível |
| Pacote XSD vigente não cobrir a v1.50/1.51 | Nota com monofasia reprovada no schema | Declarar a versão do PL na saída e rebaixar o achado de schema para aviso quando o documento usar grupo posterior ao pacote |
| A tabela da SVRS mudar de formato ou sair do ar | Download quebra no CI | A tabela está versionada no repo; o CI só avisa da divergência, nunca falha por indisponibilidade externa |
| Escopo inflar para emissão | Você abrir o manual de integração da SEFAZ | Reler o ADR-0011. Foi escrito exatamente para este momento |
| Concorrente fechar as lacunas antes | Release do `mcp-fiscal-brasil` com XSD real | Não muda o plano. A vantagem defensável é o catálogo de rejeições com ação, que é acúmulo, não feature |

---

## Métrica única do ciclo

Não é estrela, não é download. É esta:

> **Alguém de fora roda a validação num XML real e relata o resultado.**

É o mesmo critério de saída que a fase 0.5 já tinha, e continua sendo o único
sinal que importa nesta etapa. As demais métricas medem esforço, não valor.
