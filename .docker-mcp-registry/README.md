# Submissão ao Docker MCP Catalog

Isto **não** é usado pelo projeto. É o arquivo pronto para o PR em
[`docker/mcp-registry`](https://github.com/docker/mcp-registry), versionado aqui
para que a submissão não precise ser reconstruída do zero e para que o
`commit` fique rastreável.

O formato foi conferido contra os `server.yaml` reais do catálogo, não deduzido.

## Como submeter

```bash
gh repo fork docker/mcp-registry --clone
cd mcp-registry
task create -- --category productivity https://github.com/JoseTorquato/fiscal-mcp
# confira o server.yaml gerado contra .docker-mcp-registry/servers/fiscal-mcp/server.yaml
task build -- fiscal-mcp     # builda e testa a imagem localmente
git checkout -b add-fiscal-mcp && git add servers/fiscal-mcp && git commit && gh pr create
```

Depois do merge, o Docker builda e assina a imagem, e ela aparece no Docker
Desktop em até 24 h.

## Antes de abrir o PR

- [ ] `commit` no `server.yaml` aponta para o commit que você quer publicar
- [ ] a imagem sobe: `docker run -i --rm fiscal-mcp:teste` responde ao
      `initialize` do protocolo MCP
- [ ] a licença é permissiva (MIT — o catálogo recusa GPL)
- [ ] o `Dockerfile` tem o `LABEL io.modelcontextprotocol.server.name`
