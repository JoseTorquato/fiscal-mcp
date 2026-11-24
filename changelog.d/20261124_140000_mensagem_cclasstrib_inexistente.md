### Corrigido

- **cClassTrib inexistente gerava dois erros, um deles com mensagem falsa.**
  - **O que mudou:** um código que não está na tabela oficial agora gera só
    `ibs-cclasstrib-existe`. Antes gerava também `ibs-cclasstrib-modelo`, cuja
    ação dizia "este código existe, mas não para o modelo desta nota".
  - **Documento oficial:** não se aplica (correção de mensagem; nenhuma regra
    fiscal mudou).
  - **O que mudou no código:** `fiscal_mcp/regras.py`, tipo `em_tabela`: regra
    com filtro (a de modelo) não julga mais existência, que fica com a regra
    irmã sem filtro. Testes em `tests/test_ibs_cbs.py` e
    `tests/test_tipos_de_regra.py`. Varredura dos 173 códigos da tabela em NF-e
    e NFC-e: nenhum achado mudou para código existente.
  - **Desde quando vale:** não se aplica — próxima versão.
