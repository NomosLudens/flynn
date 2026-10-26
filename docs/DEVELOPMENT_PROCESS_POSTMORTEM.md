# FLYNN V2 — Postmortem do Processo de Desenvolvimento

**Escopo:** processo técnico e evidências documentadas até 26/10/2026.  
**Propósito:** identificar condições que levaram a regressões, perdas de continuidade e conclusões excessivamente amplas, sem atribuir culpa individual sem evidência.

## Síntese

O trabalho acumulou código implantado diretamente na VM, um checkout local com WIP divergente, ensaios de recuperação em múltiplas cópias e uma cadeia de componentes cuja integração causal não foi provada antes de afirmações de prontidão. A infraestrutura de 1 GiB, reserva de disco apertada, execução multiprocesso e SQLite em modo DELETE tornavam operações longas de leitura e cópia particularmente sensíveis. Os registros permitem apontar fatores e incidentes; não sustentam uma causa única para todas as regressões.

## Respostas às questões de processo

### 1. Por que ocorreram regressões sucessivas?

O caminho residente atravessava Python, SQLite, processos PicoClaw/Go, Pinocchio e systemd. Contratos de identidade de geração, métodos chamados pelo runtime e checkpoints atômicos nem sempre foram verificados como um conjunto na versão instalada. O histórico local registra, entre outros, chamada a método inexistente em `activate_causal_generation`, divergência de `causal_generation_id`, amostras Pinocchio ausentes numa fronteira e remoção acidental de `_handle_signal`. Esses são casos comprovados, não explicação completa de cada falha.

### 2. Por que diagnósticos interferiram com a execução?

SQLite estava em `journal_mode=DELETE`; um leitor prolongado pode manter lock compartilhado que impede a escrita exclusiva. Dois `database is locked` coincidiram com consultas longas, incluindo `PRAGMA integrity_check`. A correlação é forte e foi registrada como risco causal, mas o journal não identifica de modo conclusivo qual processo reteve cada lock. Isso mostra que o procedimento de inspeção não separou suficientemente a observabilidade potencialmente bloqueante da janela do writer residente.

### 3. Por que runtime e repositório divergiram?

Os arquivos foram instalados por pacote copiado para uma árvore datada da VM sem metadados Git suficientes para registrar commit de origem. O snapshot final comparado ao `master` remoto de referência encontrou 8 arquivos iguais, 4 diferentes e 19 ausentes. O checkout local também continha WIP não publicado. Não havia uma única revisão imutável que identificasse checkout, artefato implantado e processo residente ao mesmo tempo.

### 4. Por que houve alterações diretas no runtime?

O histórico registra intervenções autorizadas em arquivos instalados na VM para corrigir contratos operacionais e colocar a residência em execução. A decisão reduziu a distância até experimentar, mas cada alteração aumentou o risco de deriva em relação ao Git e exigia backup, hash, promoção e registro de proveniência estritos. Não se conclui que toda alteração direta foi inadequada; conclui-se que o resultado acumulado ficou mais difícil de reproduzir e auditar.

### 5. Quais proteções estavam ausentes ou insuficientes?

- Artefato implantável ligado a commit/hash e trilha de aprovação reprodutível.
- Gates automatizados sobre contratos de ciclo atômico, episódio/geração e referências de checkpoint antes de qualquer retomada.
- Política de diagnóstico que limitasse duração, concorrência e custo de I/O para SQLite em DELETE.
- Reserva de disco consistente com tamanho real do staging do arquivador.
- Ensaio de shutdown/restore com cópia verificável antes de declarar continuidade recuperável.
- Prova em um mesmo episódio e geração para sensor, LIF, readout, atuação, movimento e propriocepção posterior.
- Registro de produção que vinculasse cada resultado a uma versão e condição experimental inequívocas.

Esta lista é análise do processo a partir dos incidentes; não é afirmação de que uma proteção isolada teria evitado todos eles.

### 6. Quais verificações provaram apenas atividade parcial?

Builds, testes isolados, mapeamento de raízes, atividade visual/LIF, recibos PicoClaw, dispatch Pinocchio e HTTP 200 provavam apenas os respectivos limites de interface. Nenhum demonstrava por si só torque não nulo, deslocamento ou retorno proprioceptivo. Checkpoint existente sem cursor atômico não comprovava restauração; arquivos ou ticks iguais de episódios diferentes não comprovavam continuidade.

### 7–8. Como gates foram interpretados? Houve sucesso amplo demais?

Há documentos históricos que usaram `PASS` ou linguagem de integração ao descrever testes de contrato, atividade parcial ou serviço ativo. A releitura final distingue esses resultados de `FULL_CAUSAL_LOOP=NOT_DEMONSTRATED`. Não existe aqui inventário exaustivo de todas as declarações feitas em cada conversa; não se atribui intenção. Em termos de processo, o escopo do gate nem sempre foi suficientemente explícito para impedir que sucesso local ou operacional fosse entendido como sucesso científico do sistema completo.

### 9–10. Que evidências não sustentavam o estado informado e por que a recuperação se repetiu?

Uma população carregada e root IDs alinhados sustentavam validade do mapeamento observado, não eficácia sensorial. Ciclos confirmados até um checkpoint sustentavam persistência até aquela fronteira, não continuidade futura. Serviço `active` em uma fotografia não sustentava residência ininterrupta nem integração corporal. A recuperação recorrente foi favorecida pela diferença entre estado esperado e estado instalado, por tentativas de retomar dados parcialmente confirmados, contratos cruzados entre processos e evidência insuficiente do caminho completo antes de cada mudança.

### 11–12. Infraestrutura e responsabilidades indeterminadas

A VM e2-micro documentada tinha 1 GiB de RAM, sem swap configurada para a residente e disco de 10 GiB. Em capturas, o espaço livre caiu perto ou abaixo da reserva operacional. A observação de performance avançou cerca de 1.380 ms neurais em 1.800 s de parede; uma execução específica não permite atribuir todo o resultado à infraestrutura. Permanecem indeterminados o processo exato que segurou cada lock, o efeito causal isolado de cada falha sobre dados persistidos, a origem Git exata do pacote instalado e o estado atual da VM nesta retomada sem acesso SSH/GCP.

## Lições e ações de encerramento

1. Uma instalação residente deve ser identificável por revisão imutável e hashes antes de iniciar.
2. Diagnóstico do armazenamento precisa ser planejado como carga concorrente, especialmente em SQLite DELETE.
3. O contrato de restauração deve exigir cursor, geração, checkpoint e registro atômico pareados.
4. A unidade de prova científica é a cadeia causal observada no mesmo episódio e geração.
5. Serviço vivo, API disponível e atividade neural são estados parciais, não substitutos do comportamento corporal pretendido.
6. A documentação final mantém incidentes e resultados negativos visíveis e marca as atribuições incertas.

O projeto está encerrado por decisão do responsável. Este postmortem registra fatores de processo; não propõe nova versão, reestruturação ou novo experimento.
