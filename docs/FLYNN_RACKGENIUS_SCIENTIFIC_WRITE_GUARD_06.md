# FLYNN RackGenius — Scientific Write Guard 06

**Data:** 2026-11-04
**Alvo:** `flynn-rg01` — `198.134.20.21`
**Snapshot-base preservado:** `storage-guard-04-20261103`
**Snapshot ensaiado:** `/home/flynnadmin/flynn/releases/storage-guard-06-20261104`

```text
MISSION=FLYNN_RACKGENIUS_SCIENTIFIC_WRITE_GUARD_06
VERDICT=PASS

CHECKPOINT_WRITE_GUARDED=YES
SQLITE_WRITE_GUARDED=YES
LEDGER_WRITE_GUARDED=YES (event/state/cause ledger in the integrated v2 SQLite store)
CRITICAL_WRITES_AUDITED=YES (integrated v2 persistence paths)

REAL_CHECKPOINT_TEST=PASS; CSR v783, 139255 mapped roots, real LIF and world, 200 ticks
REAL_SQLITE_TEST=PASS; real episode-v2.sqlite3; allowed write and pressure refusal
DISK_PRESSURE_REJECTION=PASS; logical injection, no physical disk fill
PREVIOUS_CHECKPOINT_PRESERVED=YES; SHA-256 unchanged after refused checkpoint
SQLITE_INTEGRITY=PASS; integrity_check=ok; refused event left logical SQL dump and row counts unchanged
REAL_RESTORE=PASS; neural time, arrays and world restored exactly at tick 200

CHECKPOINT_BYTES=25076224
TEMPORARY_PEAK_BYTES=25076224
AVAILABLE_DISK_AFTER=22755655680

SCIENTIFIC_DATA_DELETED=NO
CANONICAL_EPISODE_STARTED=NO
CONTINUOUS_RESIDENCY=NOT_STARTED
OFFSITE_STORAGE=BLOCKED

NEXT_ACTION=Keep snapshot 06 staged; do not enable continuous residency until its separate scientific gate.
```

## Alterações

O snapshot 06 reutiliza o orçamento existente em uma guarda compartilhada. `_disk_budget()` e o cálculo de reserva vivem em `app/neuro_synthetic/storage_guard.py`; a guarda mantém o piso de 6 GiB, o alerta de 8 GiB, a reserva mínima provisória de 1 GiB para o próximo checkpoint, reserva de rotação de logs e espaço de rollback/capacidade restante. Um `flock` em `/tmp/.flynn-storage-write-guard.lock`, junto ao lock de processo, serializa escritores Flynn cooperantes desde a medição até o fim da gravação.

Foram protegidos os caminhos V2 de checkpoint integrado e checkpoint LIF, inicialização e transações SQLite, mapeamento CSR, eventos/estados/gerações causais, cursor/ledger, marcador atômico de parada e publicação de checkpoints de recuperação. O checkpoint integrado confirma o estado no SQLite somente depois da publicação atômica do NPZ. A recusa de espaço acontece antes da criação do temporário. Se o ledger SQLite também estiver sem margem, o motivo ainda fica recuperável no `episode.json`, baseado no último tick confirmado.

Os módulos antigos `app/brain/snapshot.py` e `app/brain/clock.py` contêm persistência própria e não fazem parte do pacote V2 instalado nem do caminho integrado ensaiado. A conclusão de cobertura se limita aos caminhos V2 de `storage-guard-06`; o código legado não foi alterado nem declarado protegido.

## Evidência do ensaio integrado

O ensaio foi isolado em `/home/flynnadmin/scientific-write-guard-06-retest-20261104`. Usou o CSR real v783 (`manifest SHA-256 499c77e789f2abeac9d21739ae106054381ad7758ab68caee9e0834dc0580045`), inicializou o LIF e o mundo reais e avançou 200 ticks até 20 ms. Nenhum estímulo ou dado científico fictício foi introduzido. O SQLite real registrou o mapeamento de 139.255 neurônios, estados e metadados do checkpoint.

