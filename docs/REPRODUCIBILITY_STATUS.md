# Estado de Reprodutibilidade

```text
REPRODUCIBILITY=UNVERIFIED
```

É possível compreender partes importantes do experimento a partir do código instalado arquivado, da documentação e dos manifests, mas não foi demonstrada uma reconstrução independente ponta a ponta. Esta declaração é intencional: um snapshot de código e hashes de dados não equivalem aos próprios dados, a dependências reproduzíveis ou a uma restauração validada.

## Materiais preservados no GitHub

- Snapshot verbatim de 31 arquivos Python instalados, com SHA-256 por arquivo e comparação contra o commit público de referência [`f69f6c0d`](../archive/runtime-installed/2026-10-26/README.md).
- Documentação de arquitetura, modelo neural, corpo, Homeostasis V2, episódios, resultados e incidentes.
- Manifesto `data.sha256` com 74 caminhos e hashes observados na VM. Ele é um inventário, não contém os bytes dos arquivos listados.
- Registros históricos de segmentos remotos de episódio 3; o catálogo documentado cobre até tick 3.786.800.

## Componentes e configuração conhecida

- Runtime Python 3.10 em `/home/tonyus-dev/flynn-v2-vm-validation-20261019/resident-app`.
- FlyWire FAFB v783: 139.255 root IDs; CSR runtime assinado com 15.091.983 pares direcionados e 54.492.922 sinapses; matriz SHA-256 `efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347`; mapa ordenado SHA-256 `b0c012e1e5abc6242e4f620e666216d2928c9821c1ad9cef0b61117a9d3c0240`.
- LIF experimental em float64; parâmetros e contratos estão em [`NEURAL_MODEL.md`](NEURAL_MODEL.md). Visual e propriocepção eram transdutores sintéticos.
- Ambiente LIF observado: NumPy 1.22.3; dependências declaradas em `requirements-neuro.txt` incluem PyArrow 11.0.0, mas a presença instalada de PyArrow não foi confirmada na captura final.
- Ambiente Pinocchio observado: `pin==4.1.0`, `cmeel==0.61.0`, NumPy 2.2.6; dependia do `LD_LIBRARY_PATH` configurado pela unidade para `libgomp`.
- PicoClaw v0.2.9 era invocado pela ponte de coordenação. A evidência residente mostra recibos; não prova atuação física efetiva.
- Body: modelo Pinocchio sintético planar XY/yaw; 22 links dinâmicos, oito arestas somente gráficas.
- Persistência: schema SQLite versão 1, arquivo em modo DELETE na inspeção; checkpoints NPZ contêm arrays LIF e snapshots de estado. Identidade deve incluir episódio, geração e referência/hash do checkpoint.

## Materiais preservados e pendências de reprodução

1. Episódio 3: banco SQLite, metadados e checkpoints 4.468.200/4.468.400 recuperados byte a byte da VM e publicados. `PRAGMA integrity_check=ok`; hashes de origem, cópia e GitHub coincidem.
2. Episódio 5: banco SQLite, metadados e checkpoints 87.600/87.800/88.000 recuperados e publicados. `PRAGMA integrity_check=ok`; hashes coincidem. A fronteira atômica confirmada é 87.800; tick 88.000 foi preservado como não confirmado.
3. Arrays CSR FAFB-v783 (`indptr.npy`, `indices.npy`, `signed_count.npy`, manifesto) copiados e publicados com hashes correspondentes e aviso de atribuição/licença CC BY-NC 4.0 conservador. As diretrizes oficiais FlyWire declaram CC BY-NC 4.0; o registro Zenodo v783 lista CC BY 4.0. A divergência está documentada e não se reivindica uso comercial.
4. O arquivo histórico GCS foi listado e copiado para a Release: 23 objetos (sete segmentos, sete manifestos, sete catálogos e um backup de checkpoint mais manifesto), 62.841.113 bytes. MD5 e tamanhos correspondem aos metadados de origem; oito payloads zstd passaram teste e os sete arquivos tar foram listados. Veja `GCS_HISTORICAL_ARCHIVE_MANIFEST.json`.
5. Ambientes Python completos, wheels/lockfile exato instalado, bibliotecas nativas e configuração integral da unidade systemd continuam incompletos.
6. A VM `flynn-1gb` foi consultada em 2026-10-26 pelo IAP SSH existente: instância `RUNNING`, `flynn-v2-resident.service` `failed`. Nenhum reinício foi realizado.

Os 37 payloads identificados e seus hashes constam em [`PRESERVATION_MANIFEST_FINAL.json`](https://github.com/NomosLudens/flynn/releases/download/v2.0-research-closed/PRESERVATION_MANIFEST_FINAL.json). A preservação dos arquivos não comprova reconstrução independente ponta a ponta nem o ciclo causal neuromotor; `REPRODUCIBILITY=UNVERIFIED`.

## Limites de hospedagem examinados

No Git regular, GitHub bloqueia arquivos maiores que 100 MiB. Git LFS no plano Free tem cota incluída de 10 GiB de armazenamento e 10 GiB de transferência por ciclo; ultrapassar cotas pode bloquear uploads ou gerar cobrança conforme configuração de billing. A instalação local não tem `git-lfs`, e a cota/consumo efetivos da conta não foram consultados. Logo LFS não foi usado e sua capacidade gratuita não foi presumida.

Assets de GitHub Releases aceitam até 1.000 arquivos por release e cada arquivo deve ser menor que 2 GiB; a documentação do GitHub informa que não há limite agregado de tamanho ou banda para assets. Isso torna Releases uma alternativa potencial para payloads já obtidos e analisados, mas não recupera arquivos a que não se tem acesso, nem resolve a revisão de licença/privacidade. O estado do repositório consultado via API era `size=2885` (KiB) antes desta publicação; isso não informa a cota de assets nem o tamanho dos dados que só estão na VM.

Referências oficiais consultadas em 26/10/2026: [limites de repositório](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits), [Git LFS e tamanhos por plano](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage), [cotas e billing Git LFS](https://docs.github.com/en/billing/concepts/product-billing/git-lfs), [limites de assets de Release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Evidência mínima ainda necessária para reprodução

Uma reprodução futura exigiria os bytes e hashes de todos os dados de entrada, um ambiente e configuração instalados vinculados a revisões conhecidas, compatibilidade de dependências/native libs, identidade de episódio/generation, checkpoint e sequência de comandos. A aceitação experimental ainda exigiria uma execução única e instrumentada que demonstrasse a cadeia causal completa. Esse trabalho não foi iniciado e não faz parte do projeto encerrado.
