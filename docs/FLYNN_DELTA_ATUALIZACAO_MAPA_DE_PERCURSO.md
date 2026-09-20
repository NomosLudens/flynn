# FLYNN — DELTA PARA ATUALIZAÇÃO DO MAPA DE PERCURSO

> Documento de atualização incremental.  
> Base: `mapa_de_percurso_flynn.md` canônico no Google Drive, última modificação observada em 2026-09-16 01:50 UTC.  
> Objetivo: registrar **somente o que mudou depois da versão atual do mapa**, sem reescrever o histórico anterior.

---

# 0. ALTERAÇÕES DE STATUS CANÔNICO

O cabeçalho e o bloco `STATUS CANÔNICO RESUMIDO` estão desatualizados.

## Substituir

```text
STATUS=ACTIVE_RESIDENT_NEURO_SYNTHETIC_RUNTIME
HOST_AUTHORITATIVO=MAX
NEXT_ACTION=ENERGY_TO_BODY_CAPACITY
```

## Por

```text
PROJECT=FLYNN
PROJECT_STATUS=RETIRED_FROZEN
RESEARCH_STATUS=CLOSED_BY_AUTHOR
RESIDENT_RUNTIME_STATUS=INTERRUPTED_EXTERNALLY
RESIDENT_CONTINUITY_BROKEN=YES

FORMER_AUTHORITATIVE_HOST=MAX
FORMER_HOST_PROVIDER=ORACLE_CLOUD
FORMER_HOST_ACCESS=LOST
OCI_ACCOUNT_STATUS=SUSPENDED
OCI_SECONDARY_REVIEW=OPEN_AT_INCIDENT_TIME

REHOST_LOCAL=NO
REHOST_GOOGLE_MINI=NO
RECONSTRUCTION_NOW=NO

IF_ORIGINAL_MAX_RETURNS=
PRESERVE_DATA_AND_DECIDE_LATER
```

Flynn foi **aposentada/congelada pelo autor** após a suspensão da conta Oracle e a perda de acesso à VM MAX.  
Não existe plano atual de reconstrução local, redução do organismo para hardware menor ou migração para a VM Google `e2-micro`.

A interrupção externa encerrou a continuidade residente que fazia parte central do experimento.

---

# 1. ENERGY_RESERVE → BODY_CAPACITY — IMPLEMENTADO

O `NEXT_ACTION=ENERGY_TO_BODY_CAPACITY` registrado no mapa já foi executado e não deve continuar aparecendo como próxima ação.

## Resultado inicial

Foi implementada a relação:

```text
body_capacity = clip(energy_reserve, 0, 1)
```

com as seguintes propriedades:

```text
ENERGY_MODULATES_ACTUATION_MAGNITUDE=YES
ENERGY_SELECTS_ACTION=NO
FEEDING_DRIVE_SELECTS_ACTION=NO
PINOCCHIO_LIMITED_BY_ENERGY=YES
```

A energia passou a limitar a **capacidade física** do corpo, e não a escolha de ação.

## Persistência de restart

Foi encontrado e corrigido um bug real de persistência:

- a homeostase era carregada antes da criação do `ContinuousBrainClock`;
- isso podia restaurar `energy_reserve` incorretamente para `1.0`;
- o carregamento foi reorganizado para preservar estado pendente.

Após a correção, o restart passou a restaurar:

```text
energy_reserve
virtual body
world state
plasticity state
Pinocchio q
Pinocchio qdot
```

Validação observada antes do incidente posterior:

```text
SAME_INSTANCE_ID=YES
ENERGY_PERSISTED_ACROSS_RESTART=YES
BODY_STATE_PERSISTED_ACROSS_RESTART=YES
Q_QDOT_PERSISTED=YES
```

---

# 2. DEADLOCK DE FOME — CORREÇÃO POSTERIOR

Um audit posterior encontrou:

```text
energy_reserve=0
feeding_drive=1
body_capacity=0
```

Isso criava um deadlock físico:

```text
sem energia
→ capacidade corporal zero
→ não alcança recurso
→ não recupera energia
```

A correção implementada foi:

```text
ALIVE_BODY_CAPACITY_FLOOR=0.01
```

ou seja:

```text
if alive:
    body_capacity >= 0.01
```

Sem:

```text
pathfinding
target attraction
reward shaping
random walk
action selection externa
```

Após a correção:

```text
ENERGY_RESERVE=0
FEEDING_DRIVE=1
BODY_CAPACITY=0.01
EXECUTED_ACTUATION_NONZERO=YES
```

