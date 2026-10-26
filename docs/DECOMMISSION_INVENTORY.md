# Inventário de Descomissionamento — Não Executado

**Estado:** `DECOMMISSION_INVENTORY=PARTIAL` · `DELETION_EXECUTED=NO`  
Este documento não é autorização de exclusão. A preservação dos dados essenciais continua parcial.

| Recurso | Identificação preservada | Estado nesta missão | Evidência / impedimento |
|---|---|---|---|
| VM | Nome `flynn-1gb`; projeto `kaline-totalidade` | Instância numérica e estado atual não confirmados | A documentação histórica coloca-a em `us-central1-f`; um resumo posterior registra `us-central1-a`. A divergência não foi resolvida. `gcloud` ausente localmente; SSH ao alias não resolveu. |
| Discos | Disco documentado historicamente como 10 GiB | Nome, ID, tipo, snapshots e associação atual não confirmados | Requer listar instância e discos com identidade GCP autorizada. |
| IP | Documentos históricos divergem entre um IPv4 externo observado anteriormente e configuração posterior somente interna/IAP | Estado atual não confirmado | `compute.addresses.list` estava negada em tentativa anterior. |
| Firewall / rede | Histórico cita rede `flynn-1gb-net` e regra de SSH/IAP dedicada | Dependências e compartilhamento atuais não confirmados | Não tratar prefixo de nome como prova de exclusividade. |
| Cloud Storage | Arquivo histórico em bucket `kaline-totalidade-backup-1079084506908`, prefixo `FLYNN/HISTORICO` | Segmentos de catálogo existentes até tick 3.786.800; upload/readback dos dados locais restantes não feito | Nenhuma permissão de escrita ou capacidade atual foi revalidada nesta missão. |
| Serviços | `flynn-v2-resident.service`, viewer LETHE e timer de arquivo aparecem no host | Estado atual não confirmado; último registro do arquivo: residente failed/start-limit, viewer inativo, timer configurado | Inspeção por SSH não disponível nesta sessão. Nenhum stop, start ou restart foi enviado. |
| GitHub | `NomosLudens/flynn` | Público e acessível | Não é alvo de descomissionamento; a missão proíbe removê-lo. |

## Permissões necessárias para completar o inventário

Histórico da missão anterior registrou `compute.instances.get`, `compute.instances.list`, `compute.disks.list` e `compute.addresses.list` como negadas. A retomada atual também não tem `gcloud` instalado e `ssh flynn-1gb` falha por resolução de nome. É necessário restabelecer o canal autorizado já existente e conceder à identidade já usada apenas as permissões de leitura necessárias, ou fornecer inventário exportado pelo operador. Não criar credenciais, não ampliar escopo automaticamente e não usar IP antigo como desvio ao IAP.

## Gate antes de qualquer exclusão

Os bancos e checkpoints locais do episódio 3 após tick 3.786.800, os dados do episódio 5 e os arrays locais do conectoma não estão preservados externamente de forma comprovada. A VM e discos devem permanecer intactos até que esses dados sejam copiados para destino aprovado, os hashes de origem/destino confiram e uma leitura de retorno confirme recuperação. Esta missão não executa nem autoriza a exclusão.
