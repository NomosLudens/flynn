# Histórico de Incidentes — FLYNN V2

Datas e horários são UTC quando há evidência temporal disponível. “Observado” indica journal, linha de estado, hash ou registro contemporâneo preservado. Hipóteses estão separadas. Não há contagem completa de todas as tentativas de recuperação; este documento inclui as ocorrências identificáveis nas evidências preservadas.

## 19/10/2026 — primeira residência e perda de alinhamento frame/checkpoint

**Contexto:** criação da residente na VM `kaline-totalidade/us-central1-f/flynn-1gb`.  
**Evidência:** episódio `resident-v2:flynn-1gb:a6379b5ef726413aab1ad0864e3a13c4` avançou estado/frame durável até tick 6.600, enquanto o checkpoint pareado estava em 6.400. O estado de membrana dos 20 ms sem checkpoint não podia ser reconstruído exatamente.  
**Ação/resultado:** recuperação recusada; episódio ficou interrompido, sem reclassificação como continuidade. A documentação atribui a interrupção ao `KillMode=control-group`, que encerrou também worker filho durante restart.  
**Recuperação:** uma execução posterior criou identidade distinta `resident-v2:flynn-1gb:7909dda987994c308ec928794a1f4e20`, iniciou em tick 0 e depois restaurou checkpoint tick 620 no mesmo episódio.  
**Limite:** registro prova episódios e cursores específicos, não uma residência ininterrupta.

## 20/10/2026 — falhas de inicialização e contrato de geração

### Método inexistente

Runtime chamou `pipeline.activate_causal_generation(...)`, inexistente em `NeuralActivityPipeline`, durante tentativa de inicialização/restauração no cursor 105.200. SQLite registrava `integrity_check=ok`, 373 eventos e 275 estados; cauda em 105.400 ficou sem ciclo/checkpoint novo. O serviço foi parado após falha. Não foi erro `database is locked` nessa tentativa.

### Geração incompatível na ponte

Uma tentativa posterior foi recusada pelo MCP em `mcp_server.py:317` devido a `causal_generation_id` divergente do frame durável. Cursor permaneceu em 105.200; sete estados novos não formavam ciclo confirmado. O serviço foi parado; a cauda não foi usada para recuperação.

### Lock no tick 107.800

Após alinhar identidade, uma inicialização confirmou ciclos até tick 107.800 e validou checkpoint pareado. O ciclo seguinte encerrou com `OperationalError: database is locked`; a mensagem não tinha traceback/callsite. Banco continuava `integrity_check=ok`, 707 eventos/519 estados; tick 108.000 não foi confirmado. Processo foi parado antes de novo restart automático. A conexão bloqueadora não foi identificada.

## 21/10/2026 — persistência e arquivamento Drive

**Contexto:** redundância entre snapshots completos em `component_states` e payloads inline de eventos foi identificada e uma alteração em `sqlite_store.py` instalada após backup reversível documentado.  
**Ação/resultado:** ensaios isolados validaram escrita em lote, resolução de referência nova e compatibilidade de payload antigo; a residente parou/restaurou no mesmo episódio até tick 439.200. Isso foi uma intervenção autorizada, mas não prova o ciclo neuromotor.  
**Falha de arquivo externo:** acesso do conector Drive não era uma credencial utilizável pela residente; navegador/consentimento necessário não estava disponível. Não houve upload, readback ou liberação de espaço. A documentação registrou zero bytes reclamados. SQLite, WAL e checkpoints ficaram preservados localmente.

## 23/10/2026 — falta de amostra Pinocchio na fronteira causal

Às **18:21:57 UTC**, execução registrada em `world_runtime.py:231` encerrou o ciclo porque faltava amostra Pinocchio na fronteira causal atual, dentro da sequência de `advance_synchronized`. Serviço tornou-se ativo novamente às **18:26:59 UTC**. A fonte local instalada em 26/10 é preservada, mas a documentação daquela observação descreve a sequência realmente instalada no evento. A retomada não prova continuidade integrada durante o intervalo. A investigação histórica não isolou de modo conclusivo se foi ordem de atualização, falha transitória na produção corporal, persistência incompleta ou outra condição.

## 23–24/10/2026 — corrida de arquivador e observabilidade stale