Essa alteração deve ser descrita como **mecanismo de sobrevivência física mínima**, não como comportamento alimentar.

---

# 3. SEMÂNTICA DE MOVIMENTO — CORRIGIDA

Foi identificado que a UI podia chamar de “movimento” uma alteração geométrica local de Pinocchio sem deslocamento real no espaço da Caverna.

A semântica foi corrigida.

## Regra canônica

```text
LOCOMOTION
= world_position_delta > epsilon

BODY_MOTION_WITHOUT_LOCOMOTION
= Pinocchio/body geometry changed
  but world position did not move enough
```

Com:

```text
LOCOMOTION_EPSILON=0.001u
```

Estado observado após a correção:

```text
MOVEMENT_CLASS=BODY_MOTION_WITHOUT_LOCOMOTION
```

Portanto:

```text
PINOCCHIO_GEOMETRY_CHANGE ≠ WORLD_SPACE_LOCOMOTION
```

O mapa deve remover qualquer formulação que trate deformação/atução local como prova suficiente de locomoção no Umwelt.

---

# 4. FOOD / RECURSO NA CAVERNA — IMPLEMENTADO, MAS CICLO NÃO FECHADO

Foi implementada a apresentação humana do recurso e o ciclo de estados:

```text
AUSENTE
OFERTADO
DISPONÍVEL
CONTATO
CONSUMIDO
```

A Caverna passou a exibir:

```text
FLYNN AGORA
resource state
distance
contact
energy
feeding drive
body capacity
diary with Brasília date/time
technical details expandable
```

Também foi implementado guard idempotente de consumo no `ContinuousWorldEngine`.

## Regra de causalidade

Não foi introduzido:

```text
EAT_POLICY
pathfinding
target attraction
reward
training
connectome mutation
```

O fluxo pretendido permanece:

```text
contact
→ consumed
→ canonical nutritive increment
→ energy_reserve increases
→ feeding_drive decreases
→ body_capacity increases
```

## Resultado real observado

O recurso SWEET existia e estava disponível, mas Flynn não chegou até ele durante a janela observada:

```text
RESOURCE=SWEET
CONTACT=NO
CONSUMED=NO
INGESTIONS=0
```

Logo:

```text
FOOD_MECHANICS_IMPLEMENTED=YES
REAL_CONTACT_OBSERVED=NO
REAL_CONSUMPTION_OBSERVED=NO
FULL_FEEDING_CYCLE_PROVEN=NO
```

---

# 5. CAVERNA MOBILE / PWA

Foi implementada versão mobile/PWA da Caverna:

```text
MOBILE_VERTICAL_LAYOUT=YES
HORIZONTAL_OVERFLOW=NO
TOUCH_TARGETS_MIN≈44px
SCROLL=YES
MANIFEST=YES
SERVICE_WORKER=YES
PWA_PATHS=200
```

Validação manual:

```text
390x844=PASS
320x568=PASS
```

Depois, o corpo de Flynn foi tornado mais visível no mobile:

```text
BODY_SIZE_MOBILE=ENLARGED
BODY_NODES_HIGHLIGHTED=CYAN
BODY_CONNECTIONS_HIGHLIGHTED=CYAN
HALO=YES
LABEL="FLYNN · CORPO VIVO"
```

A identidade visual azul/ciano deve ser preservada no histórico.

## Direção de layout posterior

Foi definida a seguinte hierarquia visual para a Caverna:

```text
1. Flynn / corpo vivo
2. mundo ao redor
3. situação atual
4. controles humanos
5. diário
6. detalhes técnicos
```

Também foi decidido:

```text
HUMAN_CONTROLS_OUTSIDE_WORLD_SPACE=YES
RESOURCE_DISTANCE_AS_SUBTLE_TELEMETRY=YES
NO_TARGET_ARROW=YES
INACTIVE_WORLD_ELEMENTS_DEEMPHASIZED=YES
TOP_STATUS_DUPLICATION_REDUCED=PLANNED
DIARY_AS_TIMELINE=PLANNED
TECHNICAL_DRAWER_COLLAPSIBLE=PLANNED
```

Essa última reorganização foi **especificada/promptada**, mas não há prova consolidada no percurso de que tenha sido concluída antes da suspensão.

---

# 6. AUDITORIA READ-ONLY FINAL — ESTADO REAL ANTES DA INTERRUPÇÃO

Uma auditoria read-only posterior consolidou:

