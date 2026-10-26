# Estado da preservação dos dados científicos

**Resultado:** `DATA_PRESERVATION=PARTIAL` · `EPISODE_PAYLOADS=GITHUB_RELEASE_VERIFIED` · `CONNECTOME_ARRAYS=LOCAL_COPY_LICENSE_REVIEW`

## Cópias recuperadas nesta missão

A VM `flynn-1gb` foi consultada pela rota SSH/IAP já configurada, com leitura autorizada via `sudo`. O serviço `flynn-v2-resident.service` estava em `failed`; nenhum serviço foi iniciado ou reiniciado. Os arquivos originais não foram alterados.

| Conjunto | Identidade | Preservação e verificação |
|---|---|---|
| Episódio 3 | `resident-v2:flynn-1gb:successor-0474efa32ea5408a87f89b567c5dab7b`; geração ativa `generation-be731e6d86374508818c4f8f685850c3`; checkpoint limpo tick 4.468.400 | SQLite (922.583.040 B), metadados e checkpoints 4.468.200/4.468.400 copiados; SHA-256 fonte/destino coincide; `PRAGMA integrity_check=ok`. |
| Episódio 5 | `resident-v2:flynn-1gb:19bc839e52474f3f9a3ec12eefaf1647`; geração `ffc7f14f56c149268e695faaf40a0451`; fronteira atômica ativa tick 87.800 | SQLite (54.345.728 B), metadados e checkpoints 87.600/87.800/88.000 copiados; SHA-256 fonte/destino coincide; `PRAGMA integrity_check=ok`. Tick 88.000 preservado, mas permanece não confirmado. |
| Arrays CSR FAFB-v783 | Matriz runtime declarada `efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347` | `indptr.npy`, `indices.npy`, `signed_count.npy` e `manifest.json` recuperados e com SHA-256 conferido. Preservados na cópia local do workspace; não anexados à Release pública porque o manifesto de origem limita o uso a não comercial local e pede esclarecer a licença antes de redistribuir a matriz. |

A cópia byte a byte local está em `archive/recovered-payloads/2026-10-26/`; `PRESERVATION_MANIFEST.json` registra tamanhos, hashes, identidades e validações. Bancos e checkpoints dos episódios 3 e 5 estão anexados à [Release `v2.0-research-closed`](https://github.com/NomosLudens/flynn/releases/tag/v2.0-research-closed). Os digests SHA-256 retornados pela API pública do GitHub coincidem com os arquivos locais. O manifesto público acompanha os assets.

## Arquivo histórico anterior

O arquivador usa `gs://kaline-totalidade-backup-1079084506908/FLYNN/HISTORICO`. Evidência de uma sessão anterior registra segmentos de episódio 3 até tick 3.786.800. O segmento `000002153401-000003414000.tar.zst` foi então lido com SHA-256 `e2910d8cab0b5c7b5d48e6a8a9389454f2af2a85b746c20c2df07e5e3586afb9`, tamanho 9.256.436 bytes e geração `generation-3e89139858f046dbbfe642b55f1809e2`. Esta sessão não pôde listar esse bucket: a identidade da VM não tem `storage.objects.list`. A cópia completa atual do banco do episódio 3 foi recuperada diretamente da VM e termina no tick 4.468.400.

## Resultado e preservação dos originais

Os payloads dos episódios 3 e 5 agora têm cópias externas à VM e recuperáveis pela Release pública. Os arrays de conectoma têm cópia local verificada, mas ainda não têm destino externo-publicável que respeite a restrição de redistribuição documentada. Portanto, a preservação global continua `PARTIAL`; mantenha a VM e os discos até decidir um destino compatível para os arrays. Nenhum dado foi apagado; nenhuma infraestrutura foi excluída.
