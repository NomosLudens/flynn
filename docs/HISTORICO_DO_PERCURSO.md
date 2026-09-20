# Flynn — histórico completo do percurso

Documento de histórico e proveniência

- Data de consolidação: 2026-09-20
- Repositório: NomosLudens/flynn
- Estado atual: kit de replicação preparado; runtime residente bloqueado

Este documento registra o caminho técnico da Flynn, desde a concepção do loop
cérebro–corpo–mundo até a recuperação do material local e a publicação do kit
no GitHub. Ele separa:

- experiência histórica observada no host MAX;
- implementação recuperada no checkout local;
- reprodução isolada que pode ser executada novamente;
- afirmação sobre a residente atual.

Essas categorias não são equivalentes.

## 1. Ideia e fronteiras

Flynn começou como uma simulação de núcleo neural derivado de Drosophila e
evoluiu conceitualmente para um organismo neuro-sintético com:

- núcleo neural;
- órgãos internos sintéticos;
- corpo articulado;
- mundo contínuo;
- histórico causal persistente.

A cadeia arquitetural registrada foi:

    mundo
      → transdução sensorial
      → cérebro LIF
      → leitura descendente
      → corpo Pinocchio
      → mundo

O princípio central separava seleção de comportamento e execução motora:

- Flynn ou o output neural determina o que fazer;
- uma camada motora pode coordenar como executar;
- Pinocchio calcula a dinâmica do corpo;
- CavernaVirtualBody permanece owner do estado corporal canônico.

Nos experimentos E01 e E01-R ficaram proibidos policy, planner, reward,
reinforcement learning, LLM, agent loop, seleção autônoma de objetivo,
pathfinding, atração, random walk, alteração do connectome, plasticidade ou
substituição do corpo canônico.

## 2. Estado residente antes da perda da VM

O ambiente autoritativo histórico era o host MAX, acessado por SSH, com o
runtime em:

- /home/ubuntu/Portifolio/flynn-max/fruit-fly-lab
- /home/ubuntu/Portifolio/flynn-max/data/flywire-v783
- /home/ubuntu/Portifolio/flynn-max/runtime

Os serviços registrados eram:

- flynn-brain.service
- flynn-web.service
- zeroclaw.service
- lethe-tunnel.service
- kallistis.service

O organismo residente tinha o identificador
759f27b3-84a9-4071-b29e-20adc1d4fc50.

O estado canônico registrado antes dos experimentos era:

- cérebro, mundo e corpo contínuos;
- plasticidade inativa;
- zero deltas aprendidos;
- connectome base não modificado;
- aprendizado associativo não comprovado;
- ZeroClaw como EXECUTION_INTERLOCK;
- CavernaVirtualBody como owner da mutação corporal.

Esses registros eram limites de segurança, não autorização para promover
experimentalmente o ZeroClaw ou alterar a residente.

## 3. E01 — Embodiment E01, 14/09/2026

### 3.1 Pergunta

O E01 investigou se ZeroClaw poderia evoluir de EXECUTION_INTERLOCK para uma
camada de coordenação motora semelhante a um cerebelo, usando Pinocchio como
modelo cinemático e dinâmico, sem adquirir agência comportamental.

Pipeline pretendido:

    MotorIntent externo congelado
      → coordenação de execução
      → Pinocchio
      → movimento articulado

O experimento não deveria conectar à residente, treinar Flynn ou alterar o
corpo canônico.

### 3.2 Preflight histórico

No MAX, o preflight registrou ARM64, Ubuntu 24.04, Python 3.12.3, serviços
canônicos ativos, KALLISTIS respondendo HTTP 200 e checkout residente limpo
em estado destacado.

Esse preflight era específico daquele momento e não prova que MAX ou os
serviços estejam disponíveis hoje.

### 3.3 Pinocchio e corpo sintético

Pinocchio foi instalado isoladamente como distribuição pin 4.1.0, com import
pinocchio, em wheel manylinux_2_28_aarch64 cp312.

Foi criado um corpo URDF sintético, sem alegação biológica:

- thorax;
- duas pernas;
- quatro graus de liberdade efetivos;
- parâmetros de massa e inércia de engenharia;
- limites explícitos de juntas.

O corpo está preservado em research/e01/flynn_e01_minimal_body.xml.

### 3.4 Casos executados

| Caso | Situação | Resultado histórico |
| --- | --- | --- |
| A | ZeroClaw e Pinocchio disponíveis | 40 ticks, articulação coordenada |
| B | ZeroClaw indisponível | FAILED/NO_EFFECT |
| C | Pinocchio indisponível | FAILED/NO_EFFECT |
| D | comando fora dos limites | DENIED/NO_EFFECT |

O caso A produziu q_delta_norm=0.1395588487606979.

