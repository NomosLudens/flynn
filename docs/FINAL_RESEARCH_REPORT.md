# FLYNN V2
## Relatório Final de Pesquisa e Encerramento

**Nomos Ludens — 26 de outubro de 2026**

## 1. Identificação do projeto e autoria

Projeto experimental de pesquisa neuro-sintética da Nomos Ludens, sob responsabilidade de Antonio Roberto de Oliveira. Repositório público: [`NomosLudens/flynn`](https://github.com/NomosLudens/flynn). O desenvolvimento foi encerrado por decisão do responsável em 26/10/2026.

## 2. Resumo científico

Flynn V2 investigou se uma rede LIF derivada da conectividade FlyWire FAFB v783 poderia operar em um ciclo sensório-motor persistente com interfaces corporais sintéticas. Na observação residente do episódio 5, iluminação global sintética chegou a 11.118 raízes visuais e foi seguida por spikes LIF persistidos. Nas janelas amostradas, a população descendente ficou silenciosa; não houve torque, movimento corporal ou retorno proprioceptivo efetivo demonstrado. O objetivo central — ciclo causal neuromotor fechado — não foi alcançado. A residente posteriormente falhou ao reiniciar, com cursor de checkpoint confirmado em 87.800 ms e estado parcial não confirmado em 88.000 ms. Os dados persistentes locais permanecem sem cópia externa comprovada nesta missão.

## 3. Motivação original

A motivação era construir um objeto experimental persistente, biologicamente ancorado e inspecionável, que ligasse dinâmica neural, estímulo sensorial, saída motora, corpo sintético, mundo e histórico causal. A hipótese de engenharia era que interfaces explicitamente instrumentadas permitiriam estudar essa integração sem alegar equivalência biológica.

## 4. Objetivos e hipóteses experimentais

O objetivo principal era observar se estímulos ambientais podiam produzir dinâmica neural persistente que alcançasse uma população descendente, comandasse um corpo dinâmico e gerasse propriocepção efetivamente processada no passo neural seguinte. Objetivos auxiliares incluíam identidade de episódios/generation, checkpoint restaurável, observabilidade pública e contabilidade de recursos. A atividade de LIF, isoladamente, não era o critério de sucesso do ciclo.

## 5. Histórico cronológico do desenvolvimento

- **19/10:** inicialização supervisionada na VM `flynn-1gb`; falha de continuidade entre frame 6.600 e checkpoint 6.400 gerou novo episódio, sem continuidade fictícia. Um restart posterior restaurou outro episódio em tick 620.
- **20/10:** tentativa de inicialização falhou por chamada a método inexistente `activate_causal_generation`; outra tentativa encontrou divergência de identificador de geração; uma execução posterior alcançou tick 107.800 e parou em `database is locked`.
- **21/10:** deduplicação de persistência foi aplicada diretamente no runtime sob autorização documentada; backup e verificação local do contrato foram registrados. Continuidade de dados e arquivamento remoto adicional não foram concluídos nessa etapa.
- **23/10:** incidente de ausência de amostra Pinocchio na fronteira causal às 18:21:57 UTC, seguido de ativação às 18:26:59. Observação posterior mostrava episódio 3 ativo, mas stale/sem atividade Desc ou dinâmica corporal. Ocorreram falhas do arquivador por corrida de checkpoint.
- **24/10:** observabilidade pública mostrou clock avançando em duas leituras, mas agregação LIF stale e corpo sem dinâmica pareada. Arquivo remoto de episódio 3 foi verificado até tick 3.786.800.
- **25/10:** Homeostasis V2 foi instalada como orçamento de CPU medido; isso não é metabolismo. Assimilação permaneceu desabilitada.
- **26/10:** documentos de operação registram correções de contrato no runtime e estado temporário ativo em uma coleta; o inventário posterior encontrou a residente em start-limit failed, com falhas de lock e checkpoint. Esses retratos têm horários distintos e não são tratados como simultâneos.

Os detalhes e limites de cada incidente estão em [histórico de incidentes](INCIDENT_HISTORY.md) e [postmortem de desenvolvimento](DEVELOPMENT_PROCESS_POSTMORTEM.md).

## 6. Fundamentos científicos utilizados

O substrato estrutural deriva do conectoma de *Drosophila melanogaster* adulta fêmea FlyWire FAFB v783. A dinâmica implantada era um modelo simplificado de neurônios integrate-and-fire com constantes e atrasos explícitos, não uma simulação biofísica integral. As interfaces visual, motora e proprioceptiva eram sintéticas. A literatura de conectoma e modelos de cérebro de mosca fundamenta o contexto; não valida automaticamente a implementação Flynn.

## 7. Fontes, referências e licenças

Fontes científicas incluem Dorkenwald et al. (2024), Schlegel et al. (2024), Shiu et al. (2024), Abbott (1999) e Carpentier et al. (2019), listadas ao final. A documentação histórica identifica FlyWire sob CC BY-NC 4.0; o repositório existente declara CPAL 1.0. A licença exata de cada arquivo derivado Shiu e das anotações não foi confirmada para redistribuição dos payloads. Pinocchio e demais dependências conservam licenças próprias. Por isso os arrays não foram incluídos no repositório público.

## 8. Arquitetura planejada

O caminho planejado era mundo → transdução visual/proprioceptiva → LIF → readout descendente → coordenador PicoClaw → passo Pinocchio → medida corporal → nova entrada neural. Persistência deveria vincular estado de cada fronteira a episódio, geração, sequência e checkpoint atômico. A implementação continha esses componentes e contratos parciais; o caminho completo não foi observado.

## 9. Arquitetura efetivamente implementada

O runtime Python instalava mundo sintético, transdutores, CSR assinado, engine LIF, agregador/readout, ponte PicoClaw, modelo Pinocchio de glifo, propriocepção derivada do corpo, orçamento Homeostasis V2 e SQLite. Serviços systemd residentes e viewer LETHE constituíam a superfície operacional. A árvore instalada não tinha Git metadata que vinculasse os arquivos a commit. O snapshot de 31 arquivos foi comparado ao `master` público `f69f6c0d…`: 8 iguais, 4 divergentes e 19 ausentes. Ver [arquitetura](FINAL_ARCHITECTURE.md) e [snapshot](../archive/runtime-installed/2026-10-26/README.md).

## 10. Integração com FlyWire FAFB v783

O mapa canônico contém 139.255 root IDs. A matriz runtime reporta 15.091.983 pares dirigidos e 54.492.922 sinapses; hashes do CSR e mapa estão em [`NEURAL_MODEL.md`](NEURAL_MODEL.md). A conectividade e sinais foram preparados como CSR assinado (`Excitatory * Connectivity`). A documentação antiga do repositório traz outras contagens históricas (por exemplo, 50.666.648 sinapses e 1.305 descending); o manifesto instalado usava 1.303 DNs. Esses números refletem fontes/versões/representações distintas e não são reconciliados como se fossem uma única matriz.

## 11. Implementação do modelo LIF

O modelo instalado `shiu-lif-experimental-v783-flynn-v1` usa float64, passo 0,1 ms, potencial de repouso/reset −52 mV, limiar −45 mV, constante de membrana 20 ms, sináptica 5 ms, refratário 2,2 ms, atraso dirigido 1,8 ms e peso 0,275 mV por contagem assinada. Não há disparo espontâneo ou comportamento injetado pela camada descrita. Ver [modelo neural](NEURAL_MODEL.md).

## 12. Modelo de transdução visual

Um comando escalar global `set_illumination` era normalizado e mapeado como condutância para 11.118 roots anotados R1–6/R7/R8. O próprio runtime classificava a entrada como `INSTRUMENTAL_SYNTHETIC_NOT_BIOPHYSICAL`. Não foi apresentada uma cena óptica com geometria, movimento ou calibração.

## 13. Mapeamento dos neurônios descendentes

O manifesto de readout continha 1.303 root IDs únicos e validava correspondência root/índice canônico nos registros amostrados. A investigação não encontrou mismatch de identidade. Isso verifica integridade do mapa observado; não prova adequação funcional do critério de seleção ou eficácia sob estímulos não executados.

## 14. Integração com PicoClaw

PicoClaw v0.2.9 e a ponte coordenavam recibos de frame e transportavam dados de readout. Recibos foram observados; os ciclos reportaram saída zero/observacional. Coordenação foi parcial, sem evidência de que PicoClaw tenha produzido atuação corporal efetiva.

## 15. Integração com Pinocchio

Pinocchio foi usado para algoritmos de dinâmica rígida no corpo sintético, com distribuição Python `pin==4.1.0`, `cmeel==0.61.0`, NumPy 2.2.6. Passos foram despachados com torque zero; pose e velocidade não mudaram. Uma importação fora do ambiente da unidade falhou em encontrar `libgomp.so.1`; o serviço configurava um `LD_LIBRARY_PATH` próprio.

## 16. Construção e representação do corpo do glifo

O modelo tinha 23 nós nomeados, 22 links/juntas selecionados na árvore dinâmica e oito relações de grafo somente estruturais. A raiz planar X/Y/yaw era sintética, livre e sem ancoragem mecânica confirmada ao EB central. O modelo não constitui reconstrução anatômica de mosca nem demonstra locomoção do glifo. Detalhes e as oito arestas estão em [`EMBODIMENT.md`](EMBODIMENT.md).

## 17. Sistema de propriocepção

O transdutor derivava sinais de posições/velocidades corporais e mapeava a população mecanossensorial. Sem deslocamento observado, os registros relevantes indicaram zero alvos e `NO_PHYSICAL_DEVIATION_NO_NEURAL_INPUT`. Um caminho de serialização existe; retorno proprioceptivo causal a um passo LIF posterior não foi demonstrado.

## 18. Homeostase e reserva energética

`homeostasis-v2-measured-cpu-budget-1` contabilizava CPU medido: reserva normalizada [0,1], escala cheia de 3.600 segundos de CPU, débito `min(reserve, cost/3600)` na fronteira seguinte. Assimilação falhava fechada sem fonte e conversão verificáveis. Isso é contabilidade operacional, não metabolismo, ATP, alimentação ou energia biológica. Ver [Homeostasis V2](HOMEOSTASIS.md).

## 19. Persistência, episódios e checkpoints

SQLite schema 1 contém metadata, mapeamentos, eventos, estímulos, estados de componente, controle do coordenador e gerações causais. A inspeção registrou `journal_mode=DELETE`. Identidade exige episódio e geração além de tick. O episódio 5 tinha cursor causal confirmado em 87.800 ms; estado parcial 88.000 ms carecia do registro atômico. Os NPZ armazenavam arrays LIF e snapshots. O manifesto publicado contém hashes/caminhos, não payloads. Ver [persistência](PERSISTENCE_AND_EPISODES.md).

## 20. LETHE e observabilidade

LETHE expunha superfície de observação do runtime via viewer local associado ao fluxo público. Uma coleta de 24/10 registrou API com avanço de 60 ms neurais em 47,008 s de parede, mas leitura LIF stale, corpo `q/qdot` zero, readout proprioceptivo nulo e pose dinâmica ausente. No inventário final de 26/10, o endpoint público respondeu HTTP 502 com viewer inativo. Não há validação manual de LETHE pós-falha neste arquivamento.

## 21. Infraestrutura computacional

A documentação operacional identifica projeto Google Cloud `kaline-totalidade`, VM `flynn-1gb`, e2-micro, 1 GiB RAM e disco de 10 GiB, historicamente em `us-central1-f`. Uma anotação posterior diverge na zona; nesta missão não foi possível resolver a diferença nem conferir a VM atual porque `gcloud` não está instalado e `ssh flynn-1gb` não resolve. Uma captura anterior reportava 964 MiB RAM total, sem swap, e 1,2 GB livres no filesystem raiz. Esses valores são snapshots históricos, não uma fotografia atual.

## 22. Experimentos efetivamente realizados

As evidências disponíveis incluem: execução residente de iluminação global e janelas LIF no episódio 5; amostra separada de 30 minutos para throughput; observações separadas de coordenação/PicoClaw/Pinocchio/propriocepção; e reconstruções isoladas de segmentos históricos do episódio 3. Identificadores, limites de comparação e vereditos estão em [resultados finais](EXPERIMENTAL_RESULTS_FINAL.md). Não houve novo experimento nesta missão.

## 23. Resultados quantitativos

Nas cinco janelas de 1 s do episódio 5 (4.020–8.020 ms), houve 381.696–1.021.001 spikes e 12.417–12.447 neurônios ativos; Desc foi zero em todas. Em 5.020 ms, o pico observado foi 1.021.001 spikes e 12.447 ativos. Uma observação separada registrou ~1.380 ms neurais em 1.800 s de parede (~1.304× mais lenta que tempo real). O ciclo de 20 ms custou cerca de 10,53 CPU s na amostra, 7,34 no núcleo neural/agregação. Não se afirma que essas medições pertençam à mesma execução.

## 24. Resultados negativos

Não houve Desc spikes nas janelas analisadas, torque não nulo, deslocamento corporal, alvo proprioceptivo efetivo ou loop sensório-motor fechado demonstrado. Assimilação de energia não estava disponível. O corpo não tinha mecânica validada para as oito arestas gráficas. A ausência nessas condições é resultado negativo da implementação observada, não prova de impossibilidade geral.

## 25. Falhas de integração

Houve chamada a método inexistente, divergência de identificador de geração, falha Pinocchio por amostra ausente na fronteira causal em 23/10 18:21:57 UTC, saída DN zero nas janelas, torque zero, falta de consequência corporal e retorno proprioceptivo sem alvo. Esses defeitos e não demonstrações são separados no [relatório de falha](FINAL_FAILURE_ANALYSIS.md).

## 26. Problemas de desempenho

O throughput de uma observação foi cerca de 1.304× mais lento que tempo real. A etapa neural/agregação dominou o custo medido naquela amostra. RAM/disco limitados, processos separados e reserva de staging influenciaram a operação. Não há evidência de que uma otimização não executada teria resolvido a diferença.

## 27. Incidentes operacionais

Incidentes documentados incluem divergências checkpoint/frame; inicializações rejeitadas por contratos de método/geração; locks SQLite; corrida e falta de espaço do arquivador; serviço systemd reiniciado automaticamente; remoção/restauração de `_handle_signal`; falha por fronteira Pinocchio; HTTP 502; e start-limit com cinco tentativas em 26/10 15:43:26 UTC. A atribuição de causa é graduada conforme fonte em [histórico](INCIDENT_HISTORY.md).

## 28. Limitações metodológicas

A entrada não era visão de uma cena realista; o mapeamento motor era instrumental; o corpo era planar e sintético; a medição de tempo neural foi de uma observação; populações e episódios variaram; o runtime não tinha commit; restaurabilidade dependia de registro atômico; leituras SQLite podiam interferir no writer. Não foi demonstrada reprodução independente ponta a ponta.

## 29. Causas demonstradas e hipóteses abertas

**Demonstrado:** cursor/registro atômico ausente em 88.000; mensagens `database is locked`; chamadas/gerações incompatíveis documentadas; limite de reinicialização; serviço failed na última inspeção anterior. **Hipótese fortemente sustentada, não comprovada:** consultas prolongadas contribuíram para locks. **Desconhecido:** processo exato que segurou cada lock, razão da ausência Desc sob outros estímulos e estado atual da VM.

## 30. Reprodutibilidade

`REPRODUCIBILITY=UNVERIFIED`. O snapshot fonte, resultados e manifests são úteis para revisão, mas dados científicos essenciais e arrays de conectoma não estão no GitHub; dependências, lib nativa e configuração integral também não foram reproduzidas. Ver [status de reprodutibilidade](REPRODUCIBILITY_STATUS.md).

## 31. Lições técnicas e científicas

Identidade de execução precisa acompanhar toda evidência; restauração requer cursor atômico e checkpoint pareados; diagnósticos de banco contam como carga; atividade neural não prova comportamento; componentes presentes não provam interfaces funcionais; e versão instalada precisa de proveniência. O [postmortem](DEVELOPMENT_PROCESS_POSTMORTEM.md) documenta limites do processo sem buscar culpados.

## 32. Limites das conclusões

As conclusões dizem respeito à implementação e aos estímulos observados. Não se afirma que o cérebro de *Drosophila*, o modelo LIF em geral ou a integração neurocorporal sejam inválidos ou impossíveis. Não há evidência de consciência, senciência, aprendizado associativo ou comportamento autônomo.

## 33. Fundamentação do encerramento

O responsável encerrou o projeto após falhas operacionais sucessivas e ausência da demonstração central. A pesquisa não cumpriu o objetivo do ciclo neuromotor fechado. O relatório não transforma essa falha de implementação/execução em conclusão contra a hipótese científica geral.

## 34. Considerações finais

Flynn V2 produziu um runtime experimental com atividade neural persistida e documentação suficiente para avaliação crítica parcial. O sistema não foi validado como organismo artificial funcional e integrado. A pesquisa está encerrada; runtime, banco, checkpoints e infraestrutura não devem ser modificados ou removidos antes de resolver a preservação dos dados remanescentes.

## 35. Referências e anexos

1. Dorkenwald et al. (2024). “Neuronal wiring diagram of an adult brain.” *Nature* 634, 124–138. [doi:10.1038/s41586-024-07558-y](https://doi.org/10.1038/s41586-024-07558-y).
2. Schlegel et al. (2024). “Whole-brain annotation and multi-connectome cell typing of Drosophila.” *Nature*. [doi:10.1038/s41586-024-07686-5](https://doi.org/10.1038/s41586-024-07686-5).
3. Shiu et al. (2024). “A Drosophila computational brain model reveals sensorimotor processing.” *Nature*. [doi:10.1038/s41586-024-07763-9](https://doi.org/10.1038/s41586-024-07763-9).
4. Abbott (1999). “Lapicque’s introduction of the integrate-and-fire model neuron (1907).” *Brain Research Bulletin* 50(5–6), 303–304. [doi:10.1016/S0361-9230(99)00161-6](https://doi.org/10.1016/S0361-9230(99)00161-6).
5. Carpentier et al. (2019). “The Pinocchio C++ library.” [doi:10.1109/SII.2019.8700380](https://doi.org/10.1109/SII.2019.8700380).

Anexos técnicos: [arquitetura final](FINAL_ARCHITECTURE.md), [análise da falha](FINAL_FAILURE_ANALYSIS.md), [histórico de incidentes](INCIDENT_HISTORY.md), [resultados finais](EXPERIMENTAL_RESULTS_FINAL.md), [reprodutibilidade](REPRODUCIBILITY_STATUS.md), [inventário de descomissionamento](DECOMMISSION_INVENTORY.md) e [manifestos de fonte/dados](../archive/runtime-installed/2026-10-26/README.md).
