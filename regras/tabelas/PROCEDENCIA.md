# Procedência das tabelas

Dado fiscal sem procedência é boato. Cada arquivo aqui registra de onde veio,
quando, com que conteúdo exato e o que foi descartado no caminho.

**O CI nunca baixa nada.** Indisponibilidade da fonte não pode quebrar o build
de quem depende do pacote. A atualização é ato deliberado:

```
python scripts/baixar_tabelas.py     # confere o diff, atualiza o sha256 aqui, abre PR
```

---

## `cst-cclasstrib.json`

| | |
|---|---|
| **Origem** | Portal da Conformidade Fácil (SVRS) — <https://dfe-portal.svrs.rs.gov.br/CFF/ClassificacaoTributaria> |
| **Baixado em** | 25/08/2026 |
| **Publicação declarada pela fonte** | 22/06/2026 (maior `DthPublicacao` do conjunto) |
| **sha256** | `89acd2b3229a0d16acbdeed65741fb26dd52108857d6f86ba01002d13b92f4df` |
| **Conteúdo** | 18 CST · 164 cClassTrib |
| **Extraído de** | variável `dadosOriginais` da própria página — a mesma que alimenta a exportação CSV/Excel do portal |

### Conferência contra fonte secundária

Os 18 códigos de CST batem integralmente com as duas fontes secundárias
independentes citadas na [spec 05 §7](../../docs/spec/05-camada-a-ibs-cbs.md):

`000` `010` `011` `200` `220` `221` `222` `400` `410` `510` `515` `550`
`620` `800` `810` `811` `820` `830`

### Campos descartados na normalização

O portal serve ~4 MB; o arquivo embarcado tem ~380 KB. A diferença é isto, e
nada além disto:

| Campo | Por que saiu |
|---|---|
| `CstNavigation` | duplicata integral do CST pai, já presente um nível acima |
| `Anexos`, `AnexoNew`, `NroAnexo` | listas de NCM por anexo de monofasia. São o grosso do peso e não participam de nenhuma regra da Camada A — entram quando houver regra que as use |
| `CtrDthInc` | carimbo de controle interno do portal, sem uso fiscal |

Nenhum indicador (`Ind*`), percentual de redução, vigência ou nome foi alterado.
Datas `DthPublicacao`/`DthIniVig`/`DthFimVig` foram truncadas de
`AAAA-MM-DDT00:00:00` para `AAAA-MM-DD` — hora não significa nada aqui.

### O que muda quando a tabela mudar

Divergência de sha256 **falha o build**. É intencional: se o arquivo mudou sem
passar por aqui, alguém editou dado oficial à mão. O caminho certo é rodar o
script, ler o diff, atualizar esta página e registrar a data de detecção no
CHANGELOG.
