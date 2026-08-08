# ADR-0005 — Não custodiar certificado digital de cliente

- **Data:** 06/08/2026
- **Status:** aceita

## Contexto

O modo gerenciado seria mais fácil de vender: o cliente não instala nada. Só que
para assinar documento fiscal é preciso ter o certificado — e o A1 é um arquivo
copiável que **é a identidade jurídica da empresa**.

Quem tem o A1 e a senha pode emitir nota, assinar contrato e agir como a empresa.
Vazamento é comprometimento total e silencioso: não há como detectar cópia.

## Decisão

**Não custodiar certificado de cliente enquanto não houver estrutura para isso.**

O modo gerenciado, quando existir, roda com o componente de assinatura na infra
do cliente: nós operamos monitoramento, atualização e suporte; a chave privada
nunca sai de lá.

## Justificativa

**1. Assimetria de risco.** O ganho é comodidade de venda. A perda potencial é
uma empresa tendo notas emitidas em seu nome — com consequência fiscal, cível e
criminal. Não é risco proporcional para um projeto em fase inicial.

**2. Custódia exige estrutura que ainda não existe.** No mínimo: HSM ou KMS com
chave por cliente, segregação real, trilha de auditoria de cada assinatura,
rotação, resposta a incidente, contrato específico e provavelmente seguro. Cada
um desses itens é projeto próprio.

**3. Vira argumento de venda.** "Seu certificado não sai da sua infra" é
diferencial num mercado onde o padrão é entregar o `.pfx` para o fornecedor.

**4. Reduz superfície regulatória.** Sem custódia, nosso papel sob a LGPD e a
responsabilidade sobre a assinatura ficam muito mais simples de delimitar.

## Consequências

- O modo totalmente gerenciado "sem instalar nada" **não existe** por ora. Isso
  custa vendas, e é aceito conscientemente.
- Exige que o componente auto-hospedado seja fácil de operar — se for penoso, a
  decisão vira obstáculo comercial em vez de diferencial.
- A1 em token A3 permanece fora de escopo no gerenciado, por exigir hardware
  presente.

## Revisão

Revisitar quando houver: receita que justifique a estrutura, demanda repetida e
explícita de clientes dispostos a pagar mais por custódia, e capacidade de operar
resposta a incidente. **Nunca revisitar só porque facilitaria fechar um contrato.**
