# FLYNN — Progresso científico e operacional na RackGenius

**Data de consolidação:** 05/11/2026  
**Escopo:** missões 12 a 21, com contexto mínimo das etapas anteriores  
**Fase:** pesquisa independente, experimental e não comercial  
**Infraestrutura:** RackGenius, com apoio da iniciativa Genius Impact  
**Estado do projeto:** EM DESENVOLVIMENTO  
**Estado da residente:** OFFLINE; nenhuma residência contínua ou episódio canônico iniciado

> **Conclusão executiva.** O observatório público independente foi publicado e validado com uma amostra histórica verificável, sem acesso de escrita aos dados científicos. Ensaios instrumentais posteriores demonstraram resposta LIF à estimulação visual real sobre o mapeamento FlyWire FAFB v783. As Missões 19 e 20 acrescentaram evidência temporal de **eventos sinápticos efetivamente entregues e de respostas de membrana sub-limiares em DN selecionados**, e a Missão 21 comprovou, em cinco caminhos positivos pré-registrados, um relé compartilhado que recebeu **64 eventos mas não disparou**. Ainda não houve **spikes DN, comandos motores ou retorno proprioceptivo efetivo**. O ciclo causal percepção–rede neural–corpo continua **NÃO DEMONSTRADO**. Os resultados são experimentais, não sinais de residência ativa, aprendizagem, consciência ou comportamento autônomo.

## 1. Estatuto deste documento

Este é um **registro consolidado dos resultados e limites declarados nos relatórios de missão 12–21**, não a transcrição integral dos experimentos nem uma nova auditoria dos bancos originais. As verificações informadas abaixo são as executadas nas respectivas missões; não foram reexecutadas para esta atualização documental. A documentação primária e os artefatos científicos continuam em seus locais de proveniência. Não se publicam aqui SQLite, checkpoints, matrizes CSR, segredos, tokens, credenciais ou qualquer conteúdo que permita reconstruir dados científicos não autorizados para redistribuição.

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
| 19 — Traçado eletrofisiológico | **PASS**, apenas para o recorte diagnóstico | Cinco caminhos dirigidos instrumentados, três DN observados; **15 eventos agendados, 14 entregues na janela 40–60 ms**, um fora da janela; rastreamento temporal de spikes, eventos e potenciais de membrana | Integração DN **sub-limiar**, sem spikes DN; resultados não extrapoláveis aos 1.303 DN, nem equivalentes a correntes biológicas medidas |
| 20 — Drive excitatório descendente | **PASS**, apenas para 12 DN amostrados | Amostra pré-selecionada de **12 DN**, 6.467 arestas aferentes; **9 eventos reais entregues a três DN** (4 positivos, 5 negativos), com resposta de membrana registrada | **Nove DN sem eventos aferentes na janela**; zero spikes DN; causas globais do silêncio descendente e comando motor permanecem abertas |
| 21 — Relés a montante | **PASS**, limitado a **7 caminhos pré-registrados** | Cinco relés com entrada e resposta de membrana, quatro com spikes; **172 eventos agendados, 166 entregues na janela**. Nos cinco caminhos positivos, relé compartilhado recebeu **64 eventos** mas não disparou | **0 eventos nos 5 DN positivos**, cinco eventos nos DN dos dois controles, **0 spikes DN**; resultado não generalizável à população inteira |

Os nomes e os vereditos de missão são mantidos como declarados, inclusive `PARTIAL` quando houve avanço científico real sem satisfazer o objetivo integral.

## 3. Proveniência, identidade e preservação

1. O manifesto científico local criado na Missão 12 relaciona **20 bancos** e constitui a referência de integridade da amostra publicada. A Missão 13 recuperou a conexão SSH estrita sem editar `known_hosts`, configuração SSH ou JSON científico.
2. O erro inicial de interpretação de fingerprints foi esclarecido: o fingerprint do **cliente** não deve ser comparado com o da **chave de host**. A identidade do servidor foi ancorada em uma entrada Ed25519 historicamente confiável; não se inferiu rotação.
3. Na Missão 14, os **20/20** bancos tiveram tamanhos e hashes conferidos antes e depois do ensaio privado; o manifesto permaneceu idêntico. O observatório não abre os bancos para responder às requisições públicas.
4. As Missões 17 a 21 utilizaram evidências e continuações **instrumentais isoladas**. Na Missão 17, uma primeira execução foi interrompida por exigências de geração causal e memória virtual; seu banco incompleto foi preservado e não contado como resultado. Na Missão 18, duas tentativas interrompidas de configuração também foram preservadas. As Missões 19 a 21 rastrearam a mesma janela de 40–60 ms em análises diagnósticas, sem alteração de parâmetros científicos nem promoção de episódios a canônicos. Bancos e checkpoints originais permaneceram sem alteração de hash nos controles reportados.
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

