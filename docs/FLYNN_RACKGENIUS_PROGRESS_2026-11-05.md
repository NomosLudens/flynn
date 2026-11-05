# FLYNN — Progresso científico e operacional na RackGenius

**Data de consolidação:** 05/11/2026  
**Escopo:** missões 12 a 18, com contexto mínimo das etapas anteriores  
**Fase:** pesquisa independente, experimental e não comercial  
**Infraestrutura:** RackGenius, com apoio da iniciativa Genius Impact  
**Estado do projeto:** EM DESENVOLVIMENTO  
**Estado da residente:** OFFLINE; nenhuma residência contínua ou episódio canônico iniciado

> **Conclusão executiva.** O observatório público independente foi publicado e validado com uma amostra histórica verificável, sem acesso de escrita aos dados científicos. Ensaios instrumentais posteriores demonstraram resposta LIF à estimulação visual real sobre o mapeamento FlyWire FAFB v783. Contudo, a atividade não produziu disparos nos neurônios descendentes nem comandos motores. O ciclo causal percepção–rede neural–corpo continua **NÃO DEMONSTRADO**. Os resultados são experimentais, não sinais de residência ativa, aprendizagem, consciência ou comportamento autônomo.

## 1. Estatuto deste documento

Este é um **registro consolidado dos resultados e limites declarados nos relatórios de missão 12–18**, não a transcrição integral dos experimentos nem uma nova auditoria dos bancos originais. As verificações informadas abaixo são as executadas nas respectivas missões; não foram reexecutadas para esta atualização documental. A documentação primária e os artefatos científicos continuam em seus locais de proveniência. Não se publicam aqui SQLite, checkpoints, matrizes CSR, segredos, tokens, credenciais ou qualquer conteúdo que permita reconstruir dados científicos não autorizados para redistribuição.

O conectoma é derivado de **FlyWire FAFB v783**, sujeito ao aviso conservador de uso não comercial **CC BY-NC 4.0** e às divergências de metadados de origem já documentadas no projeto. O repositório de software conserva sua licença e seu histórico próprios. As expressões “cérebro”, “corpo” e “residente” são nomes de arquitetura e projeto, não alegações de equivalência biológica.

## 2. Linha do tempo verificável por missão

| Missão | Veredito reportado | Resultado material | Limite não superado |
| --- | --- | --- | --- |
| 12 — Proveniência científica | PARTIAL, com adendo posterior | Inventário de **20 bancos SQLite**, manifesto de caminhos, tamanhos, hashes e integridade; 19 instrumentais e um registro não classificado mantido em quarentena | Fechamento remoto dependia de resolver a identidade SSH |
| 13 — Identidade SSH e proveniência | **PASS** | Chave pública do cliente distinguida da chave de host; Ed25519 do servidor coincidiu com a entrada histórica confiável registrada sob IP público. Via Tailscale, os **20/20 bancos** coincidiram em caminho, tamanho e SHA-256 | Não implica rotação de chave nem autorização para alterar dados |
| 14 — Observatório real somente leitura | **PASS** | Serviço Python padrão, independente, em loopback; página LETHE e `GET /api/flynn/v2/public-observer` testados localmente e pelo túnel SSH privado; respostas históricas reais | Sem leitura do runtime neural, banco ou CSR pelo serviço; não é monitoramento neural ao vivo |
| 15 — Publicação do observatório | **PARTIAL** na preparação; publicação posteriormente confirmada | Publicação HTTPS em `https://flynn.nomosludens.ia.br/` pelo túnel Cloudflare existente `flynn-lethe-public`; DNS da zona pretendida corrigido; serviço persistente iniciado | A rota antiga de `lethe.nomosludens.ia.br` foi preservada, mas respondia **502**, pois sua origem `127.0.0.1:8201` não escutava |
| 16 — Clareza e aceitação da página | **PASS** | HTTPS 200 e API 200 no navegador real; `POST` retornou 405; linguagem da visualização corrigida, rollback preservado, geometria LETHE com **23 pontos e 30 conexões** | Sem pose nodal física pareada; exibição estrutural estática, não movimento observado |
| 17 — Causalidade neural instrumental | **PARTIAL** | Estímulo visual alcançou **11.118 alvos**; **11.165 spikes LIF**, incluindo **47 fora do conjunto visual**; checkpoint integrado no tick 400; SQLite passou em `integrity_check` | **Zero spikes nos 1.303 neurônios descendentes (DN)**; nenhum comando motor ou torque; propriocepção ainda não fechou ciclo |
| 18 — Propagação sináptica | **PARTIAL** | Grafo dirigido alcança **1.299 de 1.303 DN**; 47 neurônios/eventos extravisuais têm conexões diretas com alvos visuais; continuação real isolada avançou **40 → 60 ms**, com **22.997 spikes LIF adicionais** | Ainda **zero spikes DN** e nenhum comando motor; logs sem granularidade temporal suficiente para atribuir causalmente cada spike extravisual |

