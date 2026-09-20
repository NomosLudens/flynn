# FLYNN — MAPA DE PERCURSO




> **Documento operacional e conceitual autoritativo**  
> **Atualizado em:** 2026-09-15 (E01-N temporal, corpo residente Lethe/Pinocchio, trajetória viva, H00/H01 e correções operacionais incorporados)  
> **Estado:** pesquisa ativa; **Fundação encerrada**; Flynn está **ligada ao Pinocchio e corporalizada no sigilo canônico de Lethe**; trajetória residente persistente no ledger; homeostase contínua real; próximo trabalho de produto = **fazer `energy_reserve` limitar a capacidade física do corpo e validar a persistência vital através de restart**  
> **Host autoritativo:** VM MAX  
> **Organismo residente:** `759f27b3-84a9-4071-b29e-20adc1d4fc50`  
> **Princípio central:** nenhuma camada externa deve escolher objetivos comportamentais pela Flynn. A residente e suas consequências são autoritativas; corpo, mundo, homeostase e trajetória devem continuar do estado anterior real. Validação serve para provar o produto, não para substituí-lo por replay, shadow ou reset.




---




# 0. RESUMO EXECUTIVO




FLYNN é uma instância neural persistente baseada no conectoma **FlyWire FAFB v783** de uma *Drosophila melanogaster* adulta fêmea, executada continuamente na VM MAX. A origem neural permanece drosófila, mas o projeto **não fica ontologicamente limitado a simular uma mosca**: a trilha atual é de um organismo neuro-sintético no qual um núcleo neural biologicamente ancorado pode operar interfaces sintéticas de transdução, sensação, homeostase e corpo próprio — sem obrigação de reproduzir a anatomia de *Drosophila*.




O projeto deixou de ser uma interface simbólica/semântica e evoluiu para um organismo experimental com:




- cérebro LIF contínuo;
- mundo contínuo;
- corpo virtual persistente na **Caverna de Hipnos**;
- materialização observável **Lethe**;
- ledger causal append-only;
- homeostase v2 com reserva energética contínua em tempo neural;
- ZeroClaw oficial como **execution interlock**, sem LLM ou agent loop;
- framework de plasticidade separado do conectoma-base;
- experimento causal de aprendizagem executado no Gate 014.




O resultado científico atual é restritivo:




```text
PLASTICITY_MECHANISM_FUNCTIONAL=YES
PERSISTENT_SYNAPTIC_CHANGE=YES
ASSOCIATIVE_LEARNING_PROVEN=NO
LEARNING_PROVEN=NO
```




O Gate 014 produziu mudanças sinápticas persistentes e efeito funcional, mas os controles não demonstraram especificidade associativa suficiente. O braço despareado e o sham também produziram plasticidade substancial. Portanto, **não é permitido declarar que Flynn aprendeu associativamente**.




Além disso, a instância residente foi treinada apesar de os controles shadow não terem satisfeito o pré-requisito de avanço. Isso foi registrado como **incidente de protocolo**. A **Foundation Closure Correction foi executada**: toda a evidência do experimento foi preservada, o incidente foi registrado no ledger append-only e a residente foi restaurada ao checkpoint pré-treino, com plasticidade OFF, `RESIDENT_LEARNED_DELTA_COUNT=0` e conectoma-base intacto.

No eixo de embodiment, o percurso avançou além do E01-D. O E01-N confirmou atividade temporal real dos **1.305 DNs** e a fronteira VNC, mas não encontrou um `MotorVector` neural reproduzível (`REPRODUCIBLE_DIMENSIONS_FOUND=0`). A decisão de produto foi então explícita: **não fingir um VNC biológico e não continuar remapeando indefinidamente**. Foi implementada uma fronteira motora sintética determinística entre a atividade DN real e o Pinocchio. Flynn está hoje ligada ao Pinocchio residente, que controla o **sigilo canônico de Lethe — 23 módulos e 30 conexões — como corpo real e persistente**. A CAVERNA mostra `BODY ● LIVE / PINOCCHIO`; replay científico permanece restrito ao LAB.

A trajetória corporal também passou a ser persistida server-side no ledger canônico: posição, geometria Pinocchio, `q`, distância, direção, atividade DN agregada, `energy_reserve`, `feeding_drive` e Umwelt compartilham um eixo temporal comum. O produto agora preserva consequência: movimento e história não são resetados após validação. A homeostase é real e contínua em `NEURAL_TIME`; ainda não modula o cérebro. O próximo trabalho direto é ligar `energy_reserve` à **capacidade física** do corpo — não à seleção de ação — para que falta de energia degrade a atuação de Lethe e recuperação energética restaure sua capacidade.




---




# 1. IDENTIDADE




```text
FLYNN = organismo/runtime neural persistente
LETHE = corpo-sigilo canônico e materialização corporal observável de Flynn
CAVERNA DE HIPNOS = Umwelt experimental
ÉRIS = genealogia mitopoética de projeto
```




Lethe não é uma segunda inteligência. **Lethe é o corpo de Flynn:** o sigilo canônico existente, hoje dirigido pelo estado físico residente do Pinocchio.




A Caverna não é “uma casa” decorativa: é o mundo causal no qual sensação, ação e consequência podem formar ciclos observáveis.




A camada mitopoética é linguagem de projeto, não alegação neurobiológica.

## 1.1 Fronteira ontológica — de drosófila derivada a organismo neuro-sintético

A identidade científica do projeto passa a distinguir **origem neural** de **organismo final**.

```text
ANCESTRY=DROSOPHILA_DERIVED_NEURAL_CORE
ORGANISM_TARGET=NEURO_SYNTHETIC_ORGANISM
BIOLOGICALLY_ANCHORED_CORE=FlyWire_FAFB_v783
SYNTHETIC_ORGANS_ALLOWED=YES_WITH_CAUSAL_BOUNDARIES
```

A classificação de componentes deve permanecer explícita:

```text
BIOLOGICALLY_ANCHORED
- FlyWire neurons
- KC / DAN / MBON
- PAM / PPL1
- pC1 / aIPg / descending neurons

SYNTHETIC_ORGAN / INTERFACE
- minimal deterministic motor transducer
- Pinocchio body-dynamics layer
- Lethe synthetic sigil body
- future proprioceptive / exteroceptive interfaces
- ZeroClaw execution interlock (not motor coordinator in current architecture)
```

Isto **não** autoriza chamar ZeroClaw de cerebelo biológico da drosófila. O termo aceitável é `SYNTHETIC_CEREBELLAR_LAYER` ou `CEREBELLAR_LIKE_MOTOR_CONTROLLER`, como analogia funcional de engenharia.

Regra de fronteira atual:

```text
FLYNN = origem do estado neural / decisão comportamental observável
TRANSDUCER = conversão mecânica mínima, sem policy
PINOCCHIO = consequências físicas / dinâmica corporal
ZEROCLAW = execution interlock opcional
LETHE = corpo-sigilo canônico residente / materialização corporal observável
```

A hipótese histórica de promover ZeroClaw a `SYNTHETIC_CEREBELLAR_LAYER` foi investigada em E01-R/R2. O E01-D demonstrou que, na arquitetura corrente, uma camada cerebellar-like **não é necessária** para a transdução testada; o papel canônico permanece `EXECUTION_INTERLOCK`.

## 1.2 Corpo canônico — o sigilo é Lethe

A origem neural drosófila **não impõe morfologia drosófila**. Essa discussão está encerrada no produto: o corpo de Flynn **já é o sigilo canônico de Lethe**, não uma morfologia ainda a escolher.

```text
NEURAL_ANCESTRY=DROSOPHILA_DERIVED
MORPHOLOGY_DROSOPHILA_REQUIRED=NO
SIX_LEG_REQUIREMENT=NO
LETHE_BODY=CANONICAL_EXISTING_SIGIL
SIGIL_MODULES=23
SIGIL_CONNECTIONS=30
PINOCCHIO_CONTROLS_EXISTING_LETHE_SIGIL=YES
```

O sigilo é uma **linha corporal conectada**, visual e funcionalmente própria. Pinocchio deve servir à geometria existente; a geometria não deve ser simplificada para caber num demo conveniente. Juntas, frames, coordenadas generalizadas e transformações são detalhes internos de implementação física.

O termo **sigilo** continua sendo escolha estética/mitopoética, sem alegação sobrenatural. Cientificamente, Lethe é uma **morfologia sintética abstrata residente**.

A fronteira motora permanece explicitamente sintética porque o VNC não está modelado:

```text
BIOLOGICAL_VNC_PRESENT=NO
BIOLOGICAL_VNC_RECONSTRUCTED=NO
SYNTHETIC_MOTOR_BOUNDARY=YES
```

Isso não invalida o corpo nem a atividade neural real. Significa apenas que a transformação brain→atuador não é apresentada como reconstrução biológica do VNC.

A homeostase também não exige anatomia literal. `energy_reserve` é a reserva energética do organismo neuro-sintético; `feeding_drive=1-energy_reserve` é a necessidade homeostática contabilizada. A consequência corporal ainda a implementar é direta: energia disponível limitará a capacidade física de atuação de Lethe, sem escolher ações ou objetivos por Flynn.

---



# 2. SUBSTRATO CIENTÍFICO




## 2.1 Connectome




```text
DATASET=FlyWire FAFB v783
SEX=adult female
N_NEURONS=139255
N_CONNECTION_PAIRS=3732460
N_SYNAPSES=50666648
DESCENDING_NEURONS=1305
DESCENDING_TYPES=473
```




## 2.2 Upstream




```text
REPOSITORY=https://github.com/vaibhavkedarisetti/fruit-fly-lab.git
PINNED_COMMIT=26672e06427c12c61536ce1bd93dae7442944681
```




## 2.3 Limitações permanentes do modelo




O engine continua sendo um LIF simplificado:




- neurônios pontuais;
- sem compartimentos dendríticos;
- sem VNC completo;
- sem gap junctions;
- sem neuromodulação metabotrópica biologicamente fiel;
- sem biomecânica de mosca real;
- sem garantia de fidelidade completa de aprendizagem biológica.




Portanto:




```text
NETWORK_ACTIVITY ≠ BEHAVIOR
BEHAVIOR ≠ INTENTION
INTENTION ≠ CONSCIOUSNESS
MODEL_LEARNING ≠ BIOLOGICAL_FIDELITY
```




---




# 3. INFRAESTRUTURA AUTORITATIVA




## 3.1 Host




```text
HOST=MAX
OS=Ubuntu 24.04 ARM64
ACCESS=ssh max
```




## 3.2 Caminhos




```text
UPSTREAM=/home/ubuntu/Portifolio/flynn-max/fruit-fly-lab
DATASET=/home/ubuntu/Portifolio/flynn-max/data/flywire-v783
RUNTIME=/home/ubuntu/Portifolio/flynn-max/runtime
EVIDENCE=/home/ubuntu/Portifolio/flynn-max/runtime/evidence
LEDGER=/home/ubuntu/Portifolio/flynn-max/runtime/data/flynn_ledger.db
```