**Importante:** os **0 spikes** da página são valores **medidos naquela amostra histórica específica**, não a conclusão de que os ensaios instrumentais das Missões 17 a 21 foram silenciosos. Essas missões usaram experimentos separados e evocaram atividade LIF e eventos sinápticos locais; não atualizaram a fonte pública nem criaram uma residente ativa.

A visualização LETHE expõe a **topologia estrutural** de 23 pontos e 30 conexões. Sem posições nodais dinâmicas verificadas e pareadas com o mesmo episódio, não atribui deslocamento, torque ou movimento. A correção textual da Missão 16 retirou um rótulo confuso e passou a explicar isso ao visitante.

O endereço antigo `lethe.nomosludens.ia.br` permanecia com regra preservada no túnel, mas a ausência de processo na origem antiga gerava `502`. Essa falha antiga não deve ser confundida com o funcionamento validado do novo observatório em `flynn.nomosludens.ia.br`.

## 5. Resultados neurocientíficos instrumentais

### 5.1 Entrada visual e resposta elétrica — Missão 17

O ensaio A/B integrado usou a **CSR FAFB v783 real** e uma **candidata experimental isolada** derivada da Missão 09. O estímulo luminoso instrumental, aplicado em escala completa, alcançou **11.118 alvos visuais** e produziu **11.165 spikes LIF**. Foram registrados **47 spikes fora da população visual estimulada**. No mesmo ensaio, **nenhum dos 1.303 DN** disparou. Logo, não foi observado comando motor nem torque. O readout do corpo Pinocchio foi registrado, mas **não gerou entrada proprioceptiva no LIF**.

Esse experimento comprova **responsividade elétrica ao protocolo instrumental**, não propagação sináptica individual comprovada, resposta motora, comportamento espontâneo ou residência.

### 5.2 Alcance anatômico e continuidade real — Missão 18

A análise de alcance do grafo dirigido encontrou caminhos dos alvos visuais para **1.299/1.303 DN (99,69%)**, dentro do mapeamento e critério usados. Para os quatro DN restantes, nenhum caminho foi identificado nessa análise; isso não autoriza concluir, sem avaliação adicional, que sejam biologicamente desconectados.

Os **47 spikes extravisuais** correspondem a elementos com conexões visuais diretas, mas o registro existente não tem os ticks individuais necessários para demonstrar a sequência temporal e a causa de cada evento. Trata-se de **compatibilidade estrutural com propagação**, ainda não de prova causal evento a evento.

Uma continuação real isolada, do checkpoint em **40 ms até 60 ms**, gerou **mais 22.997 spikes LIF**. Continuaram **zero spikes DN** e **nenhum comando motor**. O experimento descarta a hipótese simples de uma rede totalmente silenciosa nesse período, mas **não estabelecia naquele estágio** se o silêncio DN resultava de ausência de entrada, integração sub-limiar, atrasos, parâmetros do modelo ou defeito de implementação. As Missões 19 e 20 investigaram parte dessas alternativas em recortes limitados.

### 5.3 Eventos sinápticos e potenciais em caminhos selecionados — Missão 19

Um traçado instrumental real, partindo do checkpoint no **tick 400 (40 ms)** até o **tick 600 (60 ms)**, examinou **cinco caminhos dirigidos** da CSR FAFB v783: três diretos e dois com três arestas. **Três DN** estiveram no escopo da leitura eletrofisiológica. Dos **15 eventos sinápticos agendados** nas arestas instrumentadas, **14 foram efetivamente entregues** dentro da janela; o último estava agendado para o **tick 615**, fora dela. Para os eventos selecionados, não foi constatada perda no transporte nem discordância no ordenamento temporal do buffer.

Um caminho visual → relé → relé → DN mostrou sequência temporal de spikes/eventos, com a **última contribuição de sinal operacional negativo** (`signed_count = -1`) entregue no **tick 563**. O termo calculado de contribuição no modelo foi **−0,275 mV**, e o maior potencial DN observado no recorte foi cerca de **−51,7783472 mV**, abaixo do limiar de disparo **−45 mV** (diferença aproximada de **6,7783472 mV**). **Nenhum DN disparou**. A ordenação de eventos não prova que cada spike em um relé tenha sido causado exclusivamente pelo evento específico traçado: outros aferentes podem contribuir.

Parâmetros operacionais observados: passo `dt = 0,1 ms`; repouso/reset `−52 mV`; disparo para `v > −45 mV`; `tau_m = 20 ms`; `tau_syn = 5 ms`; refratariedade `2,2 ms`; atraso sináptico de `1,8 ms` (**18 ticks**). A escala `0,275 mV × signed_count` e os termos de contribuição são **construções de voltagem do modelo LIF**, **não correntes biológicas medidas**, nem pesos fisiológicos validados. O veredito **PASS** refere-se ao êxito diagnóstico e à rastreabilidade desses caminhos, não ao fechamento do ciclo sensório-motor.

