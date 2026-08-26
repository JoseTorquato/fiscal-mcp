# Backlog

Tarefas por fase do [ROADMAP](ROADMAP.md). Cada uma tem **critério de pronto** —
sem isso, tarefa de projeto pessoal nunca termina, só é abandonada.

Tamanhos: **P** cabe em uma sessão de ~1h · **M** algumas sessões · **G** exige
um fim de semana ou é incerta demais para estimar.

Reescrito em 25/08/2026 conforme o [ADR-0011](docs/adr/0011-validacao-e-o-produto.md).
As tarefas de emissão (T1–T8, S1–S9) saíram para o histórico do git — voltam
junto com o ADR-0003, se o gatilho disparar.

---

> **Ciclo 01 fechado em 25/08/2026.** A fase A está completa: motor, tabela
> oficial, 17 regras de IBS/CBS e camada XSD, com 153 testes. O que sobrou da
> fase B depende de credencial ou de ação em serviço de terceiro — está marcado
> com ⏳ e listado no fim deste arquivo.

## Fase A — Confiança

### Motor

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| A1 ✅ | `escopo: item` no motor de regras | M | regra com escopo item roda em todos os `det` e o detalhe traz o `nItem`; os 41 testes atuais passam sem alteração |
| A2 ✅ | Tipo `prefixo_de` | P | reprova `cClassTrib` cujos 3 primeiros dígitos não são o CST |
| A3 ✅ | Tipos `em_tabela` e `subgrupos_por_indicador` | M | leem dado versionado do repo; sem tabela embarcada, emitem `informacao` e nunca `erro` |
| A4 ✅ | Tipos `soma_campos`, `exclusivo`, `valor_numerico_em` | M | `valor_numerico_em` compara Decimal — `0.10` e `0.1000` não geram achado |
| A5 ✅ | Bloco `vigencia` substituindo `status` | P | teste falha quando alguma regra tem `reavaliar_em` no passado |

### Dado oficial

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| A6 ✅ | Baixar CST e `cClassTrib` do Portal da Conformidade Fácil (SVRS) | P | arquivos em `regras/tabelas/` |
| A7 ✅ | `PROCEDENCIA.md` com URL, data, sha256 e versão declarada pela fonte | P | teste confere o sha256 e falha na divergência |
| A8 ✅ | Tabelas viajam dentro do wheel | P | `pip install` numa venv limpa entrega as tabelas |
| A9 ✅ | Comando que imprime a versão da tabela embarcada | P | quem depende sabe contra o que está validando |

### Regras

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| A10 ✅ | L-01 a L-04 — CST e `cClassTrib` | M | as quatro com fixture que reprova e fixture que aprova |
| A11 ✅ | L-05 — subgrupos por indicador | M | entra como **aviso**; promoção a erro exige 3 XMLs reais distintos sem falso positivo |
| A12 ✅ | L-06 a L-10 — aritmética, exclusividade, presença condicional | M | idem, dois fixtures cada |
| A13 ✅ | L-11 a L-14 — formato, enums, alíquotas | P | L-11 e L-13 como erro; L-14 como aviso com `reavaliar_em`. **L-12 saiu** (o padrão real do XSD aceita `0` sozinho — a regra teria falso positivo) e a de `tpALCZFMCBS` também (elemento não existe no pacote de schema) |
| A14 ✅ | Reescrever `ibs-cbs.yaml` sem TODO, com a mensagem da spec 05 §6 | P | a mensagem cita a postergação da UB12-10 pela v1.51 |
| A15 ✅ | Teste de ausência de falso positivo | M | XML válido com IBS/CBS passa com zero achados de severidade `erro` |

