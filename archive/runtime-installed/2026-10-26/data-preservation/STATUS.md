# Estado da preservação dos dados científicos

**Resultado:** `DATA_PRESERVATION=COMPLETE_FOR_IDENTIFIED_PAYLOADS` · `GITHUB_RELEASE=VERIFIED` · `EPISODE_5_TICK_88000=UNCONFIRMED`

## Payloads recuperados e publicados

A VM `flynn-1gb` foi consultada pela rota SSH/IAP já configurada, usando a autorização `sudo` existente para leitura. O serviço `flynn-v2-resident.service` estava em `failed`; nenhum serviço foi iniciado/reiniciado e os arquivos originais não foram alterados.

| Conjunto | Identidade | Preservação e verificação |
|---|---|---|
| Episódio 3 | `resident-v2:flynn-1gb:successor-0474efa32ea5408a87f89b567c5dab7b`; geração `generation-be731e6d86374508818c4f8f685850c3`; tick limpo 4.468.400 | SQLite, metadados e checkpoints 4.468.200/4.468.400 publicados. Hashes origem/cópia/Release coincidem; `PRAGMA integrity_check=ok`. |
| Episódio 5 | `resident-v2:flynn-1gb:19bc839e52474f3f9a3ec12eefaf1647`; geração `ffc7f14f56c149268e695faaf40a0451`; fronteira atômica ativa 87.800 | SQLite, metadados e checkpoints 87.600/87.800/88.000 publicados. Hashes coincidem; `PRAGMA integrity_check=ok`. Tick 88.000 é preservado, mas continua não confirmado. |
| Arrays CSR FAFB-v783 | Matriz runtime `efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347` | `indptr.npy`, `indices.npy`, `signed_count.npy` e manifesto de origem publicados com hash de origem/cópia/Release coincidente. Atribuição/licença anexadas. |

Os 13 payloads recuperados e respectivos metadados de identidade constam em `PRESERVATION_MANIFEST_v2.json`. Todos os digests SHA-256 da API pública do GitHub coincidem com os arquivos locais. O manifesto e os arquivos estão na [Release `v2.0-research-closed`](https://github.com/NomosLudens/flynn/releases/tag/v2.0-research-closed).

## Licença e atribuição do conectoma

As diretrizes oficiais do FlyWire declaram CC BY-NC 4.0 para dados da liberação pública. O registro Zenodo v783 informa CC BY 4.0. Como há divergência, a Release aplica a condição mais restritiva, CC BY-NC 4.0, com atribuição ao FlyWire Consortium e às publicações de origem. A divergência continua explícita no aviso de licença; não é concedida permissão de uso comercial.

## Arquivo histórico anterior

O arquivador usa `gs://kaline-totalidade-backup-1079084506908/FLYNN/HISTORICO`. Evidência de sessão anterior registra segmentos do episódio 3 até tick 3.786.800. O objeto `000002153401-000003414000.tar.zst` foi então lido com hash SHA-256 `e2910d8cab0b5c7b5d48e6a8a9389454f2af2a85b746c20c2df07e5e3586afb9`. Esta sessão não pôde listar o bucket porque a identidade atual da VM não tem `storage.objects.list`. A cópia completa do banco do episódio 3 publicada aqui chega ao tick limpo 4.468.400.

A preservação acima cobre os payloads identificados na missão. A reprodução independente ponta a ponta continua `UNVERIFIED`; preservação de dados não demonstra a integração neuromotora.