Os nomes e os vereditos de missão são mantidos como declarados, inclusive `PARTIAL` quando houve avanço científico real sem satisfazer o objetivo integral.

## 3. Proveniência, identidade e preservação

1. O manifesto científico local criado na Missão 12 relaciona **20 bancos** e constitui a referência de integridade da amostra publicada. A Missão 13 recuperou a conexão SSH estrita sem editar `known_hosts`, configuração SSH ou JSON científico.
2. O erro inicial de interpretação de fingerprints foi esclarecido: o fingerprint do **cliente** não deve ser comparado com o da **chave de host**. A identidade do servidor foi ancorada em uma entrada Ed25519 historicamente confiável; não se inferiu rotação.
3. Na Missão 14, os **20/20** bancos tiveram tamanhos e hashes conferidos antes e depois do ensaio privado; o manifesto permaneceu idêntico. O observatório não abre os bancos para responder às requisições públicas.
4. As Missões 17 e 18 produziram bancos e checkpoints **instrumentais isolados**. Na Missão 17, uma primeira execução foi interrompida por exigências de geração causal e memória virtual; seu banco incompleto foi preservado e não contado como resultado. Na Missão 18, duas tentativas interrompidas de configuração também foram preservadas. Bancos e checkpoints originais permaneceram sem alteração de hash nos controles reportados.
5. Não houve exclusão de dados científicos, promoção de ensaios instrumentais a episódio canônico nem início de residência contínua. O espaço livre informado na Missão 17 era cerca de **19,39 GiB**; trata-se de medida pontual, não prova de sustentabilidade de execução prolongada.

## 4. Observatório público e interpretação correta

**URL:** https://flynn.nomosludens.ia.br/  
**API:** `GET /api/flynn/v2/public-observer`  
**Fonte:** manifesto científico local com integridade validada, em vez de consulta direta aos bancos ou runtime.

O observatório foi implementado com a biblioteca padrão Python em serviço independente. Os ensaios HTTP reais da Missão 14 demonstraram acesso `GET`, `Cache-Control: no-store`, rejeição `405` para métodos de escrita e `404` para caminhos fora do escopo. Na publicação, a página e a API foram verificadas sobre HTTPS, e a resposta de escrita continuou bloqueada. Isso delimita o **contrato da interface**; não constitui uma auditoria de segurança abrangente.

O registro publicado é uma **amostra instrumental histórica**, com os marcadores explícitos:

| Campo | Valor documentado |
| --- | --- |
| `classification` | `HISTORICAL_INSTRUMENTAL` |
| `resident_status` | `OFFLINE` |
| `canonical_episode_status` | `NONE` |
| `continuous_residency` | `NO` |
| `fresh` | `false` |
| Tick neural | `800` |
| Tempo neural / mundo | `80 ms / 80 ms` |
| Spikes LIF / DN desta amostra | `0 / 0` |
| Pose nodal dinâmica pareada | `UNAVAILABLE` |

