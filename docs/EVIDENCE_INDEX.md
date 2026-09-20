# Flynn — índice de evidências recuperadas

## Fonte local atual

/home/tonyus-dev/Documents/ChatGPT/FLYNN

O diretório estava sem commits e sem remoto. O conteúdo local foi preservado;
__pycache__, bancos e estado de execução não fazem parte do kit.

## Evidência histórica

| Área | Artefato | Classificação |
| --- | --- | --- |
| Loop encarnado | closed_loop/CLOSED_LOOP_* | evidência histórica do host max |
| Alimentação | caverna_food_ui/CAVERNA_FOOD_* | evidência histórica, contato não alcançado |
| Corpo | app/body/pinocchio_sigil.py | fonte recuperada, depende do runtime ausente |
| Mundo | app/world/continuous_world.py | fonte recuperada, depende do runtime ausente |
| Cérebro | app/brain/clock.py | fonte recuperada, dependências auxiliares ausentes |
| E01 | research/e01/ | kit reproduzível isolado |
| Mapa de percurso | docs/MAPA_DE_PERCURSO_FLYNN.md | fonte operacional histórica, atualizada em 2026-09-15 |
| Adendo de encerramento | docs/FLYNN_DELTA_ATUALIZACAO_MAPA_DE_PERCURSO.md | atualização histórica posterior; projeto congelado |
| Prints de interface | docs/PRINTS_EVIDENCIA_VISUAL.md | capturas históricas fornecidas pelo autor, com hashes |

## Resultados preservados

- E01: PARTIAL; Pinocchio 4.1.0, ARM64/Python 3.12, corpo sintético URDF
  com quatro DoF.
- E01: testes de indisponibilidade de ZeroClaw/Pinocchio e rejeição de limites
  passaram em modo fail-closed.
- E01: coordenação permaneceu em adapter experimental externo; não foi
  promovida para ZeroClaw.
- Loop residente: havia evidência de cérebro, mundo e corpo contínuos, mas a
  janela de estabilidade de memória não foi concluída antes da perda do host.
- MAX: indisponibilidade foi host-wide; a causa exata não foi comprovada.

O mapa de percurso fornecido posteriormente registra uma fase mais avançada
do produto em 2026-09-15, incluindo E01-D PASS, E01-N PARTIAL, E03 PASS,
H01 PASS_WITH_RESEARCH_BLOCKER e trajetória residente persistente. Esses
resultados são históricos do MAX e não substituem a verificação atual,
bloqueada pela perda de acesso à VM.

O adendo posterior registra que `ENERGY_TO_BODY_CAPACITY` foi implementado,
que o floor de capacidade viva foi corrigido para `0.01`, que a semântica de
locomoção foi separada de movimento geométrico do corpo e que a Caverna móvel
foi implementada. Ele também preserva os limites: contato/consumo real não
foram observados, a correção de crescimento linear de memória ficou
`UNVERIFIED` e a continuidade residente foi interrompida externamente.

O estado canônico posterior é `PROJECT_STATUS=RETIRED_FROZEN`,
`RESIDENT_RUNTIME_STATUS=INTERRUPTED_EXTERNALLY` e
`CURRENT_RESUMPTION_PLAN=NONE`. A suspensão Oracle, a perda de acesso e a
eventual exclusão de dados continuam separadas: `RESOURCE_DELETION=UNPROVEN`
e `DATA_PRESERVATION=UNKNOWN`. O adendo não é prova de que o runtime esteja
operacional hoje.

## Proveniência a recuperar

Os registros apontam para os caminhos históricos:

- /home/ubuntu/Portifolio/flynn-max/fruit-fly-lab;
- /home/ubuntu/Portifolio/flynn-max/data/flywire-v783;
- /home/ubuntu/Portifolio/flynn-max/runtime.

Eles não são considerados presentes nem atuais. Este índice não substitui
volume, backup ou console do provedor.