### Schema

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| A16 ✅ | `nfelib` como extra `[xsd]`; validação com `lxml.XMLSchema` | M | XML que viola o schema é reprovado |
| A17 ✅ | Tradução das mensagens do lxml, em `regras/schema/traducoes.yaml` | M | mensagens de `IBSCBS`, `cClassTrib`, `CST` e totais em português com `acao`; não reconhecida sai crua e marcada |
| A18 ✅ | `leiaute_validado_contra` na saída + rebaixamento por versão | M | documento com estrutura posterior ao pacote gera aviso, não erro |
| A19 ✅ | Teste de zero-rede cobrindo a camada de schema | P | `XMLSchema` não resolve import remoto |
| A20 ✅ | Revisar regras que o schema tornou redundantes | P | o que saiu está anotado no changelog, com o motivo |

> **Gate da fase A.** A15 e A19 são os dois testes que sustentam a promessa do
> projeto. Sem eles verdes, nada da fase B acontece.

---

## Fase B — Descoberta

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| B1 ⏳ falta o release | `mcp-name:` no README + release no PyPI | P | a string está na description publicada no PyPI, não só no GitHub |
| B2 ⏳ falta publicar | `server.json` + `mcp-publisher publish` | P | `curl` no registry devolve o servidor |
| B3 | PR no Awesome MCP Servers | P | merge feito |
| B4 | Claim do listing no Glama | P | o listing deixa de ser genérico |
| B5 ⏳ falta o PR | Dockerfile + PR no Docker MCP Catalog | M | `docker run` funciona; PR aberto |
| B6 | GitHub Action publicando no registry a cada release | P | só depois de B2 ter sido feito à mão uma vez |
| B7 ✅ | `CHANGELOG.md` amarrado a nota técnica | P | primeira entrada com data de detecção e data de suporte |
| B8 ✅ | Exemplo de config copiável para cliente MCP popular | P | copiar, colar, funcionar |
| B9 ✅ | `scripts/anonimizar.py` | M | substitui CNPJ/CPF com DV válido, razão social, endereço, chave com DV recalculado, IE/IM, assinatura, `infCpl` e `obsCont`; preserva NCM, CFOP, CST, `cClassTrib`, alíquotas e valores |
| B10 ✅ | `CONTRIBUTING.md` com a regra de anonimização | P | diz explicitamente que PR com dado real identificável é fechado sem merge |
| B11 | Corpus de fixtures a partir das samples MIT da `nfelib` | M | fixtures no repo, com origem declarada |
| B12 | Páginas por código de rejeição (`/rejeicoes/<codigo>`) | M | causa, XML errado, XML corrigido e o comando de validação |
| B13 | Validador no navegador, sem upload | G | roda 100% client-side; cada post de conteúdo aponta para ele |
| B14 | Série de posts técnicos, começando pelo que separa o que rejeita do que só multa | M | primeiro post publicado no TabNews e no LinkedIn |

---

## Fase C — Evidência de manutenção

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| C1 ✅ | Teste de vigência vencida rodando em CI agendado | P | falha e notifica quando alguma regra passou da data |
| C2 | Monitor de publicação de nota técnica | M | abre tarefa quando sai documento novo. Alerta para humano, não automação — NT precisa ser lida |
| C3 | Registro público de mudanças fiscais absorvidas | P | primeira entrada publicada |
| C4 | Suíte de validação contra o corpus, com resultado público | M | histórico visível; mudança de comportamento é detectada |
| C5 | Ler a seção 7 da NT v1.51 e abrir a Camada B | M | códigos de rejeição confirmados em fonte primária entram no catálogo |

---

## Fase D — Receita

| # | Tarefa | Tam. | Pronto quando |
|---|---|---|---|
| D1 | 60 contatos a partir dos *dependents* de `nfelib` e `PyNFe` no GitHub | M | planilha preenchida com nome, repo e origem |
| D2 | 10 conversas com o roteiro corrigido | G | 10 registros; toda conversa termina com a pergunta do piloto pago |
| D3 | Definir a fronteira paga em nível operacional ([ADR-0002](docs/adr/0002-open-core.md)) | M | documento sem ambiguidade sobre o que é pago |
| D4 | Contrato com fronteira de responsabilidade ([spec 03](docs/spec/03-credenciais-e-certificado.md)) | M | revisado por alguém com competência jurídica |
| D5 | Enquadramento fiscal e contábil da operação | M | resolvido antes de faturar |