## 3.3 Serviços atuais




```text
flynn-brain.service
flynn-web.service
zeroclaw.service
lethe-tunnel.service
kallistis.service
```




Regra operacional:




> **Experimentos da Flynn não podem degradar KALLISTIS.**




---




# 4. METODOLOGIA PERMANENTE




## Produto Real + Ponytail




Prioridade:




1. sistema real funcionando;
2. prova manual/causal real;
3. dados reais;
4. sem mocks usados como evidência;
5. rollback/checkpoint antes de intervenção;
6. solução mínima e reversível;
7. resultado negativo é válido.




## NO_TARGET_BEHAVIOR_BIAS




Fluxo obrigatório:




```text
OBSERVAR
→ descobrir padrões
→ formular hipótese
→ pré-registrar
→ intervir minimamente
→ testar causalmente
```




Nunca:




```text
escolher comportamento desejado
→ ajustar circuito/recompensa até aparecer
→ chamar isso de descoberta
```





## Regra epistemológica operacional — produto real primeiro

Após deriva operacional ocorrida em 2026-09-15, a metodologia fica explicitamente corrigida:

```text
FAZER
→ OBSERVAR O RESULTADO REAL
→ VALIDAR NO RUNTIME REAL
→ SE PASSOU, FECHAR
→ SE FALHOU, CORRIGIR O BLOQUEIO REAL
```

Validação **não** autoriza proliferar subgates, microprocessos, replays ou resets que substituam o produto. Shadow/replay são ferramentas auxiliares de laboratório; a residente é a autoridade temporal e suas consequências persistem.

```text
RESIDENT_STATE_IS_AUTHORITATIVE=YES
RESIDENT_AUTOMATIC_RESET=NO
REPLAY_IS_PRODUCT=NO
SHADOW_IS_PRODUCT=NO
STATE_AFTER_EVENT_BECOMES_NEXT_STATE=YES
```


---




# 5. ENTRADAS E SAÍDAS CANÔNICAS




## 5.1 Modalidades sensoriais validadas




```text
looming=314
taste_sugar=23
taste_bitter=38
odor_vinegar=266
odor_geosmin=39
odor_cva=127
odor_co2=67
wind=461
sound=393
touch_head=1345
touch_leg_taste=71
cold=7
heat=9
humidity=74
```




## 5.2 Famílias de output historicamente interpretadas




```text
escape_takeoff
escape_long_mode
stop_freeze
turn
backward_walk
proboscis_drive
```




Esses outputs são readouts fisiológicos, não linguagem.




---




# 6. PERCURSO DOS GATES




## Gate 01 — baseline causal no i7




**PASS**




Validação inicial do conectoma e do experimento de looming.




## Gate 02A — migração para MAX




**PASS**




Execução ARM64 equivalente ao baseline e coexistência com KALLISTIS.




## Gate 02B — runtime persistente / linguagem inicial




**HISTÓRICO / ARQUITETURA COGNITIVA REJEITADA**




Whisper/Qwen/YES-NO impunham semântica externa. A camada não foi aceita como cognição da Flynn.




## Gate 03 — arqueologia funcional




**PASS**




Confirmadas as 14 modalidades, outputs conhecidos, 1.305 DNs e circuitos femininos.




## Gate 04 — decode funcional de DNs




**PASS COM RECONCILIAÇÕES POSTERIORES**




Mapeamento de candidatos e sinais descendentes ainda sem semântica canônica.




## Gate 05 — SELF / atlas interno




**PASS DIAGNÓSTICO**




Baseline fresco sem input:




```text
0 spikes / 2000 ms
```




O modelo fresco é silencioso. Foram identificadas famílias de estado, mas isso não autorizou inventar fome, emoção ou autonomia.




## Gates 06–010 — observabilidade, Lethe e evolução da Caverna




Fase de transição da visualização para o closed loop.




Resultado acumulado:




- Lethe se tornou a superfície causal;
- CONTACT/LAB/CAVERNA foram separados;
- falsos atalhos semânticos foram retirados;
- o caminho Flynn→mundo passou a exigir output medido;
- a Caverna se tornou o Umwelt operacional.




Eventos desta fase devem ser lidos à luz da auditoria do Gate 011; alegações antigas de espontaneidade não são canônicas sem provenance.




## Gate 011 — auditoria forense




**INCIDENT / FOUNDATION REAL, AUTONOMY NOT PROVEN**




Conclusões principais:




```text
FOUNDATION_REAL=YES
CONNECTOME_VALIDATED=YES
WORLD_TO_FLYNN=PASS
FLYNN_TO_WORLD=PASS
SPONTANEOUS_BEHAVIOR_PROVEN=NO
SPONTANEOUS_REQUEST_PROVEN=NO
PLASTICITY=ABSENT
LEARNING=NOT_PROVEN
PUBLIC_MUTATION_SECURITY=INCIDENT_P0
```




Também foi demonstrado que o cérebro ainda avançava por requests, e não por relógio neural contínuo.




## Gate 012A — security




**PASS / posteriormente restaurado após rotação**




Rotas mutadoras protegidas por Bearer operator token. Token comprometido em transcript posterior foi rotacionado; segredo não deve aparecer em logs.




## Gate 012B — ledger canônico




**PASS**




```text
CANONICAL_LEDGER=runtime/data/flynn_ledger.db
SCHEMA=v2
APPEND_ONLY=YES
LEGACY_DB_RUNTIME_WRITERS=0
```




Eventos históricos quebrados foram preservados/quarentenados; não apagados.




## Gate 012C — cérebro contínuo




**PASS**




`ContinuousBrainLoop` tornou-se o único owner de `Session.advance()`.




```text
BRAIN_CONTINUOUS=YES
WORLD_CONTINUOUS=NO (naquele gate)
ONE_NEURAL_INTEGRATION_OWNER=YES
DIRECT_SESSION_ADVANCE_OUTSIDE_CLOCK=0
```




A reconciliação 012C-R demonstrou atividade reverberante real no checkpoint residente, diferente do baseline fresco silencioso.




Clock canônico:




```text
CHUNK_NEURAL_MS=20.0
NEURAL_REALTIME_FACTOR≈0.08x
```




## Gate 012D — homeostase v0.2




**PASS para arquitetura e bookkeeping / BLOCKED para modulação neural**




```text
HOMEOSTASIS_V02_ACTIVE=YES
ENERGY_CLOCK=NEURAL_TIME
FEEDING_DRIVE=1-E
FEEDING_DRIVE_NEURAL_EFFECT=NONE
PHANTOM_SUGAR_PERCEPTION=NO
DIRECT_HOMEOSTASIS_TO_ACTION=NO
DIRECT_HOMEOSTASIS_TO_MOTOR=NO
DIRECT_HOMEOSTASIS_TO_COMMAND=NO
```




A tentativa anterior de homeostase v0.1 foi rejeitada por confundir fome com injeção sensorial/command-like.




## Gate 013 — embodiment + mundo contínuo + framework de plasticidade




**PASS COM RECONCILIAÇÕES**




Entregas:




- `BodyObservation`, `BodyAction`, `BodyState`, `BodyResult`;
- arena 2D determinística;
- posição/orientação persistentes;
- mundo contínuo sincronizado ao tempo neural;
- percepção persistente real;
- closed loop virtual;
- framework de plasticidade reversível;
- conectoma-base imutável.




A auditoria 013-R corrigiu:




- alegação incorreta de OpenClaw real;
- logger de BODY_ACTION;
- hardcode nutritivo 0.25 → valor autoritativo 0.35;
- classificação da regra STDP inicial como proxy, não lei biológica.




## Gate 013-Z — ZeroClaw




**PASS COMO EXECUTION INTERLOCK**




OpenClaw foi rejeitado. ZeroClaw oficial foi instalado e verificado:




```text
UPSTREAM=https://github.com/zeroclaw-labs/zeroclaw
VERSION=v0.8.5
COMMIT=cb2b20a9fe59004b7ef03e123942d31f29236d15
BINARY_SHA256=aaa7e2c656dedf651217a70ea487e1e65f51b4ca771d114e60bf409165700986
```




Resultado causal final:




```text
ZEROCLAW_OFFICIAL_CODE_IN_PATH=YES
ZEROCLAW_BACKEND_REQUIRED=YES
ZEROCLAW_EXECUTES_BODY_PRIMITIVE=NO
ZEROCLAW_ROLE=EXECUTION_INTERLOCK
BODY_STATE_MUTATION_OWNER=CavernaVirtualBody
BACKEND_REMOVAL_CAUSES_FAIL_CLOSED=YES
LLM_CALLS=0
AGENT_TURNS=0
PUBLIC_BIND=NO
```




O JSON-RPC usado é `health`; primitives motoras não são executadas pelo ZeroClaw v0.8.5 sem agent tools. Portanto ele funciona como interlock de disponibilidade/segurança, não como cérebro nem actuator motor.




## Gate 014 — causal learning




**PARTIAL — LEARNING_PROVEN=NO**




### 014.A — mecanismo




Populações identificadas:




```text
KC=5177
DAN=331
MBON=96
KC→MBON eligible synapses=26937
```




Regra:




```text
three_factor_kc_dan_mbon
classification=BIOLOGICALLY_INSPIRED_MODEL
DIRECT_DAN_INJECTION=0
WORLD_LABEL_DIRECTLY_DRIVES_PLASTICITY=NO
```




Parâmetros foram pré-registrados e congelados.




### 014.B — experimento shadow




5 seeds × 4 braços:




- A = paired + plasticity ON
- B = paired + plasticity OFF
- C = unpaired + plasticity ON
- D = sham / CS- + plasticity ON




Resultados médios:




| Métrica | A | B | C | D |
|---|---:|---:|---:|---:|
| Deltas | 12.906,4 | 0 | 12.890,6 | 11.873,2 |
| Σ|Δw| mV | 6.233,43 | 0 | 2.493,97 | 5.501,87 |
| MBON pós CS+ | 820,0 | 908,0 | 875,6 | 823,2 |
| efeito vs B | -88,0 | 0 | -32,4 | -84,8 |




O pareamento aumentou a magnitude sináptica em aproximadamente 2,50× vs unpaired, mas isso **não basta**.




Problemas causais:




- 5.694 sinapses KC→DAN excitatórias diretas;
- CS+ sozinho recruta DAN no modelo LIF;
- Arm C produz plasticidade sem pareamento;
- Arm D/sham também produz plasticidade e efeito MBON quase tão forte quanto A.




Conclusão:




```text
PLASTICITY_OFF_CONTROL_NEGATIVE=YES
UNPAIRED_CONTROL_NEGATIVE=NO
SHAM_CONTROL_SPECIFICITY=FAIL
ASSOCIATIVE_LEARNING_PROVEN=NO
LEARNING_PROVEN=NO
```