Com espaço real, o checkpoint foi publicado e mediu 25.076.224 bytes; o pico do temporário também foi 25.076.224 bytes. Depois, a condição de disco foi injetada por substituição lógica de `disk_usage`, sem preencher a VPS. A tentativa de checkpoint foi recusada quando a margem simulada ficou um byte abaixo da reserva exigida: o SHA-256 do checkpoint anterior foi preservado e não houve temporário parcial. Uma escrita de evento SQLite real também foi recusada antes da transação. O digest do dump SQL, as contagens de tabelas e `PRAGMA integrity_check` permaneceram iguais (`ok`).

O marcador recuperável registrou `SAFE_STORAGE_LIMIT`, operação recusada, último tick confirmado 200, espaço simulado de 8.687.521.792 bytes e requisito de 8.687.521.793 bytes. A reabertura restaurou os arrays neurais e o estado do mundo exatamente. O teste separado de concorrência confirmou que um segundo processo não obtém o lock enquanto o escritor o mantém. Não foram encontrados arquivos `.tmp`/`.partial` abandonados. O espaço disponível variou de 22.811.312.128 para 22.755.655.680 bytes; a queda observada é compatível com o armazenamento do banco/mapeamento/checkpoint do próprio ensaio e não com preenchimento artificial.

Uma primeira checagem auxiliar comparou o hash físico do arquivo SQLite ao longo da sequência completa e retornou diferença. Como esse hash inclui representação física SQLite/WAL e não identifica sozinho uma mudança lógica, foi feita uma recusa controlada separada: nela, o digest do dump SQL e as contagens ficaram idênticos antes/depois. O teste final de integridade lógica passou; o primeiro hash bruto fica registrado como observação, não como evidência de mutação científica.

## Limites e preservação

- O lock serializa processos Flynn que usam esta guarda; processos externos ao runtime podem consumir o mesmo filesystem. O orçamento é reavaliado imediatamente antes de cada gravação crítica.
- O checkpoint de 25.076.224 bytes mede este estado instrumental. Checkpoints futuros podem ser maiores; por isso a reserva mínima de 1 GiB foi mantida e o tamanho já existente eleva a reserva do próximo checkpoint quando necessário.
- `storage-guard-04-20261103` permaneceu preservado. O serviço residente continua inativo; nenhum episódio canônico começou; nenhum dado histórico foi apagado; nenhuma publicação FlyWire ou GitHub foi feita.
- O ensaio não habilita residência contínua e não prova armazenamento externo.

## Identidade e checksums

Snapshot 06: SHA-256 dos módulos alterados na cópia implantada:

| Arquivo | SHA-256 |
|---|---|
| `storage_guard.py` | `680afc099ffddc1f813fed738fa49175a6a829928fd7f6b1431ad19f224f0ab8` |
| `sqlite_store.py` | `2a5f18702e433f1393433e73ae4c561e4b8ec3fd0581ba72486778ff245f090d` |
| `world_runtime.py` | `e2fb336be91b276ed3037552ae63172217a035563c567cafb97e40fb6627e932` |
| `neural_core.py` | `2636bac2177613dc1ddc4107ecad4fe70e8e03268eb9ced70257aed2d3166180` |
| `resident_runtime.py` | `5badd5984cfd0eeb634557b5c06f48b9ba4efd6afe7fd7e121ca11d30227d2b1` |
| `recovery_successor.py` | `5d441878c50c5a25e4b381796fb201aac82edc840bfab0bf54f76b2191248e70` |

`sha256sum -c SHA256SUMS` passou para o snapshot 06 e para os seis artefatos do CSR v783. A publicação preserva apenas código-fonte e relatório; bancos, checkpoints, arrays CSR e outros dados científicos da VM não foram enviados ao GitHub.