Não houve policy, reward, LLM, agent turn, estímulo residente ou consumo do
output motor residente.

### 3.5 Correções do harness

Duas falhas do próprio harness foram encontradas e corrigidas:

1. Pinocchio 4.1.0 não possui Model.nj; o número de juntas foi obtido por
   len(model.names) - 1.
2. O primeiro cliente abriu conexões separadas para initialize e health. O
   ZeroClaw exigia os dois métodos na mesma conexão IPC.

O runner atual em research/e01/run_e01.py incorpora essas correções e remove
os caminhos fixos da VM.

### 3.6 Resultado

O resultado correto não foi PASS:

    E01=PARTIAL
    ZEROCLAW_ROLE=EXECUTION_INTERLOCK
    MOTOR_COORDINATION_OWNER=EXTERNAL_RESEARCH_ADAPTER
    SYNTHETIC_CEREBELLAR_LAYER_IMPLEMENTED=NO
    E02_READY=NO

O corpo e a dinâmica funcionaram, mas a coordenação dependia de um adapter
experimental externo. Isso não provava uma superfície motora pertencente ao
processo ZeroClaw.

## 4. E01-R — reconciliação do ownership

O E01-R investigou se o processo ZeroClaw poderia possuir uma superfície
determinística de coordenação motora sem selecionar comportamento, objetivo ou
reward.

A auditoria do ZeroClaw real encontrou:

- versão 0.8.5;
- binário ARM64;
- IPC Unix local;
- métodos observados: initialize e health;
- nenhuma interface motora determinística observada.

A inspeção do upstream pinned indicou que plugins eram voltados a tools/WASM e
ACP era sessão de agente. Essas superfícies não provavam um caminho motor
determinístico sem agent ou LLM.

Foi estudada uma extensão mínima do dispatcher local, mas o patch
experimental não chegou a aplicação, build e validação causal final.

    E01_R=UNRESOLVED
    ZEROCLAW_CEREBELLAR_CANDIDATE=UNRESOLVED
    E02_READY=NO

Nenhum patch incompleto foi promovido para produto.

## 5. Hardening do runtime residente

### 5.1 Crescimento de memória

Foi identificado crescimento não limitado de Session.history apesar da
persistência canônica em SQLite. A correção registrada foi:

- HISTORY_MAX_FRAMES=2000;
- retenção limitada apenas no buffer em memória;
- persistência histórica mantida no SQLite.

### 5.2 Movimento corporal versus locomoção

O runtime podia classificar microvariações geométricas como locomoção. Foi
introduzida a separação por world_position_delta, epsilon 0.001 e classes:

- LOCOMOTION;
- BODY_MOTION_WITHOUT_LOCOMOTION;
- REST.

### 5.3 Capacidade corporal de baixa energia

Foi registrado um piso de capacidade corporal 0.01 para permitir atividade
mínima quando a energia chegasse a zero, sem criar seleção de ação, targeting
ou comportamento novo.

### 5.4 Limite da validação

Os arquivos foram compilados e implantados historicamente, mas a janela de
estabilidade de memória por dez minutos não terminou antes da perda do host.
A eliminação do crescimento linear permaneceu UNVERIFIED.

## 6. Fechamento do loop cérebro–corpo–mundo

O gate do closed loop registrou uma observação histórica de aproximadamente
198,89 segundos:

- cérebro: 157.800 passos;
- mundo: 789 chunks;
- corpo: 789 observações;
- energia acompanhando o tempo neural;
- feeding drive derivado da energia;
- deslocamento corporal observado;
- posição do corpo persistida;
- Pinocchio e estado mundial preservados após reload.

Também ficou registrado que posição e distância vinham do estado residente,
GET não avançava o relógio, oferta de comida não injetava estímulo diretamente
e consumo dependia de contato físico. O contato não foi alcançado durante a
janela passiva.

Resultado histórico:

    BRAIN_CONTINUOUS_REAL=YES
    WORLD_CONTINUOUS_REAL=YES
    BODY_CONTINUOUS_REAL=YES
    CONTINUITY_CLASS=MIXED
    VERDICT=PARTIAL

O material correspondente está em closed_loop/.

## 7. Lethe e Caverna

Lethe foi investigada como superfície visual de laboratório para observação de
Flynn. A experiência mostrava estado quiescente, rede causal, estímulos,
corpo, replay de trace e estados neurais/corporais.

A interpretação técnica preservada foi: laboratório de observação de um loop
cérebro–corpo–mundo para Flynn.

Foram observados riscos de UX:

- ausência de hierarquia clara de headings;
- select sem rótulo acessível evidente;
- dependência de cor e animação;
- sem prova completa de replay persistente versus integração nova;
- terminologia opaca para usuários fora do estudo.

Essa investigação foi read-only. A UI não foi tratada como prova suficiente do
runtime.

