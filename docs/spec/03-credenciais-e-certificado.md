# Spec 03 — Certificado digital e credenciais

> Este é o documento mais sério do repositório. O certificado digital de uma
> empresa **é a identidade jurídica dela**. Quem tem o A1 emite nota, assina
> documento e responde como se fosse a empresa.

## O que é o certificado

| Tipo | Formato | Implicação |
|---|---|---|
| **A1** | arquivo `.pfx` / `.p12` + senha, validade 1 ano | copiável — quem tem o arquivo e a senha é a empresa |
| **A3** | token USB ou cartão, validade até 3 anos | não exportável; exige presença física ou HSM |

Como A1 é um arquivo, **vazamento é comprometimento total e silencioso**. Não há
como saber que foi copiado.

## Postura do projeto

### Modo local e auto-hospedado

O certificado **nunca sai da máquina de quem usa**. O servidor lê do caminho
configurado, mantém em memória o tempo da operação e não persiste.

Regras:

- caminho e senha vêm de variável de ambiente ou cofre — **nunca** de parâmetro
  de ferramenta MCP, senão o certificado entra no contexto do agente e vai parar
  em log de conversa;
- senha nunca é logada, nem em nível debug;
- o servidor recusa iniciar se o arquivo estiver com permissão frouxa;
- avisa quando faltarem menos de 30 dias para vencer — certificado vencido
  derruba emissão no pior momento.

### Modo gerenciado

Ver [ADR-0005](../adr/0005-certificado-nunca-transita.md). Resumo: **não custodiar
certificado de cliente enquanto não houver estrutura para isso**. É risco
desproporcional para um projeto em fase inicial — e o dia em que houver, exige
KMS/HSM, segregação por cliente, trilha de auditoria de cada assinatura, contrato
específico e seguro.

Enquanto isso, o modo gerenciado é oferecido **sem** custódia: o cliente hospeda o
componente que assina; nós operamos o resto.

## O que nunca entra no contexto do agente

Um agente loga conversa, e conversa vaza. Nunca podem aparecer em parâmetro,
retorno ou mensagem de erro:

- conteúdo ou caminho absoluto do certificado;
- senha do certificado;
- token de acesso de prefeitura;
- XML assinado completo por padrão (contém dados pessoais de destinatário).

O XML sai por referência a arquivo local, não inline.

## LGPD

Documento fiscal carrega dado pessoal: CPF do destinatário, nome, endereço.
Consequências práticas:

- **minimização** — o resumo devolvido pelas ferramentas traz o mínimo; dado
  completo exige pedido explícito;
- **retenção** — o servidor não persiste documento; quem persiste é o cliente,
  que é o controlador;
- **papéis** — no modo auto-hospedado somos fornecedor de software, não operador
  de dados. No gerenciado, seríamos operador, com contrato correspondente. Essa
  distinção precisa estar escrita antes do primeiro cliente pago.

## Fronteira de responsabilidade

Escrito aqui para virar cláusula de contrato depois:

| Nosso | Do cliente |
|---|---|
| a integração funcionar conforme o leiaute vigente | a informação declarada estar correta |
| traduzir a rejeição da SEFAZ | classificação fiscal, CFOP, CST, alíquota |
| avisar quando o leiaute mudar | guarda e validade do certificado |
| manter o servidor atualizado | obrigação acessória e apuração |

**Erro de integração é nosso. Erro de informação é do cliente.** Sem essa linha
clara, o primeiro problema fiscal vira discussão de responsabilidade.