Uma execução de rotação tentou arquivar checkpoint NPZ ausente (`FileNotFoundError`) e a pipeline zstd terminou em `BrokenPipeError`; nenhum checksum/readback de novo objeto foi comprovado para essa tentativa. Em uma captura de 24/10, a API avançou 60 ms neurais entre leituras em 47,008 s, mas agregação LIF estava stale, spikes/DNs zero e pose dinâmica ausente. Outra execução do timer falhou por falta de espaço suficiente para staging mais reserva. O endpoint em um estado posterior indisponível respondeu HTTP 502. São observações em instantes diferentes, não uma única falha simultânea.

## 25/10/2026 — orçamento Homeostasis V2

Modelo `homeostasis-v2-measured-cpu-budget-1` passou a debitar CPU medido de reserva normalizada. Assimilação permaneceu desabilitada sem fonte/conversão verificadas. O estado é contabilidade computacional, não fisiologia. O evento é mudança funcional no runtime, não incidente de corrupção demonstrado.

## 26/10/2026 — intervenção do handler e documentação de execução ativa

Notas contemporâneas locais registram remoção acidental de `_handle_signal`, duas falhas de startup e restauração do handler, seguida de retorno ao mesmo episódio. Horários exatos não foram preservados na cópia final do journal. Outro documento de operação registra correções no contrato de checkpoint inicial e serialização do centroide Pinocchio, com amostras posteriores ativas até ao menos 960 ms. Essas notas têm limite temporal próprio e não anulam o inventário final posterior.

## 26/10/2026 15:28–15:43 UTC — falha final de execução residente

| Horário | Estado anterior / ação | Resultado observado | Causa e impacto |
|---|---|---|---|
| 15:28:07–15:28:15 | Timer/arquivador parou viewer e residente para rotação | Execução falhou às 15:28:16 com `insufficient free disk for archive staging plus reserve`; unidades foram iniciadas de novo pelo fluxo do arquivador | **Observado:** staging não cabia na reserva; a raiz configurada do arquivador era episódio 3, enquanto a unidade residente apontava para episódio 5. Nenhum novo arquivo externo foi verificado. |
| 15:32:10 | Writer residente em execução | PID 176070 terminou `OperationalError: database is locked`; systemd reiniciou às 15:32:41 | **Observado:** erro e restart. Uma consulta forense longa estava na mesma janela. Em SQLite DELETE, leitor prolongado pode bloquear writer; associação é fortemente sustentada, não provada, pois journal não contém corpo do script/conexão causadora. |
| 15:40:31–15:40:52 | Episódio 5 gravou ciclo confirmado 438 em 8.780 ms, depois estado de ciclo 439 em 8.800 ms | Cursor causal continuou tick 87.800; estado posterior sem confirmação atômica | **Observado:** persistência incompleta da fronteira 8.800 ms; esse estado não é restaurável pelo contrato. |
| 15:41:09 | Writer residente em execução | PID 176413 terminou novamente `database is locked`; systemd reiniciou às 15:41:39 | **Observado:** erro e restart. Uma sessão de verificação longa incluindo `PRAGMA integrity_check` coincidiu com essa janela; interferência é fortemente sustentada, mas não comprovada. A missão anterior explicitou que as consultas forenses contribuíram para risco de bloqueio. |
| 15:41:48, 15:42:22, 15:42:55 | Três novas tentativas systemd | Cada startup recusou `resident checkpoint lacks its atomic confirmed-cycle record` | **Observado:** falha fechada de restauração, não corrupção comprovada nem retomada bem-sucedida. |
| 15:43:26 | systemd atingiu `Start request repeated too quickly` | Serviço residente `failed`, contador 5; viewer dependente inativo | **Último estado remoto capturado no arquivo anterior.** Nenhuma parada, reinício ou alteração de banco foi feita naquela missão de arquivo. |

## Retomada da missão final — inspeção não alcançou a VM

Nesta retomada, tentativa local `ssh -o BatchMode=yes flynn-1gb ...` falhou antes de executar comando remoto: `Could not resolve hostname flynn-1gb`. O binário `gcloud` também não estava instalado no cliente. Portanto o estado atual do serviço, tamanhos e hashes atuais e capacidades de escrita/leitura do bucket não foram revalidados. Nenhum restart/stop, query SQLite, cópia ou upload foi enviado. O estado de 15:43 é o último estado arquivado, não confirmação do estado presente.

Tentativa GCP anterior havia sido negada para `compute.instances.get`, `compute.instances.list`, `compute.disks.list` e `compute.addresses.list`. Os dados de episódios 3 e 5 e arrays locais continuam sem cópia externa comprovada. Veja [postmortem do processo](DEVELOPMENT_PROCESS_POSTMORTEM.md) e [inventário de descomissionamento](DECOMMISSION_INVENTORY.md).