## 8. Caverna Food UI

A camada de alimentação foi implementada e validada historicamente com:

- estado corporal;
- energia, drive e capacidade;
- posição do recurso;
- distância canônica;
- contato;
- consumo;
- diário causal;
- detalhes técnicos colapsáveis;
- validação móvel em 390x844 e 320x568.

O contrato preservado foi:

    distância <= contact_radius
      → CONTACT
      → consumo único
      → reposição de homeostase

Foi adicionada idempotência para evitar dupla reposição. A observação real
não alcançou o recurso SWEET; consumo, aumento de energia e redução do drive
ficaram NOT_REACHED.

Os artefatos estão em caverna_food_ui/.

## 9. Perda do MAX

Depois das alterações residentes, o host MAX deixou de responder:

- Cloudflare retornou 530/Error 1033;
- SSH expirou;
- ping não respondeu;
- Tailscale mostrou o host offline.

A evidência classificou a falha como host-wide, não como defeito comprovado
apenas da Flynn.

O uso de memória próximo de MemoryMax=4G foi registrado como hipótese de
OOM/pressão, mas não como causa comprovada. Não havia evidência de kernel ou
console do provedor para fechar o diagnóstico.

    HOST_MAX=UNREACHABLE
    FLYNN_SERVICE=UNKNOWN
    CAUSA_EXATA=UNRESOLVED
    OOM_COMPROVADO=NO

Não foi feito restart cego nem recuperação destrutiva.

## 10. Retomada local em 20/09/2026

O checkout local foi reavaliado:

- não havia commits;
- não havia remoto;
- o código recuperado estava presente como arquivos não versionados;
- bytecode Python estava misturado ao diretório;
- o runtime completo não estava presente.

O Git local ainda continha árvores órfãs. Uma delas preservava o runner e o
URDF do E01. Esses artefatos foram recuperados e transformados em uma versão
replicável:

- paths da VM removidos do runner;
- binário e socket passados por argumentos;
- saída de artefatos parametrizada;
- sessão IPC corrigida;
- relatório fail-closed;
- manifesto SHA-256;
- nenhuma importação da residente.

Também foram criados:

- docs/REPLICATION_RUNBOOK.md;
- docs/EVIDENCE_INDEX.md;
- docs/RECOVERY_PROVENANCE.md;
- research/e01/requirements.txt;
- research/e01/flynn_e01_minimal_body.xml;
- research/e01/run_e01.py.

## 11. Validação da retomada local

No ambiente temporário local:

- Python compilou o código recuperado;
- o XML passou no parser;
- Pinocchio 4.1.0 foi instalado fora do projeto;
- o corpo executou 40 passos;
- N_DOF=4;
- q_norm=0.13955884876069757;
- limite inválido foi rejeitado;
- execução sem ZeroClaw real produziu relatório e encerrou com código 2.

O código 2 é intencional: sem ZeroClaw real, a replicação completa não pode
ser considerada sucesso. O runner não usa mock para mascarar essa ausência.

## 12. Publicação no GitHub

Foi criado o commit local:

    3e29d21c566e0520a81393b45dcd428fb1d33e86

O remoto informado foi configurado:

    https://github.com/NomosLudens/flynn.git

O commit foi publicado em master. A conferência final confirmou:

    LOCAL_HEAD=3e29d21c566e0520a81393b45dcd428fb1d33e86
    REMOTE_HEAD=3e29d21c566e0520a81393b45dcd428fb1d33e86
    WORKTREE=CLEAN

## 13. Estado atual consolidado

| Componente | Estado |
| --- | --- |
| Checkout local | PASS |
| Repositório GitHub | PASS |
| Kit E01 | READY |
| Corpo Pinocchio sintético | PASS em ambiente temporário |
| Casos fail-closed | PASS |
| ZeroClaw real atual | BLOCKED |
| VM MAX | UNREACHABLE |
| Runtime residente | BLOCKED |
| Estabilidade de memória | UNVERIFIED |
| Contato/consumo real de comida | NOT_REACHED |
| E01 | PARTIAL |
| E01-R | UNRESOLVED |
| E02 | NOT_READY |

## 14. Próximo percurso correto

A próxima etapa não é criar outro runtime paralelo. É recuperar a autoridade
original:

1. obter console, volume ou backup do MAX;
2. identificar positivamente diretórios, serviços e bancos;
3. copiar o runtime sem segredos;
4. comparar SHA, processos, portas e banco;
5. recuperar os módulos ausentes do checkout;
6. repetir a prova manual do fluxo residente;
7. somente então atualizar o status da residente.

Até que essa cadeia seja provada, o repositório GitHub deve ser lido como:

> código recuperado + kit de reprodução isolado + evidências históricas,
> não como uma residente Flynn atualmente operacional.