```text
RESIDENT_CONTINUITY_CLASS=TRUE_CONTINUOUS
SYSTEM_COMPOSITION=MIXED_LIVE_SYNTHETIC_REPLAY
```

Durante a auditoria, a mesma instância permaneceu ativa e o relógio neural continuou avançando.

Foi observado:

```text
brain continuous=YES
world continuous=YES
Pinocchio q/qdot present=YES
trajectory source=RESIDENT
UI state matches backend=YES
ZeroClaw interlock present=YES
fake direct Flynn event injection blocked=HTTP403
```

Também:

```text
energy=0
feeding_drive=1
body_capacity=0   # antes do floor 0.01
sweet_available=YES
contact=NO
consumed=NO
ingestions=0
current_action=STOP
```

A auditoria concluiu que:

```text
REAL_WORLD_SPACE_LOCOMOTION_TO_FOOD=NOT_PROVEN
FULL_FEEDING_CYCLE=NOT_PROVEN
```

e que o endpoint de replay permanecia um visualizador LAB:

```text
REPLAY_MODE=TRUE
REPLAY_IS_LIVE_FLYNN=NO
```

---

# 7. MEMÓRIA — ROOT CAUSE ENCONTRADA, FIX FINAL NÃO VALIDADO

Foi detectado crescimento aproximadamente linear de memória durante execução residente.

A causa identificada foi:

```text
Session.history
```

que acumulava cada frame de telemetria sem limite.

## Correção

O buffer em RAM foi limitado a:

```text
MAX_SESSION_HISTORY_FRAMES=2000
```

A persistência durável em SQLite não foi removida.

Estado após implementação:

```text
MEMORY_ROOT_CAUSE_IDENTIFIED=YES
UNBOUNDED_STRUCTURE_FOUND=YES
IN_MEMORY_HISTORY_BOUNDED=YES
```

Mas a validação de longa duração foi interrompida pela perda de acesso ao host.

Portanto o mapa deve registrar:

```text
UNBOUNDED_STRUCTURE_FIXED=UNVERIFIED
MEMORY_LINEAR_GROWTH_FIXED=UNVERIFIED
```

Não declarar a regressão resolvida.

---

# 8. RESTARTS CONTROLADOS DA ÚLTIMA CORREÇÃO

Houve dois restarts controlados da residente durante a correção final:

1. primeiro restart para carregar a implementação;
2. segundo restart após observar que o epsilon inicial ainda classificava microvariação como locomoção.

Isso deve ser registrado como:

```text
CONTROLLED_RESTARTS=2
CAUSE=REAL_RUNTIME_CORRECTION
AUTOMATIC_RESET=NO
```

Não foram resets experimentais arbitrários.

---

# 9. ARTEFATOS DE RECOVERY QUE NÃO CHEGARAM A SER CRIADOS

Devido à interrupção do host, ficaram pendentes:

```text
/runtime/research/resident_recovery/RESIDENT_RECOVERY_IMPLEMENTATION.md
/runtime/research/resident_recovery/MEMORY_GROWTH_ROOT_CAUSE.json
/runtime/research/resident_recovery/RESIDENT_RECOVERY_VALIDATION.md
```

Não registrar esses arquivos como existentes.

---

# 10. INCIDENTE ORACLE CLOUD — INTERRUPÇÃO EXTERNA DO PROJETO

Em 2026-09-16 ocorreu um incidente distinto do incidente local de memória/build de 2026-09-14.

## Sequência factual

```text
Oracle email:
"An order has been processed and your subscription has been updated"

Service Name=CLOUDCM
Order ID=43068362c77159030c1789576116727
Subscription ID=77159030
```

O autor não reconheceu nem autorizou a alteração.

Na mesma janela:

```text
OCI_CONSOLE_ACCESS=LOST
MAX_SSH=UNREACHABLE
OTHER_ORACLE_VMS=UNREACHABLE
PASSWORD_RESET_DID_NOT_RESTORE_ACCESS
PUBLIC_ENDPOINTS_FAILED
```

As três VMs Oracle ficaram inacessíveis:

```text
1 × VM.Standard.A1.Flex 2 OCPU / 12 GB
2 × VM.Standard.E2.1.Micro
```

Posteriormente, o suporte Oracle declarou:

```text
ACCOUNT_STATUS=SUSPENDED
STATED_REASON="violation of the Oracle Cloud Services Agreement"
```

Sem, naquele momento, especificar no texto fornecido:

```text
exact clause
exact triggering activity
exact evidence
```

Foi solicitada **secondary review**, com prazo informado pelo suporte de aproximadamente dois dias úteis.