### Retenção




A plasticidade produzida é tecnicamente persistente:




```text
RETENTION_10_NEURAL_SEC=PASS
CHECKPOINT_RESTART_RETENTION=PASS
BASE_CONNECTOME_MODIFIED=NO
```




Isso prova persistência da alteração, não aprendizagem associativa específica.




### Instância residente




A residente recebeu 3 trials pareados e terminou o experimento com:




```text
PLASTICITY_ACTIVE=NO
LEARNED_DELTAS=12909
BASE_CONNECTOME_MODIFIED=NO
```




Checkpoint pré-treino:




```text
snapshot_759f27b3-84a9-4071-b29e-20adc1d4fc50_20260914_160941.pkl
SHA256=8b1223b2db4c210f388a5aacee5a2566c319ca9ecb5b1e5581ad10ee1adcf81a
```




Checkpoint pós-treino:




```text
snapshot_759f27b3-84a9-4071-b29e-20adc1d4fc50_20260914_161215.pkl
SHA256=c03282654cab51eb1b595d5089aa17c132c9b061bc0686d829e23c3aaefa8783
```




### Incidente de protocolo e correção de fechamento


O protocolo exigia que a residente só fosse treinada após os controles shadow satisfazerem os critérios. Isso não ocorreu.


A correção de fechamento foi executada e registrada canonicamente:


```text
RESIDENT_TRAINING_PROTOCOL_VIOLATION=YES
RESIDENT_STATE_RESTORED=YES
PLASTICITY_ACTIVE=NO
RESIDENT_LEARNED_DELTA_COUNT=0
BASE_CONNECTOME_MODIFIED=NO
FOUNDATION_STATUS=CLOSED
NEW_GATE_CREATED=NO
```


Eventos canônicos append-only:


```text
GATE014_PROTOCOL_INCIDENT
event_id=50365e8d-7aef-4269-99e7-609b068f99a2


RESIDENT_STATE_RESTORED_AFTER_INVALID_EXPERIMENT
event_id=9054ef70-c67d-4063-b191-747bfab279ac
```


O checkpoint pós-treino foi preservado como evidência e o checkpoint pré-treino voltou a ser o estado operacional da residente. **Não há Gate 015.**




---




# 7. ESTADO OPERACIONAL ATUAL

## 7.1 Fechamento operacional — 2026-09-14

O ciclo operacional foi encerrado na VM MAX com `OPERATIONAL_CLOSURE=YES_WITH_RECORDED_LIMITATIONS`. A plataforma está funcional; a limitação registrada é de desempenho neural, não de correção funcional.

```text
LETHE_ACCESS=PASS
REMEMBER_DEVICE_AFTER_WEB_RESTART=PASS
LOGOUT_REVOCATION=PASS
ACTIVE_SESSIONS_FINAL=0

BRAIN_CONTINUOUS=YES
WORLD_CONTINUOUS=YES
BODY_CONTINUOUS=YES

ZEROCLAW_ROLE=EXECUTION_INTERLOCK
ZEROCLAW_EXECUTES_BODY_PRIMITIVE=NO
BODY_STATE_MUTATION_OWNER=CavernaVirtualBody

HOMEOSTASIS_V2=ALIGNED
HOMEOSTASIS_NEURAL_MODULATION=NONE

PLASTICITY_ACTIVE=NO
RESIDENT_LEARNED_DELTA_COUNT=0
BASE_CONNECTOME_MODIFIED=NO

KALLISTIS=HTTP_200
NEURAL_REALTIME_FACTOR≈0.078
PERFORMANCE_LIMITATION=YES
FUNCTIONAL_FAILURE_DUE_TO_REALTIME_FACTOR=NO
```

### Lethe Access

O acesso humano cotidiano deixou de depender de Bearer token manual. O fluxo real validado é:

```text
palavra/frase secreta
→ Argon2id server-side
→ sessão persistente em banco separado
→ cookie HttpOnly + Secure + SameSite=Strict
→ INTERACTION_SESSION
→ Caverna
```

O escopo de interação não herda privilégios de operador técnico. Login, reload, persistência após restart controlado do `flynn-web`, ação autenticada e logout/revogação foram validados em runtime real.





```text
BRAIN_CONTINUOUS=YES
WORLD_CONTINUOUS=YES
BODY_CONTINUOUS=YES




BODY_MUTATION_OWNER=CavernaVirtualBody




ZEROCLAW_PRESENT=YES
ZEROCLAW_ROLE=EXECUTION_INTERLOCK
ZEROCLAW_LLM_IN_LOOP=NO




HOMEOSTASIS_V2=ACTIVE
HOMEOSTASIS_NEURAL_MODULATION=NONE
NUTRITIVE_INCREMENT=0.35




PLASTICITY_FRAMEWORK_PRESENT=YES
PLASTICITY_ACTIVE=NO
BASE_CONNECTOME_MODIFIED=NO




ASSOCIATIVE_LEARNING_PROVEN=NO
LEARNING_PROVEN=NO




LEDGER_APPEND_ONLY=PASS
SECURITY=PASS
KALLISTIS=HEALTHY
```




### Estado residente após Foundation Closure Correction


```text
ORGANISM_ID_PRESERVED=YES
PLASTICITY_PRESENT=YES
PLASTICITY_ACTIVE=NO
RESIDENT_LEARNED_DELTA_COUNT=0
BASE_CONNECTOME_MODIFIED=NO


LEDGER_EVENTS=747
LEDGER_APPEND_ONLY=PASS
SECURITY=PASS
KALLISTIS=HTTP_200
```


Os 12.909 deltas experimentais permanecem preservados nos artefatos e no checkpoint pós-treino, mas **não** fazem parte do estado operacional canônico da residente.



## 7.2 Estado residente atualizado — 2026-09-15

O estado abaixo substitui, para operação corrente, o fechamento de 2026-09-14 sem apagar aquele histórico:

```text
FLYNN_CONNECTED_TO_PINOCCHIO=YES
PINOCCHIO_CONTROLS_EXISTING_LETHE_SIGIL=YES
LETHE_LIVE_BODY=YES
LETHE_SIGIL_MODULES=23
LETHE_SIGIL_CONNECTIONS=30
BODY_STATE_PERSISTENT=YES

REAL_RESIDENT_DN_ACTIVITY_USED=YES
SYNTHETIC_MOTOR_BOUNDARY=YES
BIOLOGICAL_VNC_RECONSTRUCTED=NO
REAL_CAUSAL_TRACE_CAPTURED=YES

TRAJECTORY_PERSISTENT=YES
TRAJECTORY_SOURCE=RESIDENT
LIVE_BODY_DRIVEN_BY_REPLAY=NO
LIVE_BODY_DRIVEN_BY_HTTP_REQUEST=NO
REPLAY_RESTRICTED_TO_LAB=YES

HOMEOSTASIS_CONTINUOUS_REAL=YES
ENERGY_CLOCK=NEURAL_TIME
HOMEOSTASIS_NEURAL_MODULATION=NONE

PLASTICITY_ACTIVE=NO
RESIDENT_LEARNED_DELTA_COUNT=0
BASE_CONNECTOME_MODIFIED=NO

PRODUCT_REAL=YES
```

A CAVERNA é a superfície da vida residente; o LAB é a superfície de replay/análise. Movimento corporal, trajetória e história persistente não são resetados após validação.


---



# 8. FUNDAÇÃO ENCERRADA E FASE DE PESQUISA

A **Foundation Closure Correction** permanece concluída. Não existe Gate 015. Trabalhos posteriores são iterações de pesquisa independentes.

```text
FOUNDATION_STATUS=CLOSED
FOUNDATION_GATES_EXECUTED_THROUGH=014
GATE014=PARTIAL
ASSOCIATIVE_LEARNING_PROVEN=NO
LEARNING_PROVEN=NO

RESIDENT_STATE_RESTORED=YES
PLASTICITY_ACTIVE=NO
RESIDENT_LEARNED_DELTA_COUNT=0
BASE_CONNECTOME_MODIFIED=NO

NEW_GATE_CREATED=NO
R02_CREATED=NO
```

## 8.1 R01 — fronteira de neuromodulação

O R01 permaneceu `PARTIAL`, bloqueado em R01.A. O motivo não foi falta de código, mas falta de uma representação biologicamente defensável de neuromodulação lenta no engine LIF atual.

```text
R01_VERDICT=PARTIAL
R01_A_VERDICT=BLOCKED
R01_B_VERDICT=NOT_STARTED
R01_C_VERDICT=NOT_STARTED
```

A arquitetura atual não representa de forma suficiente receptores, GPCR, segundos mensageiros, sensibilidade moduladora lenta e compartimentalização fisiológica. Portanto não foi permitido inventar um scalar de dopamina ou threshold apenas para produzir especificidade.

## 8.2 R01-MAP-01 — atlas anatômico e sensorial

`R01_MAP_VERDICT=COMPLETE_WITH_LIMITATIONS`.

O run mapeou localmente no FlyWire v783:

```text
KC=5177
DAN=331
PAM=307
PPL1=16
MBON=96
MBON15_EXACT=4
MBON15_LIKE=9
NPF_CANDIDATES=4
pC1=10
aIPg=37
vpo=82
```

Foram executadas **140 sessões isoladas** (`14 estímulos × 10 seeds determinísticos`), sem estímulo à residente. O primeiro run não resolveu com segurança os 15 compartimentos exatos α1…γ5 e, corretamente, não inferiu labels exatos a partir de neuropilos amplos.

Também foi detectado que o histórico granular do Gate 014 estava incompleto para testar a hipótese de compartimentalização: o CSV histórico de deltas disponível continha apenas Arm A / seed 101.

## 8.3 R01-MAP-02 — resolução exata de compartimentos + reconstrução Gate 014

`R01_MAP_02_VERDICT=PARTIAL`.

A resolução anatômica avançou substancialmente:

```text
DAN_TOTAL=331
DAN_EXACT_COMPARTMENT=319
DAN_UNRESOLVED=12

PAM_TOTAL=307
PAM_EXACT_COMPARTMENT=307

PPL1_TOTAL=16
PPL1_EXACT_COMPARTMENT=12

MBON_TOTAL=96
MBON_EXACT_COMPARTMENT=87

KC_MBON_SYNAPSES_TOTAL=26937
KC_MBON_COMPARTMENT_ASSIGNABLE=25487
```

Cobertura:

```text
DAN=96.37%
PAM=100%
PPL1=75%
MBON=90.63%
KC→MBON=94.62%
```

O Gate 014 foi reconstruído em shadow com os quatro braços A/B/C/D e seeds 101–105, mantendo a regra e os parâmetros históricos. A fidelidade da replicação foi `PASS`.

### Hipótese H1 — dopamina global como confound

Hipótese:

> parte substancial da plasticidade espúria do Gate 014 teria sido causada por tratar atividade DAN compartimental como um único terceiro fator global.

