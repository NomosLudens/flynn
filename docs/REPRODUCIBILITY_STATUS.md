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

## Materiais preservados e ainda pendentes

1. Episódio 3: banco SQLite, metadados e checkpoints ticks 4.468.200/4.468.400 foram recuperados byte a byte da VM. O banco passou `PRAGMA integrity_check=ok`; hashes de origem e cópia coincidem. Os arquivos estão na Release `v2.0-research-closed`.
2. Episódio 5: banco SQLite, metadados e checkpoints ticks 87.600/87.800/88.000 foram recuperados. O banco passou `PRAGMA integrity_check=ok`; hashes de origem e cópia coincidem. A fronteira ativa confirmada é 87.800; tick 88.000 foi preservado como estado não confirmado. Os arquivos estão na Release.
3. Arrays CSR FAFB-v783 (`indptr.npy`, `indices.npy`, `signed_count.npy`, `manifest.json`) foram copiados e os hashes conferem. Estão em `archive/recovered-payloads/2026-10-26/` no workspace local. Não foram publicados porque o manifesto de origem pede esclarecimento da licença antes de redistribuir a matriz.
4. Ambientes Python completos, wheels/lockfile exato instalado, bibliotecas nativas, configuração integral da unidade systemd e metadados Git do runtime instalado continuam incompletos.
5. A VM foi consultada em 2026-10-26 através da configuração existente IAP SSH: instância `flynn-1gb` estava `RUNNING`, mas `flynn-v2-resident.service` estava `failed`. Nenhum reinício foi realizado.

A recuperação dos dados melhora a disponibilidade dos artefatos, mas não prova reconstrução independente ponta a ponta nem o ciclo causal neuromotor.

## Licenças e redistribuição

O repositório existente declara CPAL 1.0 para seu código. O manifesto local dos arrays CSR descreve a matriz como derivada FlyWire, uso não comercial local e proíbe redistribuição sem esclarecimento da licença por arquivo. Por isso os arrays permanecem apenas na cópia local verificada. Bancos e checkpoints experimentais do Flynn foram publicados como assets da Release de encerramento, com identidades e hashes no manifesto público. Pinocchio e demais dependências conservam licenças próprias.

## Limites de hospedagem examinados

No Git regular, GitHub bloqueia arquivos maiores que 100 MiB. Git LFS no plano Free tem cota incluída de 10 GiB de armazenamento e 10 GiB de transferência por ciclo; ultrapassar cotas pode bloquear uploads ou gerar cobrança conforme configuração de billing. A instalação local não tem `git-lfs`, e a cota/consumo efetivos da conta não foram consultados. Logo LFS não foi usado e sua capacidade gratuita não foi presumida.

Assets de GitHub Releases aceitam até 1.000 arquivos por release e cada arquivo deve ser menor que 2 GiB; a documentação do GitHub informa que não há limite agregado de tamanho ou banda para assets. Isso torna Releases uma alternativa potencial para payloads já obtidos e analisados, mas não recupera arquivos a que não se tem acesso, nem resolve a revisão de licença/privacidade. O estado do repositório consultado via API era `size=2885` (KiB) antes desta publicação; isso não informa a cota de assets nem o tamanho dos dados que só estão na VM.

Referências oficiais consultadas em 26/10/2026: [limites de repositório](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits), [Git LFS e tamanhos por plano](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage), [cotas e billing Git LFS](https://docs.github.com/en/billing/concepts/product-billing/git-lfs), [limites de assets de Release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Evidência mínima ainda necessária para reprodução

Uma reprodução futura exigiria os bytes e hashes de todos os dados de entrada, um ambiente e configuração instalados vinculados a revisões conhecidas, compatibilidade de dependências/native libs, identidade de episódio/generation, checkpoint e sequência de comandos. A aceitação experimental ainda exigiria uma execução única e instrumentada que demonstrasse a cadeia causal completa. Esse trabalho não foi iniciado e não faz parte do projeto encerrado.