### 5.4 Drive aferente nos DN e silêncio dos relés — Missão 20

A Missão 20 pré-selecionou **12 dos 1.303 DN**, incluindo candidatos com alta pontuação estrutural positiva e controles mistos/inibitórios. Rastreou **6.467 arestas aferentes** oriundas de **5.265 candidatos pré-sinápticos**. Na continuação real de **40–60 ms**, **nove eventos** chegaram efetivamente a **três DN**: **quatro contribuições operacionais positivas** e **cinco negativas**. Dois DN receberam contribuições de sinais mistos em tempos distintos; um recebeu apenas negativas. **Isso não demonstra cancelamento simultâneo nem inibição fisiológica medida.**

Os **outros nove DN não receberam nenhum evento aferente durante a janela**, apesar de alguns possuírem caminhos estruturais excitadores de duas arestas com pontuação elevada. Os **neurônios de relé desses caminhos não dispararam** no recorte observado, impedindo a chegada do último evento ao DN. O maior potencial DN observado foi **−51,77834721116443 mV**, ainda **6,77834721116443 mV** abaixo do limiar de −45 mV. Uma contribuição positiva local máxima reportada foi apenas cerca de **+0,00449890 mV**, como termo de voltagem do modelo, não corrente biológica. **Zero spikes DN**, zero comando motor.

Todos os **nove eventos aferentes** chegaram com o atraso configurado de **18 ticks**; não houve divergência de agendamento identificada nesse recorte. O replay instrumental reproduziu os frames de **50 ms (11.552 spikes LIF)** e **60 ms (11.445 spikes LIF)**, ambos sem spikes DN. Os parâmetros permaneceram inalterados. O banco e checkpoint de origem mantiveram seus hashes, cerca de **19,08 GiB** permaneciam livres na medição e a residente continuou offline, com observatório e túnel ativos. O veredito **PASS** refere-se à amostra diagnóstica de 12 DN; **não resolve a causa do silêncio nos 1.303 DN**.

### 5.5 Primeiro elo sem spike nos caminhos positivos — Missão 21

A Missão 21 rastreou **sete caminhos pré-registrados**: cinco positivos e dois controles. Foram inspecionados **cinco relés**, todos com entrada e resposta de membrana, dos quais **quatro apresentaram spikes**. O traço registrou **172 eventos agendados**; **166 foram entregues dentro da janela**, enquanto **seis venciam a partir do tick 600**, não configurando perdas dentro da janela.

Nos **cinco caminhos positivos**, as origens dispararam e os eventos chegaram a um **relé compartilhado**. Ele recebeu **64 eventos sinápticos**, apresentou resposta de membrana e **não disparou**. Portanto, **nenhum evento chegou aos cinco DN correspondentes**. O primeiro elo sem resposta observada foi a **saída em spike do relé compartilhado**. A causa matemática específica de sua integração sub-limiar ainda precisa ser examinada.

No **controle positivo**, o sinal percorreu relés ativos e chegou a um DN, que permaneceu sub-limiar. No **controle misto**, o evento chegou ao segundo relé **após seu spike e durante a refratariedade** — não pode ser tratado como causa daquele spike anterior. Os dois controles contabilizaram **cinco eventos entregues a DN**, sem disparos DN.

No âmbito desses caminhos, **H1, H2 e H5 foram falsificadas**, **H3 (integração sub-limiar) foi apoiada localmente**, e **H4 (atraso além da janela)** foi constatada em eventos específicos. **H6 permanece limite de validação científica**, não mecanismo fisiológico demonstrado. A explicação do silêncio global dos 1.303 DN continua indeterminada.

**Preservação:** nenhum código científico ou parâmetro alterado; hashes originais preservados; residente **OFFLINE**; nenhum episódio canônico; observatório e túnel **ATIVOS**; espaço livre informado de **20.451.758.080 bytes (cerca de 19,05 GiB)**. Um erro de heredoc reportado após o avanço foi seguido de verificação separada do traço, da integridade do SQLite, dos hashes e da ausência de temporários. O veredito **PASS** refere-se somente aos sete caminhos e ao sucesso do diagnóstico.

### 5.6 Onde a cadeia causal está demonstrada

