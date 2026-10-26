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

## Materiais ainda ausentes ou não recuperáveis nesta sessão

1. Banco SQLite e checkpoints atuais completos do episódio 5 (cursor confirmado em tick 87.800 e cauda parcial em 88.000).
2. Banco/checkpoint local do episódio 3 após o último segmento de catálogo em tick 3.786.800 (a base local foi observada até tick 4.468.400).
3. Arrays locais do conectoma e mapas de população completos. O loader arquivado espera `indptr.npy`, `indices.npy`, `signed_count.npy` e `manifest.json`; a árvore do loader foi instalada em pacote datado, mas a presença, caminho resolvido, tamanhos e bytes desses arquivos não foram confirmados nesta sessão. Um manifesto de população conhecido em workstation local fora do checkout não substitui os arrays do host.
4. Ambientes Python completos, wheels/lockfile exato instalado, bibliotecas nativas, binário e configuração integral da unidade systemd.
5. Metadados Git do runtime instalado e commit de origem: não encontrados na árvore capturada.
6. Estado atual da VM: sem verificação; `gcloud` ausente no cliente e `ssh flynn-1gb` sem resolução DNS nesta sessão.

Os itens 1–3 continuam somente identificados por manifestos/hashes anteriores e não foram copiados externamente nesta missão. Nenhum dado foi removido. O acesso à VM, ao armazenamento remoto existente e a uma cópia byte a byte com leitura de retorno é necessário antes de mudar `DATA_PRESERVATION=PARTIAL`.

## Licenças e redistribuição

O repositório existente declara CPAL 1.0 para seu código. Os dados FlyWire são associados a CC BY-NC 4.0 conforme documentação histórica, e arquivos derivados Shiu/anotações possuem termos específicos que não foram confirmados para redistribuição de payload nesta missão. Pinocchio e demais dependências conservam licenças próprias. Não publicar arrays, SQLite ou checkpoints em repositório público sem confirmar licença, confidencialidade e adequação do conjunto.

## Limites de hospedagem examinados

No Git regular, GitHub bloqueia arquivos maiores que 100 MiB. Git LFS no plano Free tem cota incluída de 10 GiB de armazenamento e 10 GiB de transferência por ciclo; ultrapassar cotas pode bloquear uploads ou gerar cobrança conforme configuração de billing. A instalação local não tem `git-lfs`, e a cota/consumo efetivos da conta não foram consultados. Logo LFS não foi usado e sua capacidade gratuita não foi presumida.

Assets de GitHub Releases aceitam até 1.000 arquivos por release e cada arquivo deve ser menor que 2 GiB; a documentação do GitHub informa que não há limite agregado de tamanho ou banda para assets. Isso torna Releases uma alternativa potencial para payloads já obtidos e analisados, mas não recupera arquivos a que não se tem acesso, nem resolve a revisão de licença/privacidade. O estado do repositório consultado via API era `size=2885` (KiB) antes desta publicação; isso não informa a cota de assets nem o tamanho dos dados que só estão na VM.

Referências oficiais consultadas em 26/10/2026: [limites de repositório](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits), [Git LFS e tamanhos por plano](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage), [cotas e billing Git LFS](https://docs.github.com/en/billing/concepts/product-billing/git-lfs), [limites de assets de Release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Evidência mínima ainda necessária para reprodução

Uma reprodução futura exigiria os bytes e hashes de todos os dados de entrada, um ambiente e configuração instalados vinculados a revisões conhecidas, compatibilidade de dependências/native libs, identidade de episódio/generation, checkpoint e sequência de comandos. A aceitação experimental ainda exigiria uma execução única e instrumentada que demonstrasse a cadeia causal completa. Esse trabalho não foi iniciado e não faz parte do projeto encerrado.