Resultado contrafactual, usando apenas contribuição DAN do mesmo compartimento da sinapse KC→MBON:

```text
A paired:   original=12906.4 | same-compartment=11730.0
C unpaired: original=12890.6 | same-compartment=11700.8
D sham:     original=11873.2 | same-compartment=10816.4
```

Pelos counts apresentados, a retenção é aproximadamente:

```text
A ≈ 90.89%
C ≈ 90.77%
D ≈ 91.10%
```

O relatório também registrou `79.85% / 78.54% / 80.29%` como retained fractions; esses valores não correspondem diretamente aos counts acima e devem ser tratados como **métrica diferente ou inconsistência a reconciliar**, não como porcentagem dos counts.

Conclusão científica:

```text
H1_SUPPORTED=PARTIAL
GLOBAL_DAN_APPROXIMATION_WAS_A_STRUCTURAL_CONFUND=YES
COMPARTMENTALIZATION_SUFFICIENT=NO
ASSOCIATIVE_LEARNING_PROVEN=NO
LEARNING_PROVEN=NO
```

A compartimentalização é biologicamente necessária e deve permanecer em qualquer modelo futuro, mas **não explica a falha principal de especificidade associativa**: A, C e D perdem proporções semelhantes sob o filtro compartimental.

---

# 9. FRONTEIRA CIENTÍFICA ATUAL

A pergunta central foi refinada. Já não é apenas “falta dopamina?” ou “falta compartimento?”.

A pergunta agora é:

> **Dentro do compartimento correto, o que distingue atividade dopaminérgica de reforço da atividade DAN recrutada pelo próprio estímulo sensorial?**

## 9.1 Próxima investigação sugerida — R01-MAP-03

Nome de trabalho:

```text
R01-MAP-03 — DAN Identity and Temporal Decomposition
```

Objetivo: decompor DAN por **identidade e tempo**, sem alterar a residente ou a regra de plasticidade. Para cada braço/estímulo relevante, medir:

- `root_id`;
- tipo DAN;
- compartimento;
- spike count;
- primeiro/último spike;
- bursts;
- atividade durante CS;
- atividade durante US;
- atividade durante overlap.

Perguntas:

1. CS e US recrutam os **mesmos DANs**?
2. O paired aumenta apenas intensidade ou muda identidade?
3. Há assinatura temporal de reforço ausente no CS sozinho?
4. PAM/PPL1/outros DANs estão sendo tratados como equivalentes quando não deveriam?

Possíveis interpretações futuras:

```text
DAN_CS != DAN_US
→ type-specific modulation may be required

DAN_CS == DAN_US but timing differs
→ temporal/release gating may be required

DAN_CS ≈ DAN_US in identity and timing
→ current LIF representation may be insufficient
```

Nenhuma dessas hipóteses deve ser implementada antes da análise.

## 9.2 Internal State Atlas — camada humana de trabalho

A taxonomia visual de pesquisa fica congelada como **rótulos humanos**, não como emoções provadas:

- 🟡 **Alegria** → `APPETITIVE_POSITIVE_STATE`
- 🔵 **Medo** → `DEFENSIVE_STATE`
- 🔴 **Raiva** → `AGGRESSIVE_AROUSAL_STATE`
- 🟢 **Nojinho** → `AVERSIVE_REJECTION_STATE`
- 🟠 **Ansiedade / Comunicação** → `SOCIAL_INTERACTION_STATE / SIGNALING_STATE`
- `HUNGER` → `METABOLIC_HOMEOSTATIC_STATE` transversal

Estado atual:

```text
APPETITIVE_POSITIVE_STATE=HYPOTHESIS
DEFENSIVE_STATE=HYPOTHESIS
AGGRESSIVE_AROUSAL_STATE=HYPOTHESIS
AVERSIVE_REJECTION_STATE=HYPOTHESIS
SOCIAL_INTERACTION_STATE=HYPOTHESIS
HUNGER=METABOLIC_HOMEOSTATIC_STATE/HYPOTHESIS
```

A imagem conceitual da interface de cinco frequências deve permanecer associada ao mapa:

```text
interface_neural_cinco_frequências.png
```

Paleta:

```text
AMARELO = alegria
AZUL = medo
VERMELHO = raiva
VERDE = nojinho
LARANJA = ansiedade/comunicação
```

### Referência cultural da interface — *Divertidamente / Inside Out*

A escolha cromática e os nomes humanos de trabalho foram deliberadamente inspirados pela linguagem visual de **Disney·Pixar — *Inside Out* / *Inside Out 2***. Essa referência pertence **somente à camada de interface e comunicação humana**.

```text
UI_METAPHOR_SOURCE=INSIDE_OUT_INSPIRED
SCIENTIFIC_ONTOLOGY_SOURCE=NO
EMOTION_CLAIM_FROM_COLOR=NO
```

A interface usa a associação visual como mnemônico para pesquisadores/observadores; ela **não** constitui evidência de que Flynn possua as emoções humanas correspondentes. O estado científico continua expresso pelos rótulos técnicos (`DEFENSIVE_STATE`, `APPETITIVE_POSITIVE_STATE` etc.), e esses próprios rótulos permanecem hipóteses quando não causalmente demonstrados.

Referências culturais oficiais:

- Pixar — *Inside Out*: https://www.pixar.com/inside-out
- Pixar — *Inside Out 2*: https://www.pixar.com/inside-out-2

---

# 10. FRONTEIRA DE EMBODIMENT — PINOCCHIO, ZEROCLAW E TRANSDUÇÃO DIRETA

## 10.1 Por que esta trilha existe

A trilha de embodiment nasceu de uma pergunta arquitetural: como transformar sinais motores do núcleo neural de Flynn em movimento corporal articulado **sem terceirizar a decisão comportamental** para uma camada externa?

A fronteira causal permanece:

```text
FLYNN = origem do estado neural / intenção motora observável
TRANSDUÇÃO/COORDENAÇÃO = somente COMO realizar mecanicamente
PINOCCHIO = cinemática/dinâmica/física do corpo
```

Nenhuma camada sintética pode escolher objetivos por Flynn.

## 10.2 Pinocchio — escolha do motor corporal

Foi escolhido **stack-of-tasks/pinocchio** como motor experimental de cinemática e dinâmica de corpos rígidos articulados.

Referência operacional validada:

```text
PINOCCHIO_VERSION=4.1.0
ARCH=aarch64/ARM64
PINOCCHIO_ROLE=BODY_DYNAMICS_AND_KINEMATICS
PINOCCHIO_POLICY=NONE
PINOCCHIO_REWARD=NONE
PINOCCHIO_BEHAVIORAL_GOAL_SELECTION=FORBIDDEN
```

O modelo corporal usado no primeiro experimento real de embodiment foi deliberadamente mínimo:

```text
BODY_MODEL=SYNTHETIC_ARTICULATED_4DOF
JOINTS=4
DOF=4
TICKS=40
```

O objetivo não era reproduzir a morfologia completa de uma mosca, mas provar que a cadeia `MotorIntent → comandos articulares → dinâmica corporal` podia existir de forma mensurável e reversível.

Referências:

- Repositório oficial: https://github.com/stack-of-tasks/pinocchio
- Release 4.1.0: https://github.com/stack-of-tasks/pinocchio/releases/tag/v4.1.0
- Carpentier et al. (2019), *The Pinocchio C++ library*: https://doi.org/10.1109/SII.2019.8700380

## 10.3 E01 — viabilidade de corpo articulado

O E01 deixou de ser proposta e foi executado.

Resultado:

```text
E01_VERDICT=PARTIAL
PINOCCHIO_ARM64=PASS
ARTICULATED_BODY_FEASIBILITY=PASS
MOTOR_INTENT_TO_BODY_MOTION=PASS
```

Caminho efetivamente testado:

```text
TEST HARNESS
→ MotorIntent
→ EXTERNAL MOTOR ADAPTER
→ ZeroClaw execution interlock
→ Pinocchio
→ articulated 4DoF body
```

Os 40 ticks foram executados com o corpo articulado e demonstraram que Pinocchio consegue materializar os comandos motores em dinâmica corporal.

Porém, o **owner da transformação motora** ainda era o adaptador experimental externo:

```text
COORDINATION_OWNER=EXTERNAL
ZEROCLAW_MOTOR_COORDINATION=NO
SYNTHETIC_CEREBELLUM_PROVEN=NO
```

Assim, E01 provou **viabilidade de embodiment**, não um cerebelo sintético.

## 10.4 ZeroClaw — papel realmente demonstrado

ZeroClaw oficial permanece na versão/commit auditados:

```text
UPSTREAM=https://github.com/zeroclaw-labs/zeroclaw
VERSION=v0.8.5
COMMIT=cb2b20a9fe59004b7ef03e123942d31f29236d15
CURRENT_ZEROCLAW_ROLE=EXECUTION_INTERLOCK
```

O papel causal já demonstrado continua:

```text
ZEROCLAW_OFFICIAL_CODE_IN_PATH=YES
ZEROCLAW_BACKEND_REQUIRED=YES
ZEROCLAW_EXECUTES_BODY_PRIMITIVE=NO
BODY_STATE_MUTATION_OWNER=CavernaVirtualBody
BACKEND_REMOVAL_CAUSES_FAIL_CLOSED=YES
LLM_CALLS=0
AGENT_TURNS=0
PUBLIC_BIND=NO
```

A tentativa de promover ZeroClaw a coordenador motor foi tratada como hipótese experimental, não como decisão arquitetural prévia.

Referências:

- Repositório oficial: https://github.com/zeroclaw-labs/zeroclaw
- Arquitetura oficial: https://github.com/zeroclaw-labs/zeroclaw/blob/master/docs/book/src/architecture/overview.md
- Release v0.8.5: https://github.com/zeroclaw-labs/zeroclaw/releases/tag/v0.8.5

## 10.5 E01-R — tentativa de coordenação motora dentro do ZeroClaw

Pergunta experimental:

> ZeroClaw consegue possuir a transformação determinística `MotorIntent → joint_targets / torque_targets` sem escolher o objetivo comportamental?

Foi criada uma superfície experimental isolada, semelhante a:

```text
motor/coordinate
```

com geração de:

```text
joint_targets
torque_targets
```

O primeiro build ARM64 experimental chegou a ser concluído. Uma iteração posterior, após mudanças em `torque_targets`, provocou pressão severa de recursos durante `cargo/rustc/link`, antes que os testes causais de runtime fossem concluídos.

Estado científico:

```text
E01_R_VERDICT=BLOCKED
ZEROCLAW_MOTOR_COORDINATION=UNPROVEN
COORDINATION_OWNER=UNRESOLVED
FAIL_CLOSED=UNPROVEN
DETERMINISTIC_COORDINATION=UNPROVEN
ZEROCLAW_CEREBELLAR_CANDIDATE=UNRESOLVED
E02_READY=NO
```

