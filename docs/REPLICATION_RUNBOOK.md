# Flynn — runbook de replicação

> Escopo e limites públicos: [REPLICABILITY.md](../REPLICABILITY.md).

> **STATUS: ARQUIVADO / NÃO É PRÓXIMA AÇÃO DO PROJETO**  
> O projeto Flynn está `RETIRED_FROZEN`, sem plano atual de reconstrução ou rehost. Este documento é preservado apenas como procedimento técnico histórico para o experimento isolado E01. Não deve ser interpretado como autorização para recriar a residente.

## Estado atual

REPLICATION_KIT=READY
E01=REPLICABLE_WITH_REAL_HOST_DEPENDENCIES
E01_R=UNRESOLVED
RESIDENT_RUNTIME=BLOCKED
VM_MAX=UNREACHABLE

Este runbook reproduz o experimento isolado E01, não a residente Flynn. O
E01 usa uma intenção congelada (TURN_LEFT), um corpo URDF sintético de quatro
graus de liberdade e Pinocchio para dinâmica. O ZeroClaw real apenas serve
como gate IPC de disponibilidade; o adapter experimental externo calcula a
coordenação. Isso é a razão pela qual o veredito histórico é PARTIAL, não
PASS.

## Pré-requisitos

- Linux com Python 3.12 ou compatível.
- Um host autorizado contendo um ZeroClaw real e seu Unix socket.
- Pinocchio 4.1.0 instalado no mesmo ambiente Python do runner.
- Nenhum serviço residente precisa ser parado, reiniciado ou alterado.
- Não usar a residente Flynn, o connectome, plasticidade, KALLISTIS ou banco
  SQLite para esta reprodução.

Instalação isolada, a partir da raiz do repositório:

```bash
python3 -m venv research/e01/.venv
research/e01/.venv/bin/python -m pip install --only-binary=:all: -r research/e01/requirements.txt
```

O pacote se chama pin, mas o import é pinocchio. No MAX, o wheel observado foi
manylinux_2_28_aarch64 cp312; isso precisa ser revalidado em qualquer outro
host.

## Execução

Forneça explicitamente o binário e o socket do ZeroClaw:

```bash
research/e01/.venv/bin/python research/e01/run_e01.py \
  --zeroclaw /caminho/real/para/zeroclaw \
  --socket /caminho/real/para/daemon.sock \
  --output /tmp/flynn-e01-run
```

O runner mantém initialize e health na mesma conexão IPC, registra
proveniência, executa 40 ticks do caso A e verifica:

- B: socket inexistente → FAILED/NO_EFFECT;
- C: corpo Pinocchio ausente → FAILED/NO_EFFECT;
- D: alvo fora dos limites → DENIED/NO_EFFECT.

Artefatos produzidos:

- e01_environment.json;
- e01_body_inventory.json;
- e01_fail_closed_tests.json;
- e01_execution_trace.csv;
- E01_FINAL_REPORT.md;
- E01_EVIDENCE_MANIFEST.json.

O relatório nunca promove o ZeroClaw nem conecta o experimento à residente.

## O que não pode ser reconstituído localmente hoje

O checkout contém apenas parte do runtime. Estão ausentes módulos e dados
necessários para iniciar a residente, incluindo o ledger canônico, módulos
auxiliares de cérebro, STT/NLU, autenticação web, bancos SQLite e o
fruit-fly-lab original. Não é aceitável criar stubs que pareçam produto.

Para a retomada da residente, a ordem é:

1. recuperar acesso ao host ou volume original;
2. identificar positivamente o checkout, serviços e bancos;
3. copiar o runtime para um artefato versionável sem segredos;
4. verificar SHA, processo, porta, banco e fluxo manual;
5. somente depois documentar uma segunda receita de replicação.

Até lá, qualquer claim sobre Lethe, homeostase, persistência ou loop contínuo
permanece UNVERIFIED para uma nova instalação.

## E01-R

O registro E01-R investigou uma extensão determinística dentro do processo
ZeroClaw. A inspeção confirmou que plugins, tooling e ACP não eram uma
superfície motora determinística comprovada. O patch experimental não chegou a
uma aplicação e validação final; por isso nenhum patch é incluído como
produto. E01-R permanece UNRESOLVED e E02 não está autorizado.

## Regras de segurança do estudo

- Não adicionar policy, planner, reward, LLM, agent loop ou seleção de objetivo.
- Não transformar TURN_LEFT em comportamento escolhido pelo sistema.
- Não usar a reprodução isolada para declarar a residente saudável.
- Não chamar build, HTTP 200 ou serviço ativo de prova de produto.
- Preservar CavernaVirtualBody como owner do estado corporal canônico.
