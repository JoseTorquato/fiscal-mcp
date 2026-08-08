# ADR-0007 — Homologação por padrão; produção exige opt-in explícito

- **Data:** 06/08/2026
- **Status:** aceita

## Contexto

O servidor é operado por um **agente de IA**, não por uma pessoa que leu a
documentação. Agente erra, alucina parâmetro e repete chamada em loop de retry.

No fiscal, o erro não é um registro errado no banco: é **documento com efeito
fiscal e jurídico emitido para a Receita**. Cancelar tem prazo, exige
justificativa e nem sempre é possível.

Este é o risco mais alto do produto inteiro — e nós mesmos medimos, no Cilada,
agentes confirmando pagamento inexistente e obedecendo a instrução injetada em
campo de cadastro.

## Decisão

1. **`homologacao` é o padrão** em toda ferramenta com efeito fiscal.
2. Apontar para produção exige **variável de ambiente explícita** no servidor
   (não parâmetro de ferramenta) **e** `ambiente="producao"` na chamada.
3. Operações irreversíveis exigem parâmetro de confirmação dedicado
   (`confirmo_cancelamento=true`).
4. Toda operação em produção é registrada com quem chamou, quando e com quais
   parâmetros.
5. A descrição da ferramenta declara na primeira linha se é irreversível.

O agente sozinho **não consegue** promover para produção: falta a variável de
ambiente, que é decisão humana de implantação.

## Justificativa

**Duas chaves, dois donos.** Ambiente de execução é decisão de quem opera;
parâmetro é decisão de quem chama. Exigir os dois significa que injeção de prompt
não basta para emitir nota real.

**O padrão precisa ser o seguro.** Quem esquece de configurar acaba em
homologação — o erro barato. O inverso seria inaceitável.

**Atrito proposital.** `confirmo_cancelamento=true` não impede um agente
determinado, mas impede o acidente, que é o caso comum.

## Consequências

- Fricção real para quem quer produção rápido. É intencional e precisa estar
  clara na documentação para não virar percepção de bug.
- Exige que homologação seja boa o suficiente para desenvolver de verdade — e
  ela é instável, então o servidor precisa distinguir "SEFAZ de homologação fora
  do ar" de "seu documento está errado".
- Log de produção com parâmetros toca dado pessoal: retenção e minimização
  conforme [spec 03](../spec/03-credenciais-e-certificado.md).

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Produção como padrão, homologação opcional | inverte o custo do erro |
| Só parâmetro de ferramenta | agente controla o parâmetro; injeção de prompt bastaria |
| Confirmação por callback humano | inviável em automação; empurraria o usuário a desligar |
