# Spec 06 — Validação por schema XSD

> É o diferencial que nenhum concorrente entrega hoje. O maior deles anuncia
> "validação XSD" no README e não tem XSD nenhum embarcado — o próprio código
> admite, em comentário, que não substitui a validação de schema. A lacuna está
> aberta e o insumo é gratuito.

## 1. Por que isto vale o esforço

A validação por regra pega o que a regra conhece. O XSD pega o resto: elemento
fora de ordem, cardinalidade violada, tipo errado, campo inventado, escala
decimal fora do permitido. É a diferença entre *"achei o campo e ele parece
estranho"* e *"esta nota não passa no validador da SEFAZ"*.

E é honesto: continua sendo validação local, não garante autorização, e não
substitui a SEFAZ. Mas reprova antes o que a SEFAZ reprovaria.

## 2. A decisão: `nfelib` como fonte dos schemas

A [`nfelib`](https://github.com/akretion/nfelib) é MIT, ativa (365 commits,
último em 10/07/2026, 14 contribuidores) e **empacota os XSD oficiais da SEFAZ,
incluindo o leiaute 2026 com o grupo `IBSCBS`** — tem inclusive um sample
`nfe_reforma_tributaria.xml`.

Alternativas descartadas e por quê:

| Alternativa | Por que não |
|---|---|
| Baixar o XSD do Portal em build | Rede no build de terceiro. Quebra `pip install` quando a SEFAZ cai |
| Copiar os XSD para o repo | Duplica um artefato que já é mantido por alguém, e a manutenção volta para você |
| `PyNFe` | Excelente e com IBS/CBS completo, mas é biblioteca de emissão. Trazer emissão como dependência contradiz o ADR-0010 |
| `BrazilFiscalReport` | **LGPL.** Num projeto MIT com plano de open-core, é atrito de licença desnecessário. O concorrente já depende dela |

**A validação em si usa `lxml.etree.XMLSchema`**, que já é dependência. A
`nfelib` entra só pelos arquivos `.xsd` que ela carrega — não pelos bindings
generateDS.

## 3. Contrato

### Empacotamento

Extra opcional, não dependência do núcleo:

```toml
[project.optional-dependencies]
servidor = ["mcp>=2.0"]
xsd = ["nfelib>=2.0"]        # versão a fixar contra o pacote PL suportado
```

O núcleo continua funcionando sem ela. Sem o extra instalado, a validação de
schema não roda e a saída diz isso — nunca finge que rodou.

### Superfície

`validar_nfe` ganha um parâmetro:

```
validar_nfe(xml, incluir_resumo=True, schema=True)
```

`schema=True` por padrão quando o extra está instalado. Na CLI, `--sem-schema`
para desligar.

### Saída

Achados de schema entram na mesma lista, com `grupo: "schema"`, para que a
ferramenta continue devolvendo um laudo só. E a saída **declara contra o que
validou**:

```json
{
  "ok": false,
  "leiaute_validado_contra": "PL_010e_v1.02",
  "schema_disponivel": true,
  "achados": [
    {
      "id": "schema-cclasstrib-ausente",
      "severidade": "erro",
      "grupo": "schema",
      "problema": "o elemento cClassTrib é obrigatório dentro de IBSCBS",
      "detalhe": "item 2, linha 47 do XML",
      "acao": "Informe cClassTrib com 6 dígitos, começando pelos 3 dígitos do CST."
    }
  ]
}
```

## 4. O trabalho de verdade não é validar — é traduzir

`lxml` devolve mensagens assim:

```
Element '{http://www.portalfiscal.inf.br/nfe}IBSCBS': Missing child element(s).
Expected is ( {http://www.portalfiscal.inf.br/nfe}cClassTrib )., line 47
```

Isso é inútil para um agente e quase inútil para um humano. Rodar o XSD é uma
tarde; **traduzir é o produto**. Sem tradução, esta camada não vale mais que o
`xmllint` que o dev já tem.

### Requisitos da tradução

- Namespace some da mensagem. Ninguém precisa ver a URL do portal fiscal.
- Caminho vira posição legível: `item 2`, não `det[2]`.
- Toda mensagem traduzida tem `acao`, pela mesma regra do resto do projeto.
- **Mensagem não reconhecida passa adiante crua**, marcada como não traduzida —
  nunca é engolida nem adivinhada. Achado cru e honesto é melhor que achado
  bonito e errado.
- A tabela de tradução é **dado, não código**: `regras/schema/traducoes.yaml`,
  casando por padrão sobre a mensagem do lxml. Mesma tese do motor de regras.

### Priorização

Traduzir primeiro os erros que aparecem, não os que existem. Comece pelos
relacionados a `IBSCBS`, `cClassTrib`, `CST` e ao grupo de totais — é onde está a
dor de 2026 e o tráfego de busca. O resto passa cru até alguém reportar.

## 5. O risco de versão, e como não acusar errado

**O pacote de schemas vigente é o PL 010e v.1.02 (10/07/2026), que cobre a NT
2025.002 v1.40 — não a v1.50 nem a v1.51.** A v1.50 reestruturou o grupo UB para
monofasia de combustíveis.

Consequência prática: uma nota que usa a estrutura da v1.50 pode ser reprovada
por um schema que não a conhece. Isso é falso positivo, e falso positivo em
validação de schema é pior que em regra — parece autoritativo.

### Mitigação, em três partes

1. **Declarar sempre** o pacote em uso no campo `leiaute_validado_contra`.
2. **Rebaixar para aviso** quando o documento contiver elementos que o pacote não
   conhece e o erro do schema for de elemento inesperado. O texto precisa dizer
   o porquê: *"o pacote de schemas embarcado (PL 010e v1.02) cobre a NT v1.40;
   este documento parece usar estrutura posterior"*.
3. **Verificar** se existe pacote posterior ao PL 010e v1.02 antes de fixar a
   versão da `nfelib`. A pesquisa não localizou, mas é provável que exista, dado
   que a v1.50 mudou o grupo UB.

## 6. Critério de pronto

- [ ] XML que viola o schema é reprovado com mensagem em português e `acao`.
- [ ] XML válido de NF-e com IBS/CBS passa sem achado de schema. **Sem exceção**
      — se falhar, o problema é a versão do pacote, e a camada não sobe.
- [ ] Sem o extra instalado, a saída traz `schema_disponivel: false` e a nota
      explicando como habilitar, e nada quebra.
- [ ] `leiaute_validado_contra` aparece em toda saída.
- [ ] Ao menos as mensagens de `IBSCBS`, `cClassTrib`, `CST` e totais estão
      traduzidas.
- [ ] Mensagem não reconhecida sai crua, marcada como não traduzida.
- [ ] O teste da fatia zero continua passando: a validação de schema não abre
      rede. `XMLSchema` do lxml pode tentar resolver import remoto — o parser já
      usa `no_network=True`, e isso precisa de teste explícito.

## 7. Ganho colateral

Com os XSD embarcados, algumas regras da Camada A ficam redundantes (L-11 e L-12
são as candidatas óbvias). **Isso é bom.** Regra que o schema já cobre é regra a
menos para manter quando a nota técnica mudar. Ao fechar esta camada, revisar o
YAML e remover o que virou duplicata — anotando no changelog o que saiu e por
quê, para que ninguém reintroduza depois.
