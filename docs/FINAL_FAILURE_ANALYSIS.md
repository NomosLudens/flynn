# FLYNN V2 — Análise Técnica e Científica da Falha

**Projeto:** Nomos Ludens · **responsável:** Antonio Roberto de Oliveira  
**Data de encerramento:** 26 de outubro de 2026  
**Veredito:** `FULL_CAUSAL_LOOP=NOT_DEMONSTRATED`

## Síntese

O experimento demonstrou que uma entrada visual global sintética podia alcançar a população visual mapeada e ser seguida por atividade LIF persistida. Não demonstrou a cadeia que converteria essa atividade em saída descendente, atuação, deslocamento corporal e retorno proprioceptivo processado por uma etapa neural posterior. A conclusão se limita à implementação, aos estímulos e às janelas amostradas; não demonstra impossibilidade científica nem invalida o conectoma ou o modelo biológico.

## Ciclo pretendido e primeiro elo sem demonstração

```text
Mundo
→ estímulo sensorial
→ transdução
→ rede LIF
→ atividade descendente
→ coordenação PicoClaw
→ atuação Pinocchio
→ deslocamento corporal
→ propriocepção
→ retorno neural
```

Na observação residente do episódio 5, a iluminação global foi registrada e a atividade LIF foi persistida. A população descendente permaneceu sem spikes nas cinco janelas de um segundo documentadas entre 4.020 e 8.020 ms. Assim, o primeiro elo do caminho pretendido sem continuidade funcional observada foi **atividade visual/LIF → saída descendente**. O mapeamento `root_id`/índice canônico foi validado nos registros amostrados; a investigação não encontrou erro de identidade que explique os zeros. Isso não prova que o readout responderia a estímulos diferentes.

O estímulo foi iluminação escalar global `1.0`, convertida em incremento instrumental de condutância `0.5` para 11.118 raízes R1–6/R7/R8. Não havia padrão espacial, movimento de cena ou calibração óptica. Foram identificadas três arestas visuais diretas para DNs (`OPTIC_L→DN_TAKEOFF`, `OPTIC_R→DN_TAKEOFF`, `OPTIC_R→DN_LONG_MODE`); existência estrutural não prova que o estímulo global cause spikes nesses alvos. Ver [resultados](EXPERIMENTAL_RESULTS_FINAL.md) e [modelo neural](NEURAL_MODEL.md).

## Resultados quantitativos e seus contextos

Para uma única janela de 1 s no episódio 5, geração `ffc7f14f56c149268e695faaf40a0451`, foram registrados 1.021.001 spikes e 12.447 neurônios ativos, com zero spikes descendentes. Outras janelas desse conjunto registraram 381.696 a 1.020.669 spikes e 12.417–12.423 neurônios ativos; em todas, a população Desc observada ficou em zero. Os 1.303 root IDs descendentes do manifesto foram reconhecidos no mapa canônico. Essas métricas são contagens de atividade no modelo, não comportamento.

Uma medição separada de 1.800 s de parede avançou aproximadamente 1.380 ms neurais, razão aproximada de 1.304 vezes mais lenta que tempo real. A evidência preservada não associa de forma suficiente essa medição de desempenho à mesma janela, episódio ou geração das cinco janelas acima; elas não são combinadas como uma só execução. A etapa LIF/agregação custou cerca de 7,34 CPU s por ciclo neural de 20 ms, e o custo total amostrado foi cerca de 10,53 CPU s por ciclo. A VM tinha aproximadamente 964 MiB de RAM, sem swap, e uma captura posterior registrou 1,2 GB livres no disco raiz. Isso caracteriza aquela infraestrutura e medição, não um limite universal do modelo.

## Coordenação, atuação e corpo

Recibos de coordenação PicoClaw foram observados, mas a ponte estava em modo observacional. Sem saída Desc efetiva, os quadros enviados ao Pinocchio tinham torque zero. O dispatch de passos Pinocchio foi registrado; a pose e a velocidade permaneceram estáticas. Portanto coordenação de frames foi demonstrada parcialmente, mas atuação efetiva e consequência corporal não foram.

O corpo era um glifo sintético planar XY/yaw, com 23 módulos nomeados, 22 links na árvore dinâmica e oito arestas exclusivamente gráficas. O estado do modelo não estava ancorado mecanicamente ao EB central como a descrição de propriocepção sugeria. Não havia evidência de restrições mecânicas para as oito arestas nem de locomoção integral do glifo.