**Importante:** os **0 spikes** da página são valores **medidos naquela amostra histórica específica**, não a conclusão de que os ensaios instrumentais das Missões 17 e 18 foram silenciosos. Essas missões usaram experimentos separados e evocaram atividade LIF; não atualizaram a fonte pública nem criaram uma residente ativa.

A visualização LETHE expõe a **topologia estrutural** de 23 pontos e 30 conexões. Sem posições nodais dinâmicas verificadas e pareadas com o mesmo episódio, não atribui deslocamento, torque ou movimento. A correção textual da Missão 16 retirou um rótulo confuso e passou a explicar isso ao visitante.

O endereço antigo `lethe.nomosludens.ia.br` permanecia com regra preservada no túnel, mas a ausência de processo na origem antiga gerava `502`. Essa falha antiga não deve ser confundida com o funcionamento validado do novo observatório em `flynn.nomosludens.ia.br`.

## 5. Resultados neurocientíficos instrumentais

### 5.1 Entrada visual e resposta elétrica — Missão 17

O ensaio A/B integrado usou a **CSR FAFB v783 real** e uma **candidata experimental isolada** derivada da Missão 09. O estímulo luminoso instrumental, aplicado em escala completa, alcançou **11.118 alvos visuais** e produziu **11.165 spikes LIF**. Foram registrados **47 spikes fora da população visual estimulada**. No mesmo ensaio, **nenhum dos 1.303 DN** disparou. Logo, não foi observado comando motor nem torque. O readout do corpo Pinocchio foi registrado, mas **não gerou entrada proprioceptiva no LIF**.

Esse experimento comprova **responsividade elétrica ao protocolo instrumental**, não propagação sináptica individual comprovada, resposta motora, comportamento espontâneo ou residência.

### 5.2 Alcance anatômico e continuidade real — Missão 18

A análise de alcance do grafo dirigido encontrou caminhos dos alvos visuais para **1.299/1.303 DN (99,69%)**, dentro do mapeamento e critério usados. Para os quatro DN restantes, nenhum caminho foi identificado nessa análise; isso não autoriza concluir, sem avaliação adicional, que sejam biologicamente desconectados.

Os **47 spikes extravisuais** correspondem a elementos com conexões visuais diretas, mas o registro existente não tem os ticks individuais necessários para demonstrar a sequência temporal e a causa de cada evento. Trata-se de **compatibilidade estrutural com propagação**, ainda não de prova causal evento a evento.

Uma continuação real isolada, do checkpoint em **40 ms até 60 ms**, gerou **mais 22.997 spikes LIF**. Continuaram **zero spikes DN** e **nenhum comando motor**. O experimento descarta a hipótese simples de uma rede totalmente silenciosa nesse período, mas **não estabelece** se o silêncio DN resulta de ausência de corrente, integração sub-limiar, atrasos, parâmetros cientificamente justificados ou defeito de implementação.

### 5.3 Onde a cadeia causal está demonstrada

| Elo | Situação em 05/11/2026 |
| --- | --- |
| Protocolo luminoso → alvos visuais | **Observado** no ensaio instrumental |
| Alvos estimulados → atividade LIF | **Observado** como resposta de população |
| Atividade visual → origem causal dos 47 spikes extravisuais | **Não demonstrada** evento a evento |
| Caminhos anatômicos dirigidos → DN | **Identificados** para 1.299 DN |
| Correntes/eventos sinápticos efetivamente entregues a cada DN | **Ainda não medidos de forma conclusiva** |
| Disparos DN | **Não observados** (0/1.303) |
| DN → comando motor → torque → movimento | **Não demonstrado** no ensaio |
| Corpo Pinocchio → sinal proprioceptivo → LIF | **Não demonstrado** no ensaio |
| Ciclo causal cérebro–corpo fechado | **NÃO DEMONSTRADO** |

Não há base para diagnosticar uma única causa. A conectividade estrutural é condição de possibilidade, mas não é sinônimo de transmissão funcional.