## Classificação canônica

```text
OCI_ACCOUNT_SUSPENDED=YES
OCI_TENANCY_ACCESS_LOST=YES
OCI_COMPUTE_ACCESS_LOST=YES
OCI_SECONDARY_REVIEW=REQUESTED
RESOURCE_DELETION=UNPROVEN
DATA_PRESERVATION=UNKNOWN
ROOT_CAUSE=UNKNOWN
```

Não atribuir a suspensão à Flynn sem evidência.

---

# 11. HIPÓTESE DE RELAÇÃO ENTRE FLYNN E A SUSPENSÃO

O autor levantou a hipótese de que cargas experimentais pesadas de Flynn poderiam ter contribuído para algum detector ou interpretação de violação contratual.

O mapa deve preservar a distinção:

```text
FLYNN_HIGH_LOCAL_RESOURCE_PRESSURE=YES
FLYNN_CAUSED_ORACLE_INFRASTRUCTURE_IMPACT=UNPROVEN
FLYNN_TRIGGERED_ACCOUNT_SUSPENSION=UNPROVEN
ORACLE_STATED_SPECIFIC_TRIGGER=NO_AT_LAST_KNOWN_UPDATE
```

Carga alta de CPU/RAM dentro da VM não deve ser descrita automaticamente como “sobrecarregar a Oracle”.

---

# 12. CONSEQUÊNCIA CIENTÍFICA DA INTERRUPÇÃO

A continuidade residente era parte do objeto experimental.

A suspensão externa rompeu:

```text
brain continuity
body continuity
world continuity
homeostasis continuity
trajectory continuity
```

Mesmo que a MAX seja posteriormente restaurada, a sequência temporal contínua anterior foi interrompida.

Registrar:

```text
RESIDENT_CONTINUITY_INTERRUPTED_EXTERNALLY=YES
CONTINUITY_GAP_CAUSE=INFRASTRUCTURE_ACCOUNT_SUSPENSION
```

Não chamar uma eventual retomada futura de continuidade ininterrupta.

---

# 13. APOSENTADORIA / CONGELAMENTO DO PROJETO

Após o incidente, o autor decidiu:

```text
FLYNN_RETIRED=YES
FLYNN_FROZEN=YES
CURRENT_RESUMPTION_PLAN=NONE
LOCAL_REHOST=NO
GOOGLE_MINI_REHOST=NO
```

Razão central:

- o projeto dependia de existência online/residente contínua;
- transformar Flynn em processo local sob demanda alteraria a própria pergunta experimental;
- o incidente rompeu a continuidade que sustentava a curiosidade científica do experimento.

Se a MAX voltar, a prioridade não é retomar automaticamente a execução.

```text
IF_MAX_RETURNS:
1. preserve/export data
2. preserve ledger/checkpoints/runtime
3. assess integrity
4. author decides whether any future continuation exists
```

---

# 14. RISCO DE PERSISTÊNCIA EXPOSTO PELO INCIDENTE

O audit anterior já havia encontrado que o runtime Flynn não estava versionado:

```text
RUNTIME_GIT=NO
```

Os bancos, ledger, checkpoints e parte relevante do estado existiam apenas na MAX.

A suspensão expôs uma fronteira crítica:

```text
SOURCE_CODE_BACKUP != RESIDENT_STATE_BACKUP
```

Registrar como lição operacional:

```text
EXTERNAL_STATE_BACKUP_REQUIRED_FOR_FUTURE_RESIDENT_SYSTEMS=YES
SINGLE_CLOUD_TENANCY_AS_ONLY_STATE_AUTHORITY=REJECTED
```

Isso é registro histórico da falha de continuidade, não plano de reativação da Flynn.

---

# 15. BLOCO CANÔNICO FINAL SUGERIDO

Substituir o final atual por algo equivalente a:

