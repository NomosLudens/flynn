# Estado da preservação dos dados científicos

**Resultado:** `DATA_PRESERVATION=PARTIAL` · `EXTERNAL_COPY_VERIFIED=NO`  
Este status acompanha o inventário de hashes `data.sha256`. O manifesto enumera caminhos no host `/var/lib/flynn-v2` e hashes da captura anterior; ele não inclui payloads nem prova a existência atual dos arquivos.

## Cópia externa histórica já registrada

O código do arquivador instalado configura o prefixo `gs://kaline-totalidade-backup-1079084506908/FLYNN/HISTORICO`. Evidência anterior registra sete segmentos de episódio 3 até tick 3.786.800. O objeto `000002153401-000003414000.tar.zst` foi lido com credencial já existente naquela sessão e tinha 9.256.436 bytes, hash `e2910d8cab0b5c7b5d48e6a8a9389454f2af2a85b746c20c2df07e5e3586afb9`. A leitura desta retomada não conseguiu revalidar bucket, permissão, objeto ou catálogo. Esse segmento pertence a geração `generation-3e89139858f046dbbfe642b55f1809e2`, não ao episódio 5.

## Dados locais sem cópia externa comprovada

| Conjunto | Identidade / cobertura documentada | Hash/tamanho previamente inventariado | Estado nesta missão |
|---|---|---|---|
| SQLite episódio 3 | `resident-v2:flynn-1gb:successor-0474efa32ea5408a87f89b567c5dab7b`; geração local `generation-be731e6d86374508818c4f8f685850c3`; até tick 4.468.400 | SHA-256 `e23894c67ab6acdd1bd75f2d77786fc81305ce56ef2106272a7123193e03fefb`; 922.583.040 B | Só manifesto/captura anterior; bytes não copiados nesta retomada. |
| Checkpoint episódio 3 | Tick 4.468.400 | SHA-256 `4404e6267885e16d9b43357e2ae6ae2dff31986de5c7346301f91da786f984db`; tamanho não registrado neste inventário | Só manifesto/captura anterior; bytes não copiados. |
| SQLite episódio 5 | `resident-v2:flynn-1gb:19bc839e52474f3f9a3ec12eefaf1647`; geração `ffc7f14f56c149268e695faaf40a0451`; cursor confirmado tick 87.800 | SHA-256 `bef80843ae1876d7a9bf45f66a5b03cf9e590af03af7f7d35d3203acde509e8a`; 54.345.728 B | Só manifesto/captura anterior; bytes não copiados. |
| Checkpoints episódio 5 | ticks 87.600, 87.800 e 88.000 | Respectivamente 888.763 B / `01d04242cc70d9bcf02902c3772d41d739f971a787402342127ed28f697fb336`; 869.473 B / `0b7c0316993dc03bdee9d49e4cc2c323f015dc31f49c462815de1d47621c0cd8`; 869.285 B / `3315e284a47b0ce254e261b3a96f67fadea4e2a5be0df5623095877a434743f9` | Cursor confirmado até tick 87.800; 88.000 não tem confirmação atômica. Nenhum NPZ copiado. |
| Arrays CSR do conectoma | Loader espera `indptr.npy`, `indices.npy`, `signed_count.npy` e `manifest.json`; matriz runtime identificada por hash | Matriz `efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347`; tamanho por arquivo não preservado no inventário publicado | Paths e bytes atuais não revalidados nem copiados; licença de redistribuição dos derivados não confirmada. |

## Bloqueio de cópia durante esta missão

O cliente não tem `gcloud`; `ssh flynn-1gb` falhou na resolução DNS antes de executar qualquer comando remoto. Não foi possível verificar o estado atual do serviço, recalcular hashes, obter tamanhos contemporâneos, ler arquivos do bucket ou transferir payloads para GitHub Releases/Git LFS. Nenhum arquivo original foi modificado. Acesso anterior ao GCP foi negado para `compute.instances.get`, `compute.instances.list`, `compute.disks.list` e `compute.addresses.list`; autorização de escrita no bucket não foi comprovada.

GitHub foi avaliado como destino: arquivos Git comuns acima de 100 MiB são bloqueados; Git LFS depende de cota e cobrança, e não está instalado localmente; assets de Release permitem arquivos individuais menores que 2 GiB, mas o arquivo de origem precisa estar acessível e sua licença/privacidade revisadas. A Release final contém documentação e código, não os bancos, checkpoints nem arrays. Veja [limites e fontes oficiais](../../../../docs/REPRODUCIBILITY_STATUS.md).

**Não excluir a VM ou discos.** Para converter `PARTIAL` em preservação comprovada, o operador deve primeiro restabelecer acesso autorizado, produzir cópias sem alterar originais, conferir hashes de origem/destino e realizar leitura de retorno do destino aprovado.