## 6. Decisões, limites e próximos passos

**Decisões preservadas:**

- Manter a residente **OFFLINE**, sem criar episódio canônico, iniciar residência ou simular atividade para melhorar a aparência do painel.
- Manter o observatório público **somente de leitura** e alimentado pela amostra histórica imutável. Não misturar resultados de episódios instrumentais distintos nem rotular valores históricos como telemetria atual.
- Preservar o conectoma e o material científico de origem; não ajustar pesos, limiares, sinais ou regras motoras apenas para induzir disparos ou movimentos.
- Não publicar bancos, snapshots, checkpoints, arrays CSR, segredos, material de autenticação ou tokens no GitHub ou no Drive como parte desta consolidação. Preservar o WIP e relatórios originais.
- Não inferir consciência, intenção, aprendizagem ou equivalência biológica a partir de atividade LIF isolada.

**Próximo experimento proposto, não executado — Missão 19:** rastrear, em um conjunto pequeno e representativo de caminhos do grafo real, (1) spikes pré-sinápticos com tempo individual, (2) eventos e pesos sinápticos efetivamente encaminhados, (3) correntes e potenciais de membrana nos neurônios intermediários e DN e (4) atrasos/limiares/unidades do modelo. Distinguir **ausência de entrada**, **entrada sub-limiar**, **atraso temporal** e **falha de transporte/integração no código**. Um ensaio temporal adicional só se justifica com hipótese e orçamento de recursos explícitos. Sem retocar parâmetros para forçar o resultado.

**Pendências independentes:** fechar o caminho de propriocepção com prova causal; resolver ou arquivar a origem legada do hostname `lethe` sem afetar o novo observatório; manter a preservação externa dos dados científicos como decisão separada. Nenhuma dessas pendências autoriza substituição silenciosa do protocolo neural.

## 7. Localização dos relatórios primários e rastreabilidade

Os seguintes nomes identificam relatórios locais mantidos no projeto. Esta consolidação não declara que seus arquivos completos tenham sido incorporados ao GitHub ou Drive:

- `FLYNN_RACKGENIUS_SCIENTIFIC_PROVENANCE_12.md` e `FLYNN_RACKGENIUS_SCIENTIFIC_PROVENANCE_12.json` — inventário e manifesto.
- `FLYNN_RACKGENIUS_SSH_IDENTITY_AND_PROVENANCE_13.md` — host SSH e 20 bancos.
- Relatório da Missão 14 — implementação e aceitação do observatório somente leitura (nome a confirmar nos arquivos locais).
- `FLYNN_RACKGENIUS_PUBLIC_OBSERVER_RELEASE_15.md` — staging, autorização e publicação HTTPS.
- Relatório da Missão 16 — clareza da topologia estrutural e aceite da página (nome a confirmar nos arquivos locais).
- `FLYNN_RACKGENIUS_NEURAL_CAUSALITY_17.md` — estímulo visual e ensaio A/B integrado.
- `FLYNN_RACKGENIUS_SYNAPTIC_PROPAGATION_18.md` — alcance dirigido e continuação até 60 ms.

Arquivos históricos versionados e arquitetura: [`docs/MAPA_DE_PERCURSO_FLYNN.md`](https://github.com/NomosLudens/flynn/blob/master/docs/MAPA_DE_PERCURSO_FLYNN.md) e [README do projeto](https://github.com/NomosLudens/flynn). Os relatórios técnicos históricos continuam preservados. A etapa concluída em 26/10/2026 e os novos ensaios RackGenius são **fases experimentais distintas**; seus episódios não podem ser fundidos retrospectivamente.

---

**Síntese responsável:** a plataforma pública de observação histórica funciona, e a rede neural instrumental responde a estímulos visuais na fonte FAFB v783. **Não foi comprovada transmissão funcional até os DN, atuação, propriocepção de retorno, ciclo corporal fechado, residência contínua ou consciência.**