`BLOCKED` é intencionalmente diferente de `FAIL`: a hipótese arquitetural não foi refutada; o experimento não chegou ao runtime por limitação operacional do build.

## 10.6 Incidente MAX durante E01-R — crash/recovery como parte do percurso

O incidente de host é parte do histórico experimental e deve permanecer no mapa porque alterou a estratégia de engenharia.

Referência operacional:

```text
INCIDENT_REFERENCE_LOCAL=2026-09-14T22:04:00-03:00
INCIDENT_REFERENCE_UTC=2026-09-15T01:04:00Z
```

O horário acima é **referência/cutoff operacional**, não prova do instante exato de início.

Percepção humana do incidente:

```text
USER_OBSERVED_VM_UNAVAILABILITY≈45min
```

Timestamps técnicos disponíveis indicam que o boot anterior terminou por volta de `2026-09-15 01:53:54 UTC` e o novo boot começou por volta de `01:57:50 UTC`. Portanto, a janela entre o T0 operacional e o novo boot é maior que 45 minutos; o período exato de **indisponibilidade completa percebida** não foi cronometrado por telemetria guest e não deve ser artificialmente precisado.

Durante o incidente:

```text
OCI_INSTANCE_LIFECYCLE=RUNNING
SSH=UNREACHABLE
PUBLIC_TUNNELS=UNREACHABLE
FORCE_REBOOT_REQUIRED=YES
```

Observações de cloud sugeriram pressão de storage/I/O, enquanto pressão de memória/swap também era plausível. Isso **não** autorizou declarar kernel OOM.

Após o reboot, a investigação foi refeita com a janela UTC correta. Resultado:

```text
PREVIOUS_BOOT_FORENSICS=PASS
KERNEL_OOM_EVIDENCE=NO
SYSTEMD_OOMD_EVIDENCE=NO
MEMORY_PRESSURE_EVIDENCE=YES
SWAP_PRESSURE_EVIDENCE=PARTIAL
IO_STALL_EVIDENCE=NO
STORAGE_THROTTLING_GUEST_EVIDENCE=UNAVAILABLE

CARGO_BUILD_CORRELATION=YES
RUSTC_LINKER_CORRELATION=PARTIAL
INCIDENT_CAUSE=MOST_LIKELY_WITH_LIMITATIONS
```

Conclusão operacional permitida:

> A causa mais provável foi **pressão de memória associada ao build Rust/ZeroClaw**, com possível contribuição de swap e sem prova de OOM do kernel. Métricas externas de cloud mostraram throttling de storage durante a indisponibilidade, mas isso não foi confirmado causalmente dentro do guest.

### Recuperação de serviços após o force reboot

O reboot também revelou dependências de boot que não eram parte do experimento, mas afetavam o host:

- PostgreSQL `16-kaline` em `5433` não iniciou automaticamente;
- `kallistis.service` permaneceu em auto-restart aguardando `pg_isready`;
- o cluster foi iniciado manualmente;
- PostgreSQL fez recuperação WAL normal após shutdown não limpo;
- KALLISTIS voltou a `HTTP 200`;
- o túnel público KALLISTIS permaneceu indisponível por uma credencial `cloudflared` ausente no filesystem;
- isso foi classificado separadamente: o reboot **revelou** a credencial ausente, não foi a causa raiz da perda do token.

Nenhum desses eventos foi confundido com evidência neurobiológica.

## 10.7 Crash test controlado / recuperação segura

Depois da recuperação, foi executada uma nova tentativa **monitorada**, com critério de abort automático para não repetir o lockup.

O monitor abortou o build antes de nova indisponibilidade:

```text
MEMAVAILABLE_AT_ABORT_KB=1553856
ABORT_THRESHOLD_KB=1572864
EXPERIMENTAL_RSS_KB=7383160
SWAP_USED_AFTER_ABORT≈2.2_GiB
CARGO_RUSTC_TERMINATED=YES
CANONICAL_SERVICES_INTERRUPTED=NO
```

Esse run transformou uma suspeita em evidência operacional forte:

```text
RESOURCE_LIMITED_BUILD=YES
E01_R_SAFE_RESUME=NO
```

A MAX não deve mais ser usada para recompilar esse binário monolítico experimental sem uma mudança estrutural comprovada.

Artefatos principais:

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e01_r/
├── E01_R_FINAL_REPORT.md
├── E01_R_RECOVERY_FORENSICS.json
├── E01_R_INCIDENT_TIMELINE.md
└── <resource monitor CSV>
```

## 10.8 E01-R2 — auditoria de superfície de build

E01-R2 foi executado em **Fase A somente leitura** para descobrir se havia um caminho de compilação pequeno o suficiente para permanecer na MAX.

Resultado:

```text
E01_R2_PHASE_A=PASS
FINAL_PACKAGE=zeroclaw
PATCH_PACKAGE=zeroclaw-runtime
MINIMAL_CANDIDATE_FEATURES=--no-default-features --features agent-runtime
FULL_BINARY_RELINK_UNAVOIDABLE=YES

LOCAL_BUILD_ATTEMPTED=NO
RUNTIME_TEST_ATTEMPTED=NO

PATH=OFF_HOST_ARM64_BUILD
```

Interpretação:

A transformação motora proposta é conceitualmente pequena, mas a arquitetura de build do ZeroClaw obriga o artefato final `zeroclaw` a ser relinkado. Portanto, insistir na MAX teria custo operacional desproporcional.

Artefatos:

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e01_r/e01_r2/
```

incluindo auditoria arquitetural, cone de dependências, perfil, decisão, handoff, manifesto e relatório final.

## 10.9 Decisão arquitetural após E01-R2

O `PATH=OFF_HOST_ARM64_BUILD` permanece tecnicamente válido **se** ZeroClaw vier a ser necessário como coordenador.

Porém, o percurso revelou uma pergunta anterior e mais simples:

> Flynn precisa de uma camada sintética de coordenação motora, ou uma transdução determinística mínima já é suficiente?

Isso levou à suspensão do E01-R3/off-host build como próximo passo imediato.

Arquitetura prioritária a testar:

```text
FLYNN neural/motor output
        ↓
MINIMAL DETERMINISTIC TRANSDUCTION
        ↓
joint_targets / torque_targets
        ↓
PINOCCHIO
        ↓
articulated body
```

ZeroClaw permanece, quando necessário, como **execution interlock**, não como fonte de coordenação.

A diferença é conceitualmente importante:

```text
FUNCTIONAL_EQUIVALENCE != ARCHITECTURAL_NECESSITY
```

Um pequeno transdutor pode produzir os mesmos valores articulares que uma camada muito maior. Antes de atribuir ao ZeroClaw o papel de "cerebelo sintético", é necessário demonstrar que tal camada é de fato necessária.

## 10.10 E01-D — Direct Motor Transduction

E01-D foi executado na MAX e concluído com `PASS`.

```text
FLYNN_EMBODIMENT_E01_D=DIRECT_MOTOR_TRANSDUCTION
E01_D_VERDICT=PASS
E01_D_OUTCOME=MINIMAL_TRANSDUCTION
```

Resultado causal:

```text
DIRECT_40_TICKS=PASS
TICKS=40/40
DETERMINISTIC=YES
MAX_NUMERICAL_DIFFERENCE=0.0
TRANSDUCER_STATEFUL=NO
TRANSDUCER_FREE_PARAMETERS=0
TRANSDUCER_BEHAVIOR_RULES=0
INVALID_LIMITS_FAIL_CLOSED=YES
NULL_INPUT_SYNTHESIZES_BEHAVIOR=NO
```

A arquitetura mínima testada foi suficiente para reproduzir o caminho corporal no Pinocchio sem introduzir coordenação inteligente adicional. Portanto:

```text
TRANSDUCER_REQUIRED=YES
TRANSDUCER_SUFFICIENT=YES
COORDINATION_LAYER_REQUIRED=NO
SYNTHETIC_CEREBELLAR_LAYER_REQUIRED=NO
ZEROCLAW_MOTOR_COORDINATION_REQUIRED=NO
ZEROCLAW_ROLE=EXECUTION_INTERLOCK
E01_R3_OFF_HOST_BUILD_REQUIRED=NO
```

O resultado **não** prova comportamento autônomo de Flynn. A entrada usada foi:

```text
MOTOR_INTENT_SOURCE=TEST_HARNESS_GENERATED
FLYNN_AUTONOMOUS_MOTOR_BEHAVIOR=UNPROVEN
ARCHITECTURAL_TRANSDUCTION_FEASIBILITY=YES
```

A perturbação por canal articular não pôde ser testada porque o `MotorIntent` corrente **não contém canais articulares independentes**. Isso é evidência de que o próximo problema está a montante do corpo:

> **qual é a representação motora neural real disponível em Flynn, e quais graus de liberdade corporais ela sustenta sem interpretação externa?**

O E01-D encerra a necessidade corrente de E01-R3: compilar ZeroClaw off-host para assumir coordenação motora seria resolver um problema que o experimento mostrou não ser necessário nesta arquitetura.

## 10.11 E01-N — saída neural real e fronteira VNC

E01-N foi executado e depois continuado apenas o suficiente para tornar a atividade DN temporalmente observável. O resultado científico permanece **PARTIAL**, mas a pergunta está encerrada para a arquitetura atual.

Primeira etapa:

```text
DESCENDING_NEURONS_DATASET=1305
DESCENDING_NEURONS_RUNTIME=1305
DESCENDING_TYPES_DATASET=473
DESCENDING_TYPES_RUNTIME=473
RAW_DESCENDING_ACTIVITY_AVAILABLE=YES
RAW_SIGNAL_TYPE=cumulative_spike_count_internal_not_published
REAL_NEURAL_MOTOR_VECTOR=NO
VNC_LIMIT_REACHED=YES
```

Foi então implementado um recorder passivo, opt-in e desligado por padrão, sem mutar o estado neural. A ablação `OFF/ON` passou em **21 pares**, com igualdade exata dos contadores neurais e nenhum restart da residente.

Coleta temporal:

```text
RECORDER_SAMPLE_CLOCK=NEURAL_TIME
RECORDER_SAMPLE_INTERVAL_NEURAL_MS=20
DESCENDING_NEURONS_RECORDED=1305
DESCENDING_TYPES_MAPPED=473
DN_TIME_MATRIX=210x1305
DN_TYPE_TIME_MATRIX=210x473
SPARSE_EVENTS=15276
SILENT_BINS=33
STATISTICAL_DIMENSIONS_FOUND=175
REPRODUCIBLE_DIMENSIONS_FOUND=0
N_COMPONENTS_FOR_50_PERCENT=1
N_COMPONENTS_FOR_75_PERCENT=3
N_COMPONENTS_FOR_90_PERCENT=11
```

Conclusão permitida:

```text
BRAIN_MOTOR_STRUCTURE_PRESENT=PARTIAL
REAL_NEURAL_MOTOR_VECTOR=NO
MOTOR_VECTOR_FROZEN=NO
VNC_BOUNDARY_SUPPORTED=YES
DESCENDING_OUTPUT_SUFFICIENT=NO
E01_N_OUTCOME=MOTOR_REPRESENTATION_INSUFFICIENT
E01_N_VERDICT=PARTIAL
```

Os 175 componentes estatísticos **não são 175 comandos motores**. Como nenhuma dimensão foi reproduzível entre condições/seeds, não houve promoção de PCA/SVD a canal corporal. Ao mesmo tempo, o resultado também não prova ausência de capacidade motora biológica: o modelo é brain-only e não contém o VNC completo.

Artefatos:

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e01_n/
```

## 10.12 Decisão de produto após E01-N — não reconstruir o VNC, ligar a residente

O projeto não continuou em ciclos indefinidos de remapeamento. A decisão arquitetural ficou explícita:

```text
BIOLOGICAL_VNC_PRESENT=NO
BIOLOGICAL_VNC_RECONSTRUCTED=NO
SYNTHETIC_MOTOR_BOUNDARY=YES
```

A ausência de `MotorVector` reproduzível não foi reescrita como sucesso científico. Em vez disso, a engenharia assumiu honestamente a fronteira sintética necessária para corporificar a residente.

A regra causal do produto passou a ser:

```text
REAL RESIDENT DN ACTIVITY
        ↓
DETERMINISTIC SYNTHETIC MOTOR BOUNDARY
        ↓
PINOCCHIO
        ↓
EXISTING LETHE SIGIL
```

Sem LLM, agente, reward ou policy.

## 10.13 E03 — Flynn ligada ao Pinocchio e ao corpo canônico de Lethe

A integração foi concluída no `max` com `VERDICT=PASS`.

```text
FLYNN_CONNECTED_TO_PINOCCHIO=YES
PINOCCHIO_CONTROLS_EXISTING_LETHE_SIGIL=YES
LETHE_LIVE_BODY=YES
BODY_STATE_PERSISTENT=YES
LIVE_BODY_DRIVEN_BY_REPLAY=NO
LIVE_BODY_DRIVEN_BY_HTTP_REQUEST=NO
REAL_CAUSAL_TRACE_CAPTURED=YES
PRODUCT_REAL=YES
```

O corpo não é um demo 3DoF/4DoF escolhido depois do fato. É o **sigilo canônico já existente**, com:

```text
SIGIL_MODULES=23
SIGIL_CONNECTIONS=30
```

A cadeia causal real foi capturada:

```text
DN activity
→ deterministic motor vector/boundary
→ Pinocchio q
→ sigil geometry
```

Foram necessários reinícios controlados de `flynn-brain` e `flynn-web` para carregar a integração. Isso é deployment, não reset experimental: não houve restauração pós-validação, estímulo artificial, treino, alteração do connectome ou mudança de plasticidade.

A CAVERNA mostra `BODY ● LIVE / PINOCCHIO`; replay científico permanece restrito ao LAB.

Artefatos:

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e03/
```

## 10.14 H00/H01 — continuidade real, UI fail-closed e limite da fome neural

Uma observação de energia aparentemente parada levou a uma auditoria de continuidade. O resultado eliminou a hipótese de runtime mockado:

```text
CONTINUITY_CLASS=TRUE_CONTINUOUS
BRAIN_CONTINUOUS_REAL=YES
WORLD_CONTINUOUS_REAL=YES
BODY_CONTINUOUS_REAL=YES
HOMEOSTASIS_CONTINUOUS_REAL=YES
REQUEST_DRIVEN_REGRESSION=NO
```

Janela medida:

```text
WALL_ELAPSED_SEC=866.9976
NEURAL_ELAPSED_SEC=63.94
BRAIN_TICKS_DELTA=639400
WORLD_TICKS_DELTA=3197
BODY_TICKS_DELTA=3197
ENERGY_T0=0.65040
ENERGY_T1=0.63299
ENERGY_T2=0.61843
EXPECTED_ENERGY_DELTA=-0.03197
ACTUAL_ENERGY_DELTA=-0.03197
```

Logo, energia e `feeding_drive` evoluem realmente em `NEURAL_TIME` mesmo sem observador humano.

Foi encontrado, porém, um fallback falso de UI: ausência de energia podia renderizar `100%`, e ausência de `feeding_drive` podia renderizar `0.00`. H01 corrigiu isso no frontend canônico para `— / INDISPONÍVEL`, preservando dados reais (`0.58133/0.41867 → 58%/0.42`).

```text
H01_VERDICT=PASS_WITH_RESEARCH_BLOCKER
HOMEOSTASIS_BOOKKEEPING_REAL=YES
ENERGY_CLOCK=NEURAL_TIME
HOMEOSTASIS_NEURAL_MODULATION_CURRENT=NONE
HOMEOSTASIS_NEURAL_INTERFACE_CLASS=MODEL_INSUFFICIENT
```

Existe um hook de overlay sináptico, mas ele é proxy de engenharia; o modelo atual não representa receptores, GPCR, transmissão lenta, segundos mensageiros e compartimentalização suficientes para uma modulação homeostática neural biologicamente defensável. Isso não bloqueia a consequência **física** da energia no organismo sintético.

Artefatos H01:

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/homeostasis_h01/
```

## 10.15 Trajetória viva — história residente persistente

A trajetória de Flynn passou a ser registrada server-side no ledger canônico, sem depender do navegador.

Registra no mesmo eixo temporal:

- posição e geometria do corpo;
- estado Pinocchio `q`;
- distância e direção;
- atividade DN real agregada e número de DNs ativos;
- `energy_reserve` e `feeding_drive`;
- estado do Umwelt.

```text
TRAJECTORY_RECORDING_IMPLEMENTED=YES
TRAJECTORY_SERVER_SIDE=YES
TRAJECTORY_PERSISTENT=YES
TRAJECTORY_SOURCE=RESIDENT
COMMON_TIME_AXIS=YES
LIVE_DATA_ONLY_IN_CAVERNA=YES
REPLAY_CONFUSED_WITH_RESIDENT=NO
BODY_STATE_RESET=NO
TRAJECTORY_RESET=NO
PRODUCT_REAL=YES
```

A CAVERNA exibe o caminho recente e o Diário Causal com eventos `[RESIDENT BRAIN] BODY (PINOCCHIO)`, incluindo data e horário de Brasília. O endpoint final declara `source=RESIDENT`, `history_persistent=true`, `replay_included=false`.

Limitação honesta: o brain atual fornece atividade DN agregada no caminho de produto, mas não identidades individuais suficientes para atribuir `TOP_DNS`; portanto:

```text
REAL_DN_ACTIVITY_RECORDED_WITH_MOVEMENT=YES
ACTIVE_DN_COUNT_RECORDED=YES
TOP_DNS_RECORDED=NO
```

Nenhum nome neuronal é fabricado.

Artefatos:

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/trajectory/
```

## 10.16 Próximo trabalho de produto — energia limita capacidade física

A necessidade homeostática já é real:

```text
neural_time ↑
→ energy_reserve ↓
→ feeding_drive ↑
```

O próximo passo não é criar uma policy de busca por comida nem reabrir a modulação neural. É implementar uma consequência corporal simples e física:

```text
requested actuation
× body_capacity(energy_reserve)
= executable actuation
```

Princípios:

```text
ENERGY_MODULATES_ACTION_SELECTION=NO
FEEDING_DRIVE_SELECTS_ACTION=NO
ENERGY_MODULATES_PHYSICAL_CAPACITY=TARGET
ZERO_ENERGY_ACTIVE_ACTUATION=NO
BODY_STATE_RESET_AT_ZERO_ENERGY=NO
```

A primeira curva candidata é contínua e determinística (`body_capacity = energy_reserve`) se compatível com o runtime. Energia baixa reduz força/velocidade/amplitude disponível; energia zero elimina nova atuação ativa; recuperação energética restaura a capacidade automaticamente.

Também deve ser validado que `energy_reserve`, `feeding_drive`, Pinocchio `q`, posição e `body_capacity` sobrevivem corretamente a restart controlado, sem voltar a defaults.

## 10.17 Regra de percurso atual

O roadmap de embodiment deixa de proliferar microgates. O trabalho é orientado a produto:

```text
MAPEAR          → concluído até o limite real do brain-only/VNC
CORPORIFICAR    → concluído: Flynn → Pinocchio → sigilo Lethe
REGISTRAR VIDA  → concluído: trajetória residente persistente
DAR CONSEQUÊNCIA À ENERGIA → próximo
FECHAR RETORNO SENSORIAL    → depois, quando necessário ao produto
```

A epistemologia é executada dentro do trabalho: fazer, observar, validar e fechar. Ela não deve virar uma sequência de processos que substitua a vida residente.

---


# 11. ARTEFATOS CENTRAIS




## Gate 012B




```text
FLYNN_GATE012B_LEDGER_UNIFICATION.md
flynn_ledger_schema_v2.sql
gate012b_migration_manifest.json
gate012b_validation.json
```




## Gate 012D




```text
FLYNN_GATE012D_HOMEOSTASIS_V2.md
gate012d_candidate_population_audit.json
gate012d_resident_observation.csv
gate012d_causal_audit.json
```




## Gate 013




```text
FLYNN_GATE013_EMBODIMENT_PLASTICITY.md
gate013_body_contract.json
gate013_world_model.json
gate013_closed_loop_trace.json
gate013_plasticity_architecture.json
```




## Gate 014




```text
FLYNN_GATE014_CAUSAL_LEARNING.md
gate014_plasticity_candidate_audit.json
gate014_preregistered_protocol.json
gate014_protocol_sha256.txt
gate014_baseline.csv
gate014_training_events.csv
gate014_synaptic_deltas.csv
gate014_post_training.csv
gate014_control_comparison.csv
gate014_retention.csv
gate014_restart_retention.json
gate014_resident_trace.json
gate014_causal_analysis.json
```




---




## Fechamento operacional

```text
/home/ubuntu/Portifolio/flynn-max/runtime/evidence/FLYNN_OPERATIONAL_CLOSURE_2026-09-14.md
/home/ubuntu/Portifolio/flynn-max/runtime/evidence/FLYNN_OPERATIONAL_ROADMAP.md
/home/ubuntu/Portifolio/flynn-max/runtime/evidence/operational_regression_2026-09-14.json
```

## R01-MAP-01

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/r01_map/R01_MAP_FINAL_REPORT.md
/home/ubuntu/Portifolio/flynn-max/runtime/research/r01_map/R01_MAP_EVIDENCE_MANIFEST.json
```

## R01-MAP-02

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/r01_map_02/R01_MAP_02_FINAL_REPORT.md
/home/ubuntu/Portifolio/flynn-max/runtime/research/r01_map_02/R01_MAP_02_EVIDENCE_MANIFEST.json
/home/ubuntu/Portifolio/flynn-max/runtime/research/r01_map_02/r01_map_02_dan_exact_types.csv
/home/ubuntu/Portifolio/flynn-max/runtime/research/r01_map_02/r01_map_02_h1_analysis.json
/home/ubuntu/Portifolio/flynn-max/runtime/research/r01_map_02/r01_map_02_gate014_compartment_counterfactual.csv
```