> **O roteiro mudou.** O do [ADR-0008](docs/adr/0008-validar-antes-de-construir.md)
> pergunta *"você pagaria para nunca mais manter essa integração?"*, e a resposta
> é sim universal — o ACBr Pro já provou isso comercialmente a R$ 1.500/ano.
> As perguntas que discriminam:
>
> 1. Quanto você pagou de licença fiscal em 2025, e para quem?
> 2. Quantas horas custou a NT 2025.002 este ano?
> 3. Você já avaliou o ACBr Pro? Por que sim ou por que não?
> 4. Me conta o último XML que rejeitou. Quanto tempo levou para achar a causa?
> 5. **Topa pagar R$ 3.000 por um piloto de 60 dias?**
>
> Sem cartão de crédito, não é validação.

---

## Dívidas e riscos conhecidos

| Item | Risco | Mitigação |
|---|---|---|
| Falso positivo em nota real | destrói confiança de forma irreversível | regra vira aviso no mesmo dia do relato; L-05 nasce como aviso por padrão |
| Pacote XSD não cobrir a v1.50/1.51 | reprova nota válida com monofasia | declarar a versão na saída e rebaixar por versão (A18) |
| Códigos de rejeição não confirmados | citar número errado é pior que não citar | nenhum número entra sem leitura humana da NT (C5) |
| Tabela da SVRS mudar ou sair do ar | quebra build de terceiro | tabela versionada no repo; CI nunca baixa |
| Concorrente fechar as lacunas | perda do diferencial técnico | a vantagem defensável é o catálogo com ação, que é acúmulo |
| PyNFe lançar MCP oficial | redesenha o tabuleiro | gatilho de revisão do ADR-0011 |
| Bus factor = 1 | é a objeção que mata a venda de manutenção | não se resolve com feature; endereçar com registro público e código aberto |
| Vontade de codar emissão | meses gastos fora do caminho crítico | [ADR-0011](docs/adr/0011-validacao-e-o-produto.md), escrito exatamente para esse momento |
| Autor com emprego integral | ritmo imprevisível | tarefas P e M; nada de G fora de fim de semana |

---

## O que ficou pendente do ciclo 01, e por quê

Nada aqui é trabalho técnico: é ação que exige credencial sua ou aprovação de
terceiro. A ordem importa — o registry só valida a posse contra a *description
publicada no PyPI*, então o release vem primeiro.

| # | Ação | Por que não dá para fazer daqui |
|---|---|---|
| B1 | `python -m build && twine upload dist/*` | exige o token do PyPI. A string `mcp-name:` já está no README, mas o registry lê a description **publicada**, não a do GitHub — é a pegadinha que faz a primeira tentativa falhar |
| B2 | `mcp-publisher login github && mcp-publisher publish` | exige device code no github.com/login/device. O `server.json` já está versionado e com o `name` idêntico ao `mcp-name:` do README |
| B3 | PR no Awesome MCP Servers | ação em repositório de terceiro, com a sua autoria |
| B4 | Claim do listing no Glama | exige login na conta |
| B5 | PR no Docker MCP Catalog | fork de `docker/mcp-registry` + `task create`. O `Dockerfile` já está pronto e com o `LABEL` que o catálogo exige |
| B6 | Action publicando no registry a cada release | só depois de B2 ter sido feito à mão uma vez, para saber o que quebra |

**Critério de saída do ciclo:** três das quatro linhas do
[PLANO-CICLO-01](PLANO-CICLO-01.md) estão verdes. A quarta — `fiscal-mcp`
aparecer na busca do registry — é B1 + B2.
