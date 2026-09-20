# Flynn — estudo de organismo contínuo

Este repositório reúne o material recuperado localmente do estudo Flynn: a
cadeia mundo → transdução sensorial → cérebro LIF → leitura descendente →
corpo Pinocchio → mundo, além dos artefatos de validação da Caverna e do
closed loop. Ele também contém o kit reproduzível do experimento isolado E01,
que não depende da residente Flynn.

## Estado da recuperação

**PARTIAL / REPLICATION KIT READY** — o protocolo, o corpo sintético, o runner
e os contratos do E01 estão presentes e parametrizados. A VM que hospedava o
runtime residente está indisponível; portanto a replicação da residente,
SQLite, serviços e fluxo Lethe permanece `BLOCKED`, enquanto a execução do E01
fica pronta para ser repetida em um host autorizado com Pinocchio e ZeroClaw
reais.

As validações registradas em `closed_loop/` e `caverna_food_ui/` são
evidências históricas observadas no host `max`, datadas nos próprios
artefatos. Não devem ser lidas como uma execução nova deste checkout.

## Conteúdo

- `app/body/`: contrato de corpo, adaptador da Caverna e integração Pinocchio.
- `app/brain/`: relógio contínuo e snapshots do cérebro.
- `app/world/`: geometria e estado contínuo do mundo.
- `app/web/`: superfície web da Caverna/Lethe.
- `closed_loop/`: implementação e traço causal do loop encarnado.
- `caverna_food_ui/`: implementação e validação da interface de alimentação.
- `research/e01/`: runner isolado, URDF, dependências e artefatos gerados do
  experimento E01.
- `docs/`: runbook de replicação, índice de evidências e limites do E01-R.
- `docs/HISTORICO_DO_PERCURSO.md`: histórico cronológico completo da retomada.
- `docs/MAPA_DE_PERCURSO_FLYNN.md`: mapa operacional e conceitual fornecido
  pelo estudo, atualizado em 2026-09-15.
- `index.html`, `manifest.webmanifest`, `sw.js` e `icon.svg`: superfície
  web recuperada.

## Limites importantes

O runtime residente não é um pacote standalone: partes do runtime original (por
exemplo `app.ledger`, módulos de cérebro, STT/NLU e dados persistentes) não
estão presentes neste diretório, e os caminhos absolutos apontam para a antiga
instalação da VM. Não instale dependências, não recrie dados e não inicialize
um substituto residente sem uma decisão explícita de recuperação.

O kit E01 é a unidade replicável atual. Ele não altera o cérebro, a
plasticidade, o connectome, o corpo canônico ou o serviço ZeroClaw. A
coordenação do E01 continua classificada como adapter experimental externo;
portanto o veredito correto permanece `E01=PARTIAL`.

Para reproduzir o E01, siga [`docs/REPLICATION_RUNBOOK.md`](docs/REPLICATION_RUNBOOK.md).

Nenhum segredo, banco de dados, `__pycache__` ou estado de execução local deve
ser versionado. O `.gitignore` mantém esses itens fora do repositório.

## Proveniência

O material é um snapshot de pesquisa, não uma declaração de prontidão. Para
qualquer afirmação operacional, verificar separadamente host, processo,
checkout servido, banco de dados e fluxo manual real.