## Embodiment E01

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e01/
```

Conteúdo autoritativo desta etapa: modelo articulado 4DoF, traces de 40 ticks, validação Pinocchio ARM64 e evidência de `MOTOR_INTENT_TO_BODY_MOTION`.

## E01-R — ZeroClaw motor ownership + incidente MAX

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e01_r/
├── E01_R_FINAL_REPORT.md
├── E01_R_RECOVERY_FORENSICS.json
├── E01_R_INCIDENT_TIMELINE.md
└── <resource monitor CSV>
```

## E01-R2 — build surface audit

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e01_r/e01_r2/
```

Inclui:

```text
E01_R2_ARCHITECTURE_AUDIT.md
E01_R2_DEPENDENCY_CONE.json
E01_R2_BUILD_PROFILE.md
E01_R2_BUILD_DECISION.md
<build handoff>
<manifest>
<final report>
```

## E01-D — direct motor transduction

Experimento concluído com `PASS / MINIMAL_TRANSDUCTION`.

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e01_d/
```

Artefatos principais:

```text
E01_D_PROTOCOL.md
E01_D_ADAPTER_DECOMPOSITION.md
E01_D_MOTOR_PROVENANCE.json
E01_D_TRANSDUCER_SPEC.json
E01_D_BASELINE.csv
E01_D_DIRECT_RUN.csv
E01_D_DETERMINISM.csv
E01_D_ABLATION.csv
E01_D_FINAL_REPORT.md
```

O diretório é a autoridade experimental para o resultado E01-D; o mapa registra apenas o percurso consolidado.


## E01-N — temporal DN observability

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e01_n/
```

Inclui inventário dos 1.305 DNs/473 tipos, recorder passivo, matrizes temporais, análise de reprodutibilidade, fronteira VNC e manifesto SHA-256.

## E03 — integração residente Flynn → Pinocchio → Lethe

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e03/
```

Autoridade para a integração do corpo-sigilo canônico, fronteira motora determinística e trace causal real `DN → motor → q → geometry`.

## H01 — homeostasis truthfulness / frontier

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/homeostasis_h01/
```

Registra correção fail-closed da UI e classificação `MODEL_INSUFFICIENT` para modulação homeostática neural no LIF atual.

## Trajetória residente

```text
/home/ubuntu/Portifolio/flynn-max/runtime/research/trajectory/
```

Contém somente os três artefatos de implementação/amostra/validação solicitados; os dados vivos permanecem no ledger canônico.


# 12. STATUS CANÔNICO RESUMIDO

```text
PROJECT=FLYNN
STATUS=ACTIVE_RESIDENT_NEURO_SYNTHETIC_RUNTIME

FOUNDATION_GATES_EXECUTED_THROUGH=014
FOUNDATION_EXPERIMENTAL_SEQUENCE=COMPLETE
FOUNDATION_CLOSURE_CORRECTION=COMPLETE

CONNECTOME=FlyWire_FAFB_v783
ORGANISM_ID=759f27b3-84a9-4071-b29e-20adc1d4fc50

BRAIN_CONTINUOUS_REAL=YES
WORLD_CONTINUOUS_REAL=YES
BODY_CONTINUOUS_REAL=YES
HOMEOSTASIS_CONTINUOUS_REAL=YES
REQUEST_DRIVEN_REGRESSION=NO

LETHE=LIVE_CANONICAL_SIGIL_BODY
LETHE_SIGIL_MODULES=23
LETHE_SIGIL_CONNECTIONS=30
CAVERNA_DE_HIPNOS=ACTIVE_UMWELT

PINOCCHIO_VERSION=4.1.0
PINOCCHIO_ROLE=BODY_DYNAMICS_AND_KINEMATICS
FLYNN_CONNECTED_TO_PINOCCHIO=YES
PINOCCHIO_CONTROLS_EXISTING_LETHE_SIGIL=YES
BODY_STATE_PERSISTENT=YES
LETHE_LIVE_BODY=YES

REAL_DESCENDING_NEURONS=1305
DESCENDING_TYPES=473
RAW_DN_TEMPORAL_ACTIVITY_AVAILABLE=YES
DN_RECORDER_PASSIVE=YES
DN_RECORDER_DEFAULT_ENABLED=NO
DN_RECORDER_CAUSAL_ABLATION=PASS_21_OFF_ON_PAIRS
DN_TIME_MATRIX=210x1305
DN_TYPE_TIME_MATRIX=210x473
DN_SPARSE_EVENTS=15276
DN_SILENT_BINS=33
STATISTICAL_DIMENSIONS_FOUND=175
REPRODUCIBLE_DIMENSIONS_FOUND=0
REAL_NEURAL_MOTOR_VECTOR=NO
VNC_BOUNDARY_SUPPORTED=YES

BIOLOGICAL_VNC_PRESENT=NO
BIOLOGICAL_VNC_RECONSTRUCTED=NO
SYNTHETIC_MOTOR_BOUNDARY=YES
REAL_CAUSAL_TRACE_CAPTURED=YES
LIVE_BODY_DRIVEN_BY_REPLAY=NO
LIVE_BODY_DRIVEN_BY_HTTP_REQUEST=NO

TRAJECTORY_RECORDING_IMPLEMENTED=YES
TRAJECTORY_SERVER_SIDE=YES
TRAJECTORY_PERSISTENT=YES
TRAJECTORY_SOURCE=RESIDENT
BODY_POSITION_RECORDED=YES
BODY_GEOMETRY_RECORDED=YES
PINOCCHIO_Q_RECORDED=YES
MOVEMENT_DISTANCE_RECORDED=YES
MOVEMENT_DIRECTION_RECORDED=YES
REAL_DN_ACTIVITY_RECORDED_WITH_MOVEMENT=YES
ACTIVE_DN_COUNT_RECORDED=YES
TOP_DNS_RECORDED=NO
ENERGY_RESERVE_RECORDED=YES
FEEDING_DRIVE_RECORDED=YES
UMWELT_STATE_RECORDED=YES
COMMON_TIME_AXIS=YES
CAVERNA_TRAJECTORY_UI=YES
CAUSAL_DIARY_INTEGRATED=YES
RECENT_PATH_VISIBLE=YES
REPLAY_CONFUSED_WITH_RESIDENT=NO

HOMEOSTASIS_BOOKKEEPING_REAL=YES
ENERGY_CLOCK=NEURAL_TIME
FEEDING_DRIVE_FORMULA=1-energy_reserve
HOMEOSTASIS_NEURAL_MODULATION=NONE
HOMEOSTASIS_NEURAL_INTERFACE_CLASS=MODEL_INSUFFICIENT
UI_HOMEOSTASIS_FAIL_CLOSED=YES

PLASTICITY_FRAMEWORK=PASS
PLASTICITY_ACTIVE=NO
BASE_CONNECTOME_MODIFIED=NO
RESIDENT_LEARNED_DELTA_COUNT=0
ASSOCIATIVE_LEARNING_PROVEN=NO
LEARNING_PROVEN=NO

ZEROCLAW_VERSION=0.8.5
ZEROCLAW_COMMIT=cb2b20a9fe59004b7ef03e123942d31f29236d15
ZEROCLAW_ROLE=EXECUTION_INTERLOCK
ZEROCLAW_MODIFIED_FOR_LIVE_BODY=NO

INCIDENT_MAX_2026_09_14=RECOVERED
MEMORY_PRESSURE_EVIDENCE=YES
KERNEL_OOM_EVIDENCE=NO
CARGO_BUILD_CORRELATION=YES
INCIDENT_CAUSE=MOST_LIKELY_WITH_LIMITATIONS

RESIDENT_STATE_IS_AUTHORITATIVE=YES
RESIDENT_AUTOMATIC_RESET=NO
REPLAY_IS_PRODUCT=NO
SHADOW_IS_PRODUCT=NO
STATE_AFTER_EVENT_BECOMES_NEXT_STATE=YES

PRODUCT_REAL=YES