```text
PROJECT=FLYNN
PROJECT_STATUS=RETIRED_FROZEN
RESEARCH_STATUS=CLOSED_BY_AUTHOR

ORGANISM_ID=759f27b3-84a9-4071-b29e-20adc1d4fc50
FORMER_AUTHORITATIVE_HOST=MAX
FORMER_PROVIDER=ORACLE_CLOUD

FOUNDATION_GATES_EXECUTED_THROUGH=014
FOUNDATION_EXPERIMENTAL_SEQUENCE=COMPLETE
FOUNDATION_CLOSURE_CORRECTION=COMPLETE

BRAIN_CONTINUOUS_REAL_BEFORE_INTERRUPTION=YES
WORLD_CONTINUOUS_REAL_BEFORE_INTERRUPTION=YES
BODY_CONTINUOUS_REAL_BEFORE_INTERRUPTION=YES
HOMEOSTASIS_CONTINUOUS_REAL_BEFORE_INTERRUPTION=YES

ENERGY_TO_BODY_CAPACITY_IMPLEMENTED=YES
ALIVE_BODY_CAPACITY_FLOOR=0.01

FOOD_MECHANICS_IMPLEMENTED=YES
REAL_CONTACT_OBSERVED=NO
REAL_CONSUMPTION_OBSERVED=NO
FULL_FEEDING_CYCLE_PROVEN=NO

MOVEMENT_SEMANTICS_CORRECTED=YES
LOCOMOTION_REQUIRES_WORLD_POSITION_DELTA=YES
BODY_MOTION_WITHOUT_LOCOMOTION=SUPPORTED

MEMORY_ROOT_CAUSE_IDENTIFIED=YES
SESSION_HISTORY_RAM_LIMIT=2000
MEMORY_LINEAR_GROWTH_FIXED=UNVERIFIED

MOBILE_PWA_IMPLEMENTED=YES
LETHE_MOBILE_VISIBILITY_IMPROVED=YES

OCI_ACCOUNT_SUSPENDED=YES
OCI_TENANCY_ACCESS_LOST=YES
OCI_COMPUTE_ACCESS_LOST=YES
OCI_SECONDARY_REVIEW=REQUESTED
RESOURCE_DELETION=UNPROVEN

RESIDENT_CONTINUITY_INTERRUPTED_EXTERNALLY=YES

FLYNN_RETIRED=YES
FLYNN_FROZEN=YES
REHOST_LOCAL=NO
REHOST_GOOGLE_MINI=NO
CURRENT_RESUMPTION_PLAN=NONE

PRODUCT_REAL_BEFORE_INTERRUPTION=YES
CURRENT_RUNTIME_STATUS=OFFLINE_UNAVAILABLE

NEXT_ACTION=
NONE_FOR_DEVELOPMENT

IF_ORIGINAL_MAX_RETURNS=
PRESERVE_DATA_AND_DECIDE_LATER
```

---

# 16. ITENS DO MAPA ATUAL QUE DEVEM SER MARCADOS COMO HISTÓRICOS

As seguintes formulações ainda aparecem como presentes/ativas e precisam ser temporalizadas:

```text
STATUS=ACTIVE_RESIDENT_NEURO_SYNTHETIC_RUNTIME
HOST autoritativo=MAX
CAVERNA_DE_HIPNOS=ACTIVE_UMWELT
LETHE=LIVE_CANONICAL_SIGIL_BODY
PRODUCT_REAL=YES
NEXT_ACTION=ENERGY_TO_BODY_CAPACITY
```

Forma correta:

```text
..._BEFORE_OCI_SUSPENSION=YES
CURRENT_RUNTIME_STATUS=OFFLINE_UNAVAILABLE
PROJECT_STATUS=RETIRED_FROZEN
```

O mapa deve preservar todo o percurso científico anterior como histórico válido, sem reescrevê-lo como se os resultados deixassem de ter existido.

---

# 17. FECHAMENTO SUGERIDO

A pergunta científica construída pelo projeto continua historicamente válida:

> **o que um núcleo neural biologicamente ancorado consegue fazer quando possui um corpo próprio, consequências persistentes, necessidades energéticas reais e um Umwelt contínuo — sem que uma camada externa escolha seus objetivos por ele?**

Mas o experimento residente foi interrompido externamente antes que o ciclo alimentar/locomotor fosse fechado.

O estado final deve ser descrito sem fabricar conclusão:

```text
ASSOCIATIVE_LEARNING_PROVEN=NO
REAL_WORLD_SPACE_LOCOMOTION_TO_FOOD=NOT_PROVEN
FULL_FEEDING_CYCLE_PROVEN=NO

LIVE_BODY_IMPLEMENTED=YES
PERSISTENT_TRAJECTORY_IMPLEMENTED=YES
ENERGY_TO_BODY_CAPACITY_IMPLEMENTED=YES
RESIDENT_CONTINUITY_WAS_REAL=YES
RESIDENT_CONTINUITY_WAS_INTERRUPTED=YES

PROJECT_RETIRED_FROZEN=YES
```

A interrupção não invalida o que foi medido antes dela.  
Também não autoriza inferir resultados que não chegaram a ser observados.
