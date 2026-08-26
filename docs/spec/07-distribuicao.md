# Spec 07 — Distribuição

> Três horas de trabalho. É a maior razão retorno/esforço de todo o ciclo, e a
> única frente onde o projeto está atrás por omissão, não por escolha.

## 1. Situação

O `fiscal-mcp` está no PyPI e tem landing. **Não está no registry oficial de
MCP**, não tem Docker, não tem `server.json`, não tem CHANGELOG. O concorrente
principal tem duas entradas no registry, npm, Docker, Smithery e site de docs.

Num mercado onde a descoberta acontece por diretório e por ingestão automática
entre catálogos, isso é desvantagem barata de corrigir e cara de ignorar.

## 2. Onde publicar, e onde não

| Destino | Esforço | Vale? |
|---|---|---|
| **Registry oficial de MCP** | 1–2 h | **Sim, primeiro.** É a fonte que os demais diretórios e os clientes ingerem |
| **Awesome MCP Servers** | 30 min | **Sim.** 90,9k estrelas — é o link que o Google indexa |
| **Docker MCP Catalog** | médio | **Sim, depois.** `docker run` é o formato que dev de ERP quer, e entra no Docker Desktop |
| **Glama** | 15 min | Sim. Já indexa por crawl; reivindicar a propriedade tira o listing genérico |
| PulseMCP | zero | Indexa sozinho |
| **Smithery** | médio/alto | **Não.** Exige servidor remoto HTTPS. O valor deste projeto é rodar offline — publicar lá contradiz a proposta |
| mcp.so, LobeHub, mcpservers.org | baixo | Baixa prioridade. Tráfego difuso |
| n8n | zero | Nada a submeter; o MCP Client Tool node consome qualquer servidor. Vale como tutorial, não como listagem |

## 3. Registry oficial — o caminho para pacote PyPI

O registry hospeda **só metadados**; o artefato continua no PyPI. A verificação
de posse procura uma string no README **que virou a description do PyPI** — o
que exige um novo release, não basta commitar no GitHub. É a pegadinha que faz
a primeira tentativa falhar.

### Passo 1 — marcar o README

```markdown
<!-- mcp-name: io.github.josetorquato/fiscal-mcp -->
```

### Passo 2 — republicar no PyPI com o README atualizado (bump de versão)

### Passo 3 — `server.json`

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.josetorquato/fiscal-mcp",
  "title": "Fiscal MCP",
  "description": "Valida NF-e, NFC-e e NFS-e nacional offline, sem certificado digital.",
  "repository": {
    "url": "https://github.com/JoseTorquato/fiscal-mcp",
    "source": "github"
  },
  "version": "0.2.0",
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "fiscal-mcp",
      "version": "0.2.0",
      "transport": { "type": "stdio" }
    }
  ]
}
```

### Passo 4 — publicar

```bash
mcp-publisher init          # gera o esqueleto
mcp-publisher login github  # device code em github.com/login/device
mcp-publisher publish
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=fiscal-mcp"
```

### Três coisas que quebram a publicação

- O `name` do `server.json` precisa ser **idêntico** à string `mcp-name:` do
  README publicado no PyPI.
- Com auth do GitHub, o namespace tem que começar por `io.github.<usuário>/`.
- `description` curta — os guias recomendam menos de 100 caracteres.

### Notas

- O registry está oficialmente **em preview**: pode haver breaking change ou
  reset de dados. Manter o `server.json` versionado no repo para republicar
  rápido.
- Automatizar depois com GitHub Actions, para que cada release atualize o
  registry sozinho. Não no primeiro dia — publique à mão uma vez, para entender
  o que quebra.

## 4. Docker

Requisitos do catálogo: `Dockerfile` na raiz e licença permissiva (MIT serve;
GPL não). Fluxo: fork do `docker/mcp-registry` → `task create` → `server.yaml` →
PR → merge → disponível em 24 h. O Docker builda e assina a imagem.

Se publicar imagem própria, o Dockerfile precisa de:

```dockerfile
LABEL io.modelcontextprotocol.server.name="io.github.josetorquato/fiscal-mcp"
```

Ganho colateral que justifica o esforço sozinho: `docker run` dá ao dev de ERP —
majoritariamente Delphi e C#, não Python — uma forma de usar a ferramenta sem
instalar Python. Esse público é o maior do fórum ACBr e hoje ninguém o atende
com ferramenta de IA.

## 5. CHANGELOG amarrado a nota técnica

Não é higiene de repositório. É o ativo comercial descrito na
[spec 04](04-manutencao.md), e é o que um dev de ERP realmente avalia antes de
adotar dependência fiscal.

Formato: cada entrada diz **o que mudou, qual documento oficial determinou, o
que mudou no código, e a partir de quando é obrigatório**.

```markdown
## 0.2.0 — 2026-09-xx

### Absorvido
- **NT 2025.002 v1.51** — UB12-10 reclassificada como implementação futura.
  A regra `ibs-grupo-ausente` continua como aviso, com o motivo corrigido.
  Detectado em 25/08/2026, suportado em 0.2.0.
  Fonte: Ato Técnico Conjunto RFB/CGIBS nº 1, de 31/07/2026.
```

O par **data de detecção / data de suporte** é o que transforma "manutenção" de
promessa em evidência. Sem histórico, é promessa; com histórico, é produto.

## 6. Critério de pronto

- [ ] `curl` no registry devolve o servidor.
- [ ] O projeto aparece no Awesome MCP Servers.
- [ ] O listing do Glama está reivindicado.
- [ ] `docker run` funciona e o PR no Docker MCP Catalog está aberto.
- [ ] `CHANGELOG.md` existe com ao menos uma entrada amarrada a nota técnica.
- [ ] O README traz um exemplo de config copiável para pelo menos um cliente MCP.