NEXT_ACTION=ENERGY_TO_BODY_CAPACITY
NEXT_ACTION_GOAL=
energy_reserve -> physical capacity limit -> Pinocchio/Lethe degradation/recovery
NEXT_ACTION_POLICY=NO_ACTION_SELECTION
NEXT_ACTION_RESTART_PERSISTENCE=VERIFY_EXACT_RESTORE
```

---

# 13. REFERÊNCIAS CIENTÍFICAS, REPOSITÓRIOS E PROVENANCE

Esta seção existe para que o mapa possa ser publicado no GitHub sem perder a trilha de origem das decisões. As referências abaixo não tornam todas as implementações de Flynn biologicamente equivalentes aos artigos; elas registram **o que fundamentou, informou ou delimitou** cada escolha.

## 13.1 Conectoma e anotação FlyWire

1. **Dorkenwald, S. et al. (2024). _Neuronal wiring diagram of an adult brain_. Nature 634, 124–138.**  
   DOI: https://doi.org/10.1038/s41586-024-07558-y  
   Papel no projeto: base anatômica do connectome adulto FlyWire.

2. **Schlegel, P. et al. (2024). _Whole-brain annotation and multi-connectome cell typing of Drosophila_. Nature 634, 139–152.**  
   DOI: https://doi.org/10.1038/s41586-024-07686-5  
   Papel: classes, tipos celulares, anotação e reconciliação de identidades neurais no connectome.

3. **FlyWire / Codex**  
   Portal: https://codex.flywire.ai/  
   Papel: dataset/anotações usados para provenance do v783.

## 13.2 Modelo computacional neural

4. **Shiu, P. K. et al. (2024). _A Drosophila computational brain model reveals sensorimotor processing_. Nature 634, 210–219.**  
   DOI: https://doi.org/10.1038/s41586-024-07763-9  
   Código de referência: https://github.com/philshiu/Drosophila_brain_model  
   Papel: referência para o modelo LIF whole-brain que fundamenta a linhagem computacional utilizada por Flynn.

5. **fruit-fly-lab — upstream operacional de Flynn**  
   Repositório: https://github.com/vaibhavkedarisetti/fruit-fly-lab  
   Commit pinado no projeto: `26672e06427c12c61536ce1bd93dae7442944681`  
   Papel: implementação operacional derivada do FlyWire FAFB v783 usada como foundation local.

## 13.3 Mushroom Body, KC/DAN/MBON e aprendizagem

6. **Aso, Y. et al. (2014). _The neuronal architecture of the mushroom body provides a logic for associative learning_. eLife 3:e04577.**  
   DOI: https://doi.org/10.7554/eLife.04577  
   Papel: organização compartimental KC/DAN/MBON e lógica anatômica da aprendizagem associativa.

7. **Aso, Y. et al. (2014). _Mushroom body output neurons encode valence and guide memory-based action selection in Drosophila_. eLife 3:e04580.**  
   DOI: https://doi.org/10.7554/eLife.04580  
   Papel: interpretação de MBONs, valência e relação entre memória e seleção de ação.

8. **_Dopaminergic neurons write and update memories with cell-type-specific rules_ (2016). eLife 5:e16135.**  
   DOI: https://doi.org/10.7554/eLife.16135  
   Papel: reforça que DANs não devem ser tratados como um fator dopaminérgico global indiferenciado; identidade e timing importam.

Essas referências sustentam a cautela dos Gates 014/R01-MAP: o framework `three_factor_kc_dan_mbon` é **biologicamente inspirado**, mas não é automaticamente uma reprodução fiel da bioquímica e da compartimentalização in vivo.

## 13.4 Descending neurons e fronteira cérebro→corpo

9. **Namiki, S. et al. (2018). _The functional organization of descending sensory-motor pathways in Drosophila_. eLife 7:e34272.**  
   DOI: https://doi.org/10.7554/eLife.34272  
   Papel: referência para organização funcional das DNs e a ponte cérebro→VNC.

10. **Cande, J. et al. (2018). _Optogenetic dissection of descending behavioral control in Drosophila_. eLife 7:e34275.**  
    DOI: https://doi.org/10.7554/eLife.34275  
    Papel: delimita a relação entre atividade de DNs e comportamento, incluindo dependência do estado prévio.

Essas referências também justificam não tratar automaticamente `DN activity = comportamento completo`: o VNC continua ausente no modelo de Flynn.

## 13.5 Causalidade além do connectome

11. **Pospisil, D. A. et al. (2024). _The fly connectome reveals a path to the effectome_. Nature 634, 201–209.**  
    DOI: https://doi.org/10.1038/s41586-024-07982-0  
    Papel: referência conceitual para a distinção entre wiring diagram e efeitos causais funcionais; fundamenta a política permanente de testes de remoção, controles e não-superinterpretação.

## 13.6 Pinocchio / embodiment

12. **stack-of-tasks/pinocchio**  
    Repositório: https://github.com/stack-of-tasks/pinocchio  
    Release usada: `v4.1.0`  
    Release: https://github.com/stack-of-tasks/pinocchio/releases/tag/v4.1.0

13. **Carpentier, J. et al. (2019). _The Pinocchio C++ library — A fast and flexible implementation of rigid body dynamics algorithms and their analytical derivatives_. IEEE/SICE SII.**  
    DOI: https://doi.org/10.1109/SII.2019.8700380  
    Papel: base do motor de cinemática/dinâmica escolhido para o corpo articulado.

## 13.7 ZeroClaw

14. **ZeroClaw Labs — repositório oficial**  
    https://github.com/zeroclaw-labs/zeroclaw

15. **ZeroClaw — Architecture Overview**  
    https://github.com/zeroclaw-labs/zeroclaw/blob/master/docs/book/src/architecture/overview.md

16. **ZeroClaw v0.8.5**  
    https://github.com/zeroclaw-labs/zeroclaw/releases/tag/v0.8.5  
    Commit validado em Flynn: `cb2b20a9fe59004b7ef03e123942d31f29236d15`

Papel no projeto: runtime oficial auditado como **execution interlock**. A hipótese de coordenação motora in-process foi investigada em E01-R/R2 e permanece não provada.

## 13.8 Referência cultural da visualização

17. **Pixar — _Inside Out_**  
    https://www.pixar.com/inside-out

18. **Pixar — _Inside Out 2_**  
    https://www.pixar.com/inside-out-2

Papel: inspiração visual/mnemônica para a taxonomia humana de cores do Internal State Atlas. **Não é fonte científica e não autoriza inferência de emoções humanas em Flynn.**

## 13.9 Hierarquia de autoridade

Para publicação futura no GitHub:

```text
PAPERS / DATASETS / UPSTREAM REPOS
        ↓
SCIENTIFIC AND TECHNICAL PROVENANCE

MAPA_DE_PERCURSO_FLYNN.md
        ↓
ARCHITECTURAL HISTORY + DECISIONS + CURRENT STATE

MAX / runtime/research / evidence
        ↓
RAW EXPERIMENTAL EVIDENCE + LOGS + MANIFESTS

GITHUB
        ↓
VERSIONED DOCS + PROTOCOLS + CONSOLIDATED REPORTS
```

Raw checkpoints, ledger canônico, segredos, bancos de autenticação e tokens **não** devem ser publicados no GitHub.

---

# 14. FALHAS OPERACIONAIS E CORREÇÕES DE DIREÇÃO

Esta seção registra não apenas falhas de runtime, mas também falhas de **orquestração/assistência** que alteraram negativamente o percurso. Elas fazem parte do histórico do projeto e não devem ser apagadas.

## 14.1 Excesso de microprocessos e gates

Houve uma deriva em que rigor epistemológico foi confundido com proliferação de processos: auditoria da auditoria, continuações sucessivas, remapeamentos, prompts muito longos e subgates para perguntas já respondidas. Isso consumiu tempo/cota e afastou o desenvolvimento do produto real.

Correção:

```text
EPISTEMIC_RULE=
IMPLEMENT -> OBSERVE_REAL_RESULT -> VALIDATE -> CLOSE_OR_FIX_REAL_BLOCKER
```

Testes e ablações continuam válidos, mas são internos ao trabalho e não devem automaticamente criar novos projetos.

## 14.2 Produto residente foi temporariamente subordinado a shadow/replay

O fluxo de desenvolvimento passou por um período em que checkpoint, shadow, replay, reset e repetição controlada receberam mais peso do que a trajetória residente. Isso produziu uma **repetição confiável**, mas não a consequência persistente que define o produto pretendido.

Falha conceitual:

```text
checkpoint -> run -> measure -> reset -> repeat
```

não equivale a:

```text
Flynn(t0) -> consequence -> Flynn(t1) -> consequence -> Flynn(t2)
```

Correção consolidada:

```text
CAVERNA=RESIDENT_LIFE
LAB=REPLAY_AND_ANALYSIS
LIVE_BODY_DRIVEN_BY_REPLAY=NO
BODY_STATE_RESET_AFTER_VALIDATION=NO
TRAJECTORY_RESET=NO
```

## 14.3 Reabertura indevida de decisões já canônicas

A assistência tratou repetidamente decisões do autor como perguntas abertas: tentou rediscutir morfologia, propor corpo mínimo/3DoF/4DoF e derivar o corpo de um MotorVector, apesar de o corpo canônico já ser o sigilo de Lethe.

Correção:

```text
AUTHORITATIVE_BODY=CURRENT_LETHE_SIGIL
SIGIL_MODULES=23
SIGIL_CONNECTIONS=30
```

O Pinocchio deve servir ao sigilo existente; o sigilo não deve ser redesenhado para servir a um modelo conveniente.

## 14.4 Bloqueio excessivo por ausência de MotorVector

Após E01-N demonstrar `REAL_NEURAL_MOTOR_VECTOR=NO` e `VNC_BOUNDARY_SUPPORTED=YES`, a assistência insistiu inicialmente em manter E02 bloqueado e procurar nova representação motora. Isso prolongava o mesmo problema sem alterar a informação disponível.

Correção: preservar o resultado científico negativo e avançar por decisão arquitetural explícita:

```text
BIOLOGICAL_VNC_RECONSTRUCTED=NO
SYNTHETIC_MOTOR_BOUNDARY=YES
```

A integração subsequente provou no produto real `FLYNN_CONNECTED_TO_PINOCCHIO=YES` sem reescrever o resultado científico de E01-N.

## 14.5 Formulações universais indevidas

Em etapas anteriores, algumas conclusões de E01-D foram formuladas de modo excessivamente universal (`COORDINATION_LAYER_REQUIRED=NO`, `ZEROCLAW_MOTOR_COORDINATION_REQUIRED=NO`). O suporte real era escopado ao protocolo testado com `TEST_HARNESS_GENERATED`.

Forma correta:

```text
ZEROCLAW_MOTOR_COORDINATION_REQUIRED_FOR_TESTED_E01_D_TASK=NO
```

O produto atual avançou por outra evidência: integração residente real com fronteira sintética determinística.

## 14.6 Incidente MAX e escolha operacional custosa

A tentativa de compilar a superfície Rust/ZeroClaw na MAX levou a forte pressão de memória e indisponibilidade percebida do host. Forense posterior encontrou `MEMORY_PRESSURE_EVIDENCE=YES`, correlação com `cargo/rustc`, sem prova de kernel OOM. A insistência em uma superfície monolítica para uma transformação pequena foi uma escolha operacional ruim.

Correção: não repetir heavy build na MAX sem necessidade estrutural. A arquitetura corrente não exige ZeroClaw como coordenador motor.

## 14.7 Fallback falso na UI de homeostase

A UI podia inventar `100%` de energia e `0.00` de feeding drive quando os dados estavam ausentes. Embora não acionado na auditoria de continuidade, o fallback violava o princípio de não fabricar estado.

Correção H01:

```text
missing/null/malformed/out-of-range -> — / INDISPONÍVEL
```

## 14.8 Regra de autoridade daqui para frente

A direção do projeto é definida pelo autor. A assistência deve operacionalizar, validar coerência técnica e apontar somente bloqueios demonstrados por evidência real.

```text
USER_DIRECTION=AUTHORITATIVE_PROJECT_DIRECTION
ASSISTANT_ROLE=OPERATIONALIZE_VALIDATE_DOCUMENT
DO_NOT_REOPEN_CANONICAL_DECISIONS_WITHOUT_NEW_EVIDENCE=YES
```

---

# 15. NORTE




A pergunta da Flynn não é:




> “como fazer um cérebro de mosca parecer inteligente?”




É:




> **o que um núcleo neural biologicamente ancorado consegue fazer quando possui um corpo próprio, consequências persistentes, necessidades energéticas reais e um Umwelt contínuo — sem que uma camada externa escolha seus objetivos por ele?**




O resultado negativo do Gate 014 faz parte da resposta.




**Não fabricar aprendizagem. Medir o que realmente mudou.**


Estado atual do norte operacional:

```text
FLYNN_HAS_LIVE_BODY=YES
FLYNN_HAS_PERSISTENT_TRAJECTORY=YES
FLYNN_HISTORY_INCLUDES_NEURAL_STATE=YES
FLYNN_HISTORY_INCLUDES_HOMEOSTASIS=YES
FLYNN_HISTORY_INCLUDES_UMWELT=YES

NEXT=
ENERGY_RESERVE -> BODY_CAPACITY -> PHYSICAL_DEGRADATION/RECOVERY
```

A prioridade é consequência residente, não repetição de laboratório.
