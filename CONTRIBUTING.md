# Contribuir

Obrigado por considerar. Antes de qualquer coisa, a regra que não tem exceção:

## ⚠️ Nunca envie dado fiscal real identificável

**Pull request com XML que contenha CNPJ, CPF, razão social, endereço, inscrição
estadual, chave de acesso real ou assinatura digital de terceiro é fechado sem
merge.** Não é rigor burocrático: é dado pessoal e sigilo fiscal, e uma vez
publicado no histórico do git não sai mais.

Isso vale para issue, comentário e print de tela também.

### Como anonimizar

Troque tudo que identifica, preserve tudo que é fiscal:

| Trocar | Preservar |
|---|---|
| CNPJ, CPF (use documentos fictícios com DV válido) | NCM, CFOP, CST, `cClassTrib` |
| Razão social, nome fantasia, nome de pessoa | alíquotas, bases de cálculo, valores |
| Endereço, CEP, telefone, e-mail | quantidade de itens e estrutura do XML |
| Inscrição estadual e municipal | versão do leiaute |
| Chave de acesso (recalcule o DV) | códigos de rejeição recebidos |
| `infCpl`, `obsCont`, `xProd` com dado de cliente | |
| Bloco `<Signature>` inteiro | |

O que importa para uma regra fiscal é a **estrutura** e os **códigos**, nunca
quem emitiu. Se o XML anonimizado ainda reproduz o problema, ele serve.

### O script faz isso para você

```bash
python scripts/anonimizar.py nota.xml -o anonimizada.xml
python scripts/anonimizar.py anonimizada.xml --conferir   # procura resíduo do original
```

Ele troca CNPJ e CPF por documentos fictícios **com DV válido e estáveis** (o
mesmo documento de entrada vira sempre o mesmo de saída, então a relação entre
emitente e destinatário se mantém), recalcula o DV da chave de acesso, remove
assinatura, protocolo e comentários — emissor comercial carimba nome de cliente
em comentário de XML — e preserva NCM, CFOP, CST, `cClassTrib`, alíquotas e
valores.

Quando ele não tem certeza, **ele avisa em vez de adivinhar**: no Id da NFS-e,
por exemplo, o leiaute não está confirmado, então ele só mexe se encontrar o
documento sem ambiguidade. Leia os avisos antes de anexar o arquivo.

**`--conferir` é a rede de segurança**, não a garantia. Rode, mas confira você
também: o script não sabe que o `xProd` do item 3 tem o nome do seu cliente.

## O que mais ajuda, em ordem

1. **XML anonimizado que a ferramenta validou errado.** Falso positivo é a única
   falha que destrói a confiança de forma irreversível, e é o que mais precisamos
   descobrir cedo. Um relato desses vale mais que dez features.
2. **Código de rejeição que você levou** e não está no catálogo, com o texto
   exato devolvido pela SEFAZ.
3. **Leitura de nota técnica em fonte primária** — especialmente a seção de
   regras de validação da NT 2025.002-RTC.
4. **Regra nova** em `regras/`, com as duas fixtures (ver abaixo).

## Escrever uma regra

Regras são dados, não código. Uma regra nova é uma entrada em YAML dentro de
`regras/`, não uma função em Python.

```yaml
- id: ibs-cst-existe
  tipo: em_tabela
  escopo: item              # documento (padrão) | item
  severidade: erro          # erro | aviso | informacao
  campo: imposto/IBSCBS/CST
  tabela: cst-cclasstrib
  coluna: cst
  mensagem: CST de IBS/CBS não existe na tabela oficial
  referencia: Tabela de Classificação Tributária · SVRS
  acao: >
    Use um dos 18 CST publicados.
```

### Contratos que a revisão vai cobrar

- **Duas fixtures.** Uma que a regra reprova e uma que ela aprova. Sem as duas a
  regra não entra: regra com só a fixture de reprovação pode estar acusando o
  mundo inteiro, e regra com só a de aprovação pode estar morta.
- **`acao` obrigatória.** Quem lê é um agente que vai tentar de novo — erro sem
  ação vira loop de retry ou nota duplicada. Um teste falha sem isso.
- **`referencia` à fonte.** De onde veio a regra: leiaute, nota técnica, tabela.
- **Nenhum código numérico de rejeição** sem leitura humana da nota técnica
  vigente. Descrever o problema sem o número é sempre permitido e quase sempre
  suficiente. Citar número errado é pior que não citar.
- **Campo ausente devolve `None`.** Obrigatoriedade é responsabilidade de uma
  regra `existe` dedicada, com severidade própria.
- **Regra que ainda não estabilizou nasce como `aviso`**, com bloco `vigencia` e
  `reavaliar_em` em data concreta. Um teste falha quando a data passa.

## Rodar os testes

```bash
pip install -e ".[servidor,xsd]" pytest
pytest -q
```

Se você mexeu em regra, o teste que mais importa é
`test_nota_correta_passa_sem_nenhum_erro`: uma nota válida e completa não pode
gerar um erro sequer.

## Atualizar a tabela oficial

O CI **nunca** baixa a tabela — indisponibilidade da SVRS não pode quebrar o
build de quem depende do pacote. A atualização é ato deliberado:

```bash
python scripts/baixar_tabelas.py   # confere o diff, atualiza o sha256, abre PR
```

Dado oficial mudando é notícia, não rotina: leia o diff antes de commitar e
registre a data de detecção no `CHANGELOG.md`.

## Estilo

- Código, comentários e mensagens em **português brasileiro**.
- Comentário explica **por quê**, não o quê. Registre a decisão e a armadilha,
  não narre a linha.
- Sem dependência nova no núcleo. `lxml` e `pyyaml` bastam; o resto é extra.

## O que este projeto não vai fazer

Emissão, assinatura, transmissão e custódia de certificado estão **suspensos com
gatilho escrito** — ver [ADR-0011](docs/adr/0011-validacao-e-o-produto.md). PR
nessa direção será recusado, não por qualidade, mas por escopo. Se você acha que
o gatilho disparou, abra uma issue argumentando em vez de um PR.
