# Flynn — replicabilidade e limites

Flynn é preservada como **arquivo técnico e pesquisa experimental encerrada**. O objetivo desta publicação é tornar reproduzíveis os artefatos que foram efetivamente preservados sem fingir que o estado residente perdido ainda existe.

## Matriz de replicabilidade

| Componente | Estado de distribuição | O que pode ser reproduzido |
| --- | --- | --- |
| Código recuperado em `app/` e superfícies web | **AVAILABLE / ARCHIVAL** | inspeção, estudo e reconstrução parcial das camadas preservadas |
| Closed loop e Caverna Food UI | **EVIDENCE + IMPLEMENTATION PRESERVED** | implementação e traços históricos preservados no repositório |
| Experimento isolado E01 | **REPLICABLE_WITH_EXTERNAL_DEPENDENCY** | runner, corpo sintético, testes fail-closed e geração de artefatos |
| Corpo mínimo E01 | **REPLICABLE** | `research/e01/flynn_e01_minimal_body.xml` |
| Pinocchio usado no E01 | **PINNED** | distribuição `pin==4.1.0` |
| ZeroClaw usado no E01 | **EXTERNAL / NOT BUNDLED** | exige binário real compatível e Unix socket funcional |
| Estado residente final de Flynn | **NOT RECONSTRUCTIBLE FROM THIS REPOSITORY** | não alegar reconstrução integral |
| SQLite, ledger canônico, checkpoints e estado temporal da MAX | **NOT RECOVERED** | ausentes |
| Continuidade temporal residente original | **IRREPRODUCIBLE BY DEFINITION** | uma nova execução seria uma nova instância temporal |
| Screenshots históricos | **EVIDENCE ONLY** | documentam observações passadas; não provam disponibilidade atual |

## O que é reproduzível hoje

O artefato com receita técnica explícita é o **E01**.

A partir da raiz do repositório:

```bash
python3 -m venv research/e01/.venv
research/e01/.venv/bin/python -m pip install --only-binary=:all: -r research/e01/requirements.txt
```

A execução exige um ZeroClaw real e compatível. O procedimento completo, argumentos e critérios de falha estão em [docs/REPLICATION_RUNBOOK.md](docs/REPLICATION_RUNBOOK.md).

O repositório **não fornece mock, stub ou fallback falso** para substituir essa dependência. Se o ZeroClaw real não estiver disponível, o E01 não deve ser declarado reproduzido.

## O que não deve ser alegado

Publicar o código recuperado não reconstrói automaticamente:

- a residente Flynn;
- o estado persistente que existia na VM MAX;
- o ledger canônico;
- os bancos SQLite;
- checkpoints não recuperados;
- a continuidade temporal anterior à interrupção;
- resultados científicos que o próprio arquivo registra como não provados.

Em particular:

```text
E01_REPLICATION != RESIDENT_FLYNN_RECONSTRUCTION
SOURCE_CODE_BACKUP != RESIDENT_STATE_BACKUP
HISTORICAL_EVIDENCE != CURRENT_RUNTIME
```

## Compromisso de replicabilidade

Os artefatos distribuídos neste repositório devem ser **reconstruíveis dentro dos limites declarados**, não apenas inspecionáveis.

Se uma receita documentada falhar porque um componente sob controle da Nomos Ludens está faltando, abra uma issue neste repositório descrevendo:

1. o passo executado;
2. o ambiente utilizado;
3. o componente ausente ou erro observado;
4. a saída real obtida.

Quando a peça puder ser publicada de forma segura, legal e tecnicamente fiel, ela será disponibilizada ou o caminho de reprodução será documentado. Uma lacuna não deve ser escondida com simulação.

## Regra de evidência

```text
IMPLEMENT -> OBSERVE_REAL_RESULT -> VALIDATE -> CLOSE_OR_FIX_REAL_BLOCKER
```

Build, import bem-sucedido, HTTP 200 ou interface renderizada não substituem a prova do fluxo que está sendo alegado.

## Licença

O código publicado neste repositório é disponibilizado sob a [Common Public Attribution License 1.0](LICENSE), observados os direitos de terceiros sobre datasets, dependências, imagens e outros materiais quando aplicável.

**Atribuição:** Flynn, por Nomos Ludens — https://github.com/NomosLudens/flynn
