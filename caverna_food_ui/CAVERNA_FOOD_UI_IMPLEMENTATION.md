# Caverna Food UI — Gate único

Host: `max`

## Escopo implementado

- A Caverna ganhou uma camada principal factual `FLYNN AGORA`, alimentada por `/api/caverna/state` e pela janela residente de trajetória.
- A camada principal mostra estado corporal, energia, necessidade alimentar, capacidade corporal, estado único do SWEET, distância canônica e `CONTACT`.
- O menu abre `DETALHES TÉCNICOS`; o drawer mantém os cards do Umwelt, controles, diário e um bloco `<details>` com `q`, `qdot`, atividade de DNs, posições, raio, contato, consumo, IDs e proveniência.
- O diário causal agora mostra data e hora locais de Brasília (`America/Sao_Paulo`) e um resumo factual curto. Cada evento pode ser expandido para os valores técnicos e a proveniência.
- Estados de recurso apresentados pela interface são mutuamente exclusivos: `AUSENTE`, `OFERTADO`, `DISPONÍVEL`, `CONTATO` ou `CONSUMIDO`.
- O corpo continua sendo desenhado e atualizado a partir do estado Pinocchio residente; nenhum alvo, navegação ou atração foi adicionado.

## Fechamento físico

`ContinuousWorldEngine.observe_body()` continua sendo o único dono da decisão de contato/consumo:

```text
distance(body.position, resource.position) <= resource.contact_radius
  -> CONTACT
  -> consumed_at + available=false
  -> HomeostasisEngineV2.replenish()
```

Foi adicionada uma guarda explícita para que um objeto com `consumed_at` nunca aplique a reposição duas vezes em ticks ou observações repetidas. O HTTP de oferta apenas publica o recurso no Umwelt; não injeta estímulo neural, não movimenta o corpo e não consome energia.

## Integridade

Não houve alteração de connectoma, plasticidade, ZeroClaw, política de alvo, pathfinding, atração, reward ou treino.