| Elo | Situação em 05/11/2026 |
| --- | --- |
| Protocolo luminoso → alvos visuais | **Observado** no ensaio instrumental |
| Alvos estimulados → atividade LIF | **Observado** como resposta de população |
| Atividade visual → origem causal dos 47 spikes extravisuais | **Não demonstrada** evento a evento |
| Caminhos anatômicos dirigidos → DN | **Identificados** para 1.299 DN |
| Eventos sinápticos entregues e resposta de membrana em DN selecionados | **Observados** em 3 DN instrumentados (M19) e em 3 dos 12 amostrados (M20); amostras não equivalem a prova para toda a população |
| Cinco caminhos positivos → entrada no relé compartilhado | **Observada**: 64 eventos e resposta de membrana |
| Relé compartilhado → spike de saída → DN positivos | **Não observado**: relé não disparou e cinco DN não receberam eventos |
| Controles com relés ativos → DN | **Observado**: cinco eventos chegaram aos DN de controle, mas não houve spikes DN |
| Disparos DN | **Não observados** (0/1.303) |
| DN → comando motor → torque → movimento | **Não demonstrado** no ensaio |
| Corpo Pinocchio → sinal proprioceptivo → LIF | **Não demonstrado** no ensaio |
| Ciclo causal cérebro–corpo fechado | **NÃO DEMONSTRADO** |

Não há base para diagnosticar uma única causa global. A conectividade estrutural é condição de possibilidade, mas não é sinônimo de transmissão funcional. Nos **recortes examinados**, há transporte sináptico real até alguns DN, porém com integração insuficiente para disparo; em cinco caminhos positivos, a entrada chegou a um relé compartilhado que não disparou, deixando os cinco DN sem eventos. O primeiro elo sem spike está localizado nesses caminhos, sem causa matemática/fisiológica final estabelecida. **Nenhuma dessas observações constitui defeito de implementação demonstrado.**

## 6. Decisões, limites e próximos passos

**Decisões preservadas:**

- Manter a residente **OFFLINE**, sem criar episódio canônico, iniciar residência ou simular atividade para melhorar a aparência do painel.
- Manter o observatório público **somente de leitura** e alimentado pela amostra histórica imutável. Não misturar resultados de episódios instrumentais distintos nem rotular valores históricos como telemetria atual.
- Preservar o conectoma e o material científico de origem; não ajustar pesos, limiares, sinais ou regras motoras apenas para induzir disparos ou movimentos.
- Não publicar bancos, snapshots, checkpoints, arrays CSR, segredos, material de autenticação ou tokens no GitHub ou no Drive como parte desta consolidação. Preservar o WIP e relatórios originais.
- Não inferir consciência, intenção, aprendizagem ou equivalência biológica a partir de atividade LIF isolada.

**Próximo experimento proposto, não executado — Missão 22:** auditar quantitativamente **por que o relé compartilhado, apesar de receber 64 eventos, não disparou**, comparando sua integração à dos **quatro relés que dispararam** na Missão 21. Reutilizar traços reais antes de qualquer replay. Quantificar distribuição temporal, sinais e amplitudes dos eventos, evolução da membrana, somação, vazamento, máximo, distância ao limiar e refratariedade; conferir unidades, ordem do solver e proveniência dos parâmetros. Separar integração sub-limiar matematicamente explicada, erro de implementação demonstrável e falta de validação fisiológica. Análise de sensibilidade, se pertinente, será **contrafactual matemática** sem alterar runtime, parâmetros ou checkpoints. Não forçar disparos.

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
- `FLYNN_RACKGENIUS_ELECTROPHYSIOLOGICAL_TRACE_19.md` — traçado de eventos e potencial em cinco caminhos selecionados.
- `FLYNN_RACKGENIUS_DESCENDING_EXCITATORY_DRIVE_20.md` — inspeção aferente e sub-limiar em 12 DN.
- `FLYNN_RACKGENIUS_UPSTREAM_RELAY_CAUSALITY_21.md` — relé compartilhado recebeu 64 eventos sem disparar nos cinco caminhos positivos.

Arquivos históricos versionados e arquitetura: [`docs/MAPA_DE_PERCURSO_FLYNN.md`](https://github.com/NomosLudens/flynn/blob/master/docs/MAPA_DE_PERCURSO_FLYNN.md) e [README do projeto](https://github.com/NomosLudens/flynn). Os relatórios técnicos históricos continuam preservados. A etapa concluída em 26/10/2026 e os novos ensaios RackGenius são **fases experimentais distintas**; seus episódios não podem ser fundidos retrospectivamente.

---

**Síntese responsável:** a plataforma pública de observação histórica funciona, e a rede neural instrumental responde a estímulos visuais na fonte FAFB v783. **A Missão 21 localizou o primeiro elo sem spike em cinco caminhos positivos: um relé compartilhado recebeu 64 eventos mas não disparou; os cinco DN não receberam eventos.** Controles provaram chegada de eventos a DN e respostas sub-limiares, sem spikes DN. **Não foi demonstrado comando motor, propriocepção de retorno, ciclo corporal fechado, residência contínua ou consciência.** A explicação dinâmica do relé e a causa global do silêncio DN continuam abertas.
