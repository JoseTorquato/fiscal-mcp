# Imagem do servidor MCP. Existe por um motivo específico: o público-alvo deste
# projeto é majoritariamente dev de ERP em Delphi e C#, não em Python. `docker
# run` é a forma de usar a ferramenta sem instalar Python nem gerenciar venv.
FROM python:3.12-slim

LABEL io.modelcontextprotocol.server.name="io.github.josetorquato/fiscal-mcp"
LABEL org.opencontainers.image.source="https://github.com/JoseTorquato/fiscal-mcp"
LABEL org.opencontainers.image.description="Valida NF-e, NFC-e e NFS-e offline, com schema XSD oficial e sem certificado."
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app
COPY . .

# O extra [xsd] entra na imagem: quem roda por Docker não vai querer descobrir
# depois que a camada mais valiosa não estava instalada.
RUN pip install --no-cache-dir ".[servidor,xsd]"

# Usuário sem privilégio. O servidor só lê XML que chega pela entrada padrão;
# não precisa de nada além disso, e rodar como root seria pedir problema à toa.
RUN useradd --create-home --uid 1000 fiscal
USER fiscal

# Sanidade de build: imagem que sobe sem as regras ou sem as tabelas é pior que
# imagem que não sobe. Falhar aqui é falhar no lugar certo.
RUN python -c "\
from fiscal_mcp.regras import carrega; \
from fiscal_mcp.tabelas import resumo; \
assert len(carrega()) >= 10, 'regras não embarcadas'; \
assert resumo()['disponivel'], 'tabela oficial não embarcada'; \
print('regras e tabelas ok')"

ENTRYPOINT ["fiscal-mcp-servidor"]
