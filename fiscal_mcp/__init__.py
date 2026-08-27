"""fiscal-mcp — validador de documento fiscal brasileiro, offline e auditável.

Valida NF-e, NFC-e e NFS-e do padrão nacional em três camadas: schema XSD
oficial, regras fiscais declarativas (incluindo IBS/CBS conferido contra a
tabela oficial da SVRS) e chave de acesso.

Nada aqui assina, transmite, emite ou cancela documento — não por falta de
tempo, mas por decisão. Ver docs/adr/0010-fatia-zero-sem-credencial.md e
docs/adr/0011-validacao-e-o-produto.md.
"""

__version__ = "0.2.1"
