# ADR-0002 — Open core: servidor aberto, manutenção e operação pagas

- **Data:** 06/08/2026
- **Status:** aceita

## Contexto

Precisamos de adoção (o comprador descobre pelo dev) e de receita recorrente. Se
abrirmos tudo, não há o que vender; se fecharmos tudo, ninguém descobre — e
concorrente aberto ocupa o espaço.

## Decisão

Open core com a fronteira desenhada assim:

| Camada | Aberto (MIT) | Pago |
|---|---|---|
| Servidores MCP e ferramentas | ✅ | |
| Validação local e tradução de erro | ✅ | |
| Adapters de UF para NF-e | ✅ | |
| Adapters municipais de NFS-e | os mais comuns | **cobertura ampla mantida** |
| Atualização por nota técnica | quando sai, sai para todos | **compromisso de prazo** |
| Suíte diária contra homologação | | ✅ |
| Telemetria agregada de rejeição | | ✅ |
| Status e alerta de webservice | | ✅ |

**O que se vende não é código: é compromisso, cobertura e operação.**

## Regra de arquitetura inegociável

Nada que sustente a assinatura pode ser distribuído dentro do pacote aberto. Se
a cobertura municipal ampla viajar no `pip install`, a receita recorrente vaza no
primeiro download.

Concretamente: adapters mantidos e dados operacionais são **servidos**, não
embarcados. O pacote aberto sabe pedir; o serviço sabe responder.

> Esta regra foi aprendida no Cilada, onde o mesmo raciocínio vale para o corpus
> privado de ataques.

## Justificativa

**Precedente:** OpenVAS e OWASP ZAP são abertos, e auditoria de segurança custa
dezenas de milhares. A ferramenta vira commodity; a operação e a garantia não.

**No fiscal é ainda mais nítido:** o servidor aberto emite nota hoje. Em três
meses, quando sair nota técnica, ele para de emitir — a menos que alguém atualize.
Quem não quer ser esse alguém, assina.

**O aberto é o funil, não o vazamento.** Quem rodar sozinho descobre que
funciona e descobre o custo de manter. Os dois levam à mesma conversa.

## Consequências

- Precisa existir versão aberta genuinamente útil, senão vira *open washing* e
  queima a credibilidade — que é o ativo principal.
- A fronteira será testada por usuários pedindo o que é pago; precisa de resposta
  pronta e honesta.
- O serviço tem que existir como serviço desde cedo: se nascer como biblioteca,
  não dá para fechar depois sem quebrar quem já usa.

## Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| Tudo fechado | sem descoberta; concorrente aberto ocupa o nicho |
| Tudo aberto + só consultoria | receita não escala e depende de hora |
| Licença restritiva (BUSL) | mata adoção, que é o objetivo da camada aberta |
| SaaS puro, sem código aberto | dev não avalia sem rodar; ciclo de venda cresce |
