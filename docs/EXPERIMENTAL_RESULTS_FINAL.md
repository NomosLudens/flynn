# Resultados Experimentais Finais

Esta consolidação separa evidências por identidade e condição. Janelas neurais do episódio 5 não são combinadas com medição de desempenho sem identidade explícita, segmentos remotos do episódio 3 ou ensaios de restauração. Um manifesto de hashes não contém o payload dos dados.

## Experimento E1 — estímulo visual e atividade LIF residente

| Campo | Evidência |
|---|---|
| Episódio / geração | episódio 5: `resident-v2:flynn-1gb:19bc839e52474f3f9a3ec12eefaf1647`; `ffc7f14f56c149268e695faaf40a0451` |
| Código | Runtime instalado sem commit Git demonstrável; snapshot de 31 arquivos e manifestos em [`archive/runtime-installed/2026-10-26/`](../archive/runtime-installed/2026-10-26/README.md) |
| Estímulo | `set_illumination`, luz global normalizada 1.0; incremento 0.5 por tick; entrada instrumental sintética, hash `36b0d95c6e5546d03c0f7c65f617dd1332f8f94503a245b847d68ba2ecbbc5d0` |
| Duração | Agregados em janelas de 1 s de tempo neural entre 4.020 e 8.020 ms. Duração de parede para estas janelas não registrada neste resumo. |
| Medições | 11.118 raízes visuais alcançadas; cinco janelas com 381.696–1.021.001 spikes e 12.417–12.447 neurônios ativos; 1.303 raízes Desc acompanhadas; zero spikes Desc em todas as janelas. |
| Resultado | Atividade LIF induzida e persistida observada; resposta descendente não observada sob este estímulo. |
| Limitação / veredito | Luz global sem padrão espacial ou movimento; a evidência não prova incapacidade de resposta a outros estímulos. **PARTIAL: entrada→LIF observada; saída corporal não demonstrada.** |

A janela de 5.020 ms conteve especificamente 1.021.001 spikes e 12.447 neurônios ativos. Não se generaliza esse máximo para toda a execução.

## Experimento E2 — desempenho de uma observação de 30 minutos

| Campo | Evidência |
|---|---|
| Episódio / geração | Não associados com segurança no registro consolidado aqui disponível. |
| Duração | 1.800 s de parede; aproximadamente 1.380 ms neurais avançados. |
| Medições | Passo LIF configurado 0,1 ms; ciclo coordenador 20 ms; cerca de 10,53 CPU s/ciclo, sendo 7,34 s/ciclo atribuídos ao núcleo neural/agregação. |
| Resultado | Aproximadamente 1.304 vezes mais lento que tempo real naquela observação. |
| Limitação / veredito | Não combinar com E1 sem identidade causal da execução. **OBSERVADO, escopo único.** |

## Experimento E3 — coordenação, Pinocchio e propriocepção no episódio 5

| Campo | Evidência |
|---|---|
| Episódio / geração | Episódio 5 / geração `ffc7f14f56c149268e695faaf40a0451` para registros residentes amostrados. |
| Estímulo / entrada motora | Frames coordenados; readout Desc zero nos agregados documentados. |
| Medições | Recibos PicoClaw observados; saída com torque zero; dispatch de passo Pinocchio; pose/velocidade estáticas; transdutor proprioceptivo registrou `NO_PHYSICAL_DEVIATION_NO_NEURAL_INPUT`, zero alvos. |
| Resultado | Nenhuma atuação corporal, deslocamento ou retorno proprioceptivo efetivo demonstrado. |
| Limitação / veredito | Registros de coordenação e despacho não equivalem a movimento. **CICLO FECHADO NÃO DEMONSTRADO.** |

## Experimento E4 — arquivo e restauração de histórico remoto

O catálogo existente registra sete segmentos de episódio 3 até tick 3.786.800, com várias gerações. Um segmento 2.153.401–3.414.000, identificado como geração `generation-3e89139858f046dbbfe642b55f1809e2`, teve leitura/decompressão e reconstrução isolada já verificadas. Isso não o transforma no episódio 5. O banco local de episódio 3 alcança tick 4.468.400. Para a cobertura e proveniência, veja [`Persistence and episodes`](PERSISTENCE_AND_EPISODES.md) e o manifesto de 74 arquivos. 

## Experimento E5 — restauração de checkpoint do episódio 5

O cursor causal confirmado permaneceu em tick 87.800 / 8.780 ms. Há arquivo de checkpoint para tick 88.000 e registros parciais de componentes nesse tempo, mas falta o registro atômico de ciclo confirmado exigido pelo runtime. Inicializações automáticas posteriores foram recusadas com essa inconsistência e o serviço atingiu o start limit após cinco tentativas. O checkpoint de 88.000 não é classificado como restaurável. Nenhuma restauração foi tentada no arquivamento final.

## Resultado científico agregado

**Demonstrado:** entrada escalar alcançou a população visual; LIF produziu e persistiu spikes; recibos de coordenação e despacho de passo foram registrados.  
**Não demonstrado:** spikes descendentes no estímulo testado; torque não nulo; deslocamento; feedback proprioceptivo neural posterior; locomoção integral do glifo; ciclo causal neuromotor fechado.  
**Não verificado:** reprodução independente ponta a ponta; associação da observação de desempenho com E1; estado atual da VM e dos dados locais nesta retomada.
