### Alterado

- **O espelho do Docker MCP Catalog aponta para a 0.3.1.**
  - **O que mudou:** nada muda para quem usa o pacote; a cópia versionada do
    `server.yaml` submetido ao catálogo do Docker passa a apontar para o commit
    da 0.3.1, como o PR aberto lá.
  - **Documento oficial:** não se aplica (metadado de distribuição, não fiscal).
  - **O que mudou no código:** `.docker-mcp-registry/servers/fiscal-mcp/server.yaml`,
    `commit` de `a26a709` (v0.3.0) para `b1c5257` (v0.3.1), copiado de
    docker/mcp-registry#4803. No CHANGELOG da 0.3.1, só a quebra de linha de um
    item, sem mudar o texto.
  - **Desde quando vale:** não se aplica — próxima versão.
