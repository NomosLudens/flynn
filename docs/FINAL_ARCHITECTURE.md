# Arquitetura Final da FLYNN V2

**Estado:** `PROJECT_STATUS=ENDED` · `FULL_CAUSAL_LOOP=NOT_DEMONSTRATED`  
**Origem operacional:** runtime instalado na VM `flynn-1gb`, observado em 26/10/2026. A árvore instalada não continha metadados Git suficientes para associá-la a um commit.

## Fluxo pretendido

```text
LETHE / interface de mundo
  → ContinuousWorldEngine / iluminação global sintética
  → visual_light_transducer
  → signed_connectome CSR + lif_engine + neural_core
  → aggregator + descending_readout
  → ponte e coordenação PicoClaw
  → adaptação instrumental do sinal motor
  → Pinocchio sigil body / plano XY-yaw
  → proprioceptive_transducer + proprioceptive_readout
  → próxima fronteira LIF
  → eventos, estados e checkpoints SQLite
```

O caminho completo era a intenção arquitetural, não um resultado validado. Foram observadas entrada visual sintética e atividade LIF persistida; atividade descendente ficou zero nas janelas documentadas, torque permaneceu zero, corpo estático e nenhum retorno proprioceptivo efetivo chegou a um passo neural posterior.

## Componentes e contratos

| Componente / arquivo instalado | Responsabilidade implementada | Evidência e limite observado |
|---|---|---|
| `app/world/continuous_world.py`, `app/neuro_synthetic/world_runtime.py` | Estado do mundo e comando de iluminação, com persistência temporal | Estímulo residente foi uma luz escalar global, não cena visual espacial. |
| `app/neuro_synthetic/visual_light_transducer.py` | Converter luz em condutância para roots visuais R1–6/R7/R8 | 11.118 raízes; sinal explicitamente sintético e instrumental. |
| `app/neuro_synthetic/signed_connectome.py` | Carregar CSR, raiz e metadados de sinais | Arrays não foram copiados para o GitHub. |
| `app/neuro_synthetic/lif_engine.py`, `neural_core.py` | Avançar estado LIF e spikes por passos de 0,1 ms | atividade observada; fidelidade biológica não estabelecida. |
| `aggregator.py`, `descending_readout.py` | Agregar contagens e mapear 1.303 DNs | mapa root/index consistente nas amostras; zero Desc nas janelas. |
| `picoclaw_port.py`, `mcp_server.py`, worker/bridge | Receber frames e sincronizar etapas | receipts/coordenação observados; atuação corporal não demonstrada. |
| `app/body/pinocchio_sigil.py`, `pinocchio_motor_worker.py` | Aplicar torques a modelo rígido do glifo | passos despachados com torque zero, sem mudança de pose. |
| `proprioceptive_transducer.py`, `app/body/proprioceptive_readout.py` | Derivar sinais de q/qdot e mapear raízes mecanossensoriais | corpo sem desvio; zero alvos efetivos. |
| `app/brain/homeostasis_v2.py` | Contabilidade de CPU e reserva normalizada | não representa energia/metabolismo biológico. |
| `app/neuro_synthetic/sqlite_store.py` | Persistir eventos, estados, cursor/generation/checkpoint | schema 1; SQLite observado em `DELETE`, locks podem bloquear writer. |
| `app/neuro_synthetic/resident_runtime.py` | Orquestrar execução residente e recuperação | implementação instalada arquivada; não restaurada nesta missão. |
| `app/web/server.py`, raiz `server.py`, `app/web/caverna.py` | LETHE e observabilidade web local | viewer configurado em loopback; na última inspeção anterior estava inativo; API respondeu 502. |
| `ops/flynn_history_archiver.py` e timer systemd | Arquivar/rotacionar estado | timer nominal de 30 min; tentativa final observada falhou por espaço de staging. |

## Sincronização e persistência

O ciclo coordenado era de 20 ms neurais, com subpassos LIF de 0,1 ms. Eventos de componentes continham identidade causal e snapshots eram persistidos em tabelas de estado. Os checkpoints NPZ retinham vetores LIF e snapshots de mundo/observabilidade. Cursor causal restaurável requeria episódio, generation, checkpoint id/hash e registro atômico de ciclo compatíveis. No episódio 5, o cursor parou em tick 87.800; dados parciais em 88.000 não continham a confirmação atômica. A unidade recusou inicialização.

## Serviços e configuração de referência

- `flynn-v2-resident.service`: executava `python -m app.neuro_synthetic.resident_runtime` em Python 3.10 a partir de `/home/tonyus-dev/flynn-v2-vm-validation-20261019/resident-app`.
- `flynn-lethe-viewer.service`: Uvicorn em `127.0.0.1:8201`, leitura local do banco da residente.
- `flynn-history-archive.timer`: agendamento de arquivador a cada 30 min, segundo a configuração observada.
- Banco do episódio 5: `/var/lib/flynn-v2/resident-episode-5/episode-v2.sqlite3`.
- Ambientes separados: LIF com NumPy 1.22.3; Pinocchio com `pin==4.1.0`, `cmeel==0.61.0`, NumPy 2.2.6 e bibliotecas nativas próprias.
- Cloudflare fazia parte do caminho público LETHE/observer em observações históricas; não há prova de disponibilidade pública após a última captura.

## Corpo, observação e fontes

O modelo tinha 23 módulos de glifo, 22 links dinâmicos selecionados, oito arestas de grafo não mecânicas e base planar X/Y/yaw. A indicação “central EB anchored” não coincide com a base livre observada. A observabilidade distinguiu estado persistido de dados stale; estado estrutural estático do glifo não era evidência de pose dinâmica.

Os limites de cada interface estão em [modelo neural](NEURAL_MODEL.md), [embodiment](EMBODIMENT.md), [resultados](EXPERIMENTAL_RESULTS_FINAL.md), [análise da falha](FINAL_FAILURE_ANALYSIS.md) e [reprodutibilidade](REPRODUCIBILITY_STATUS.md).

## Proveniência: instalado versus GitHub

O snapshot preserva 31 arquivos copiados byte a byte do host e hash individual. Comparado ao `master` público em `f69f6c0d2193e128df97ca58cabca75c06636172`, havia 8 correspondências, 4 diferenças e 19 caminhos sem arquivo no GitHub naquela revisão. Nenhuma revisão histórica é atribuída à árvore instalada. O WIP local não é declarado equivalente ao runtime. A lista completa e hashes estão em [`archive/runtime-installed/2026-10-26/README.md`](../archive/runtime-installed/2026-10-26/README.md).

## Estado atual e reconstrução

Última observação remota arquivada: serviço residente `failed` ao atingir start limit após cinco tentativas às 15:43:26 UTC de 26/10; viewer inativo. Esta retomada não conseguiu confirmar o estado atual: o cliente não tem `gcloud` e `ssh flynn-1gb` falha na resolução de nome. Nenhum processo foi iniciado, parado ou restaurado nesta sessão. Reprodução integral permanece `UNVERIFIED`.