## Propriocepção

O transdutor derivava medidas do estado do corpo. Como não foi observado desvio corporal, os registros amostrados indicaram `NO_PHYSICAL_DEVIATION_NO_NEURAL_INPUT` e zero alvos. Não se demonstrou sinal proprioceptivo efetivo chegando a uma etapa LIF posterior. A existência de código ou de registros de estado não substitui essa prova causal.

## Falhas de execução e persistência

- Episódios e gerações distintos possuem cursores e checkpoints próprios; ticks iguais não estabelecem continuidade. O episódio 5 (`resident-v2:flynn-1gb:19bc839e52474f3f9a3ec12eefaf1647`) tinha geração `ffc7f14f56c149268e695faaf40a0451`.
- O último cursor causal confirmado do episódio 5 era tick 87.800 / 8.780 ms. Há estado parcial em 88.000 / 8.800 ms sem o registro atômico de ciclo confirmado exigido para restauração. Tentativas automáticas falharam fechadas com `resident checkpoint lacks its atomic confirmed-cycle record`.
- A SQLite estava em `journal_mode=DELETE`. O journal registrou dois `OperationalError: database is locked` antes das falhas de inicialização. Consultas forenses longas, incluindo uma sessão com `PRAGMA integrity_check`, coincidiram temporalmente com esses erros e poderiam manter lock compartilhado. A hipótese de interferência das leituras é fortemente sustentada pela coincidência e pelo modo DELETE; o journal sudo não conserva o corpo dos scripts nem identifica a conexão bloqueadora. Portanto, a causalidade não é comprovada.
- O systemd executou reinicializações automáticas. Às 15:43:26 UTC de 26/10, o serviço atingiu o limite após cinco tentativas e ficou `failed`; o viewer dependente estava inativo. Essa foi a última inspeção operacional arquivada. Nesta missão não foi possível atualizar esse estado: o hostname SSH não resolveu e `gcloud` não está instalado no cliente. O runtime atual é, portanto, `UNVERIFIED` nesta retomada.
- O endpoint público respondeu HTTP 502 enquanto o viewer estava indisponível. HTTP 200 anterior não foi considerado prova de dados residentes recentes.
- O timer do arquivador tentou parar serviços, mas a execução falhou por espaço insuficiente para staging e reserva. Um checkpoint alvo também faltou em uma tentativa anterior, resultando em `FileNotFoundError` e `BrokenPipeError` no zstd; consulte o histórico para contexto e horários.

## Intervenções assistidas e proveniência

Em uma implantação anterior foi removido `_handle_signal`, causando duas falhas de inicialização reportadas em notas de implantação. O handler foi restaurado e a documentação descreve retorno ao mesmo episódio. Os horários exatos dessas duas tentativas não estão conservados no journal final; essa sequência vem das notas locais contemporâneas, não de uma nova verificação na VM.

O código instalado não tinha metadados Git que permitissem associá-lo a commit. Comparado ao `master` público no commit `f69f6c0d2193e128df97ca58cabca75c06636172`, o snapshot de 31 arquivos teve 8 correspondências byte a byte, 4 diferenças e 19 arquivos ausentes. A origem histórica de um commit não é inferida. O processo de desenvolvimento, regressões e limites de responsabilização estão em [postmortem](DEVELOPMENT_PROCESS_POSTMORTEM.md).

## Conclusão e limites causais

**Demonstrado:** entrada visual sintética alcançou a população mapeada; spikes LIF foram observados e persistidos; coordenação de frames e dispatch Pinocchio foram registrados.  
**Não demonstrado:** atividade descendente sob as janelas documentadas, torque não nulo, movimento do corpo, retorno proprioceptivo efetivo, ciclo causal completo, locomoção integral do glifo e restauração do cursor parcial de 88.000.  
**Inferido com cautela:** leituras longas podem ter contribuído aos locks, pois coincidiram com os erros em SQLite DELETE.  
**Desconhecido:** se outro estímulo, modelo corporal ou capacidade computacional produziria o comportamento pretendido; estado atual da VM e preservação externa dos dados locais nesta sessão.

O resultado é uma falha experimental e operacional da implementação executada em atingir seu objetivo central. Não prova que a integração pretendida seja impossível nem que o modelo biológico original seja inválido.
