# ADR-0004 — Python com o SDK oficial de MCP

- **Data:** 06/08/2026
- **Status:** aceita

## Contexto

Escolha de linguagem e de SDK para os servidores. Candidatos: Python, Node/
TypeScript, Go.

## Decisão

**Python**, com o SDK oficial de MCP, distribuído no PyPI.

## Justificativa

**1. É onde o autor é mais rápido.** Projeto de uma pessoa em tempo parcial: a
linguagem principal de quem escreve importa mais que benchmark.

**2. É onde o ecossistema fiscal brasileiro está.** As bibliotecas maduras de
NF-e, assinatura XML e comunicação com SEFAZ em código aberto são majoritariamente
Python. Reaproveitar o que existe encurta meses.

**3. O comprador é Python-friendly.** ERPs e integradores fiscais brasileiros
usam Python e PHP predominantemente. Node é comum em produto, menos em fiscal.

**4. Distribuição.** `pip install` é o caminho natural do público.

## Consequências

- Empacotar servidor MCP em Python para uso local exige atenção a ambiente
  (`uvx`/`pipx` são o caminho recomendado, não `pip install` global).
- Performance não é fator relevante aqui: o gargalo é o webservice da SEFAZ, não
  a linguagem.
- Se um dia houver demanda por servidor embarcado em produto Node, o protocolo
  MCP é agnóstico — dá para reimplementar a superfície sem reescrever o domínio,
  desde que a fronteira do [spec 01](../spec/01-arquitetura.md) seja respeitada.

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Node/TypeScript | ecossistema fiscal BR mais fraco; autor mais lento |
| Go | binário único é atraente para distribuição, mas ecossistema fiscal quase inexistente |
| Implementar o protocolo à mão | MCP ainda evolui; acompanhar spec à mão é custo recorrente sem retorno |
