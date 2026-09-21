# Flynn — recuperação do cache iOS — 2026-09-21

Este diretório preserva os 12 screenshots feitos no iPhone em 21/09/2026, aproximadamente entre 17:15 e 17:37 (BRT), quando a interface LETHE/Flynn ainda apareceu navegável no cliente mesmo sem confirmação de disponibilidade do origin/backend.

## Natureza da evidência

- Os arquivos `.webp` deste diretório são **derivados de preservação otimizados** dos screenshots enviados no chat, produzidos apenas para arquivamento via conector GitHub.
- Eles **não são byte a byte idênticos** aos JPEG originais.
- Os JPEG originais permanecem preservados no iPhone/chat; seus SHA-256 estão registrados abaixo para proveniência.
- A presença de dados no cliente é compatível com cache/PWA/service worker e/ou armazenamento local. **Não constitui, sozinha, prova de que o backend estava vivo.**

## Conteúdo visível recuperado

Entre os elementos registrados nas telas estão:

- LETHE / `FLYNN · LIVE`, estado `QUIESCENTE · SEM ESTÍMULO`;
- `CORPO VIVO · CAVERNA`, movimento ativo, energia 0%, necessidade alimentar 100% alta;
- doce disponível a aproximadamente `d=3.091 u`;
- Replay Científico `Looming (DNp01 Escape Takeoff)`;
- telemetria `VIRTUAL / ZEROCLAW (DETERMINISTIC)`, Experience Store online, ensaio de 400 ms, seed 0;
- Experiment Ledger com sessão `sess_default`, causal chain `CC-20260916-3d7d49` e status `ACTIVE (WAL APPEND-ONLY)`;
- seis saídas descendentes canônicas;
- gramática de interação humana e variáveis SWEET/BITTER/WIND/SOUND/LOOMING/CONTACT;
- Umwelt com posição `[-0.087, 0.148]`, 172 DNs ativos, sweet em `[3.000, 0.000]`, contato NO;
- diário causal com eventos `RESIDENT BRAIN` e `HUMAN OPERATOR` de 15–16/09/2026;
- detalhes técnicos com `q[23]`, `qdot[23]`, resource `sweet`, trajetória `f4e44cda-5dc3-4174-aad2-bbf42e064c01`, `caverna=73` e proveniência `lethe_sigil_fafb_v783`.

## Ordem dos screenshots

1. `flynn-ios-cache-17-15-23.webp`
2. `flynn-ios-cache-17-31-14.webp`
3. `flynn-ios-cache-17-31-18.webp`
4. `flynn-ios-cache-17-32-58.webp`
5. `flynn-ios-cache-17-33-25.webp`
6. `flynn-ios-cache-17-33-37.webp`
7. `flynn-ios-cache-17-34-05.webp`
8. `flynn-ios-cache-17-34-22.webp`
9. `flynn-ios-cache-17-36-56.webp`
10. `flynn-ios-cache-17-37-07.webp`
11. `flynn-ios-cache-17-37-19.webp`
12. `flynn-ios-cache-17-37-33.webp`

## SHA-256 dos JPEG originais

| Horário | SHA-256 |
|---|---|
| 17:15:23 | `00e2747293775a90b96a61ed8f5697b9521c05a420904a3cd93df2a1a6035e06` |
| 17:31:14 | `9bc188f014a7f15bc0968c619a9506d62b889d96e4873b39042e9ca118f00daf` |
| 17:31:18 | `92edc02445a912c95213144fb07c850419d882b626716df70503af3d3f33a9d1` |
| 17:32:58 | `da4e4e1c74ba292700f4fb0ce0f53718d1711d5d87d58dc82571355879594dc7` |
| 17:33:25 | `9d783b8abe4f37354c8a5d2fc576e969f8fd090b941c9589f5a5ae253d8e05fd` |
| 17:33:37 | `b917f12fd99620feca3110cd66718fecd9eb5e4d0d9ad50c312220b092af3bc5` |
| 17:34:05 | `cfbb8bbe083ddfab8f5a0c5c2ec34109cfd3e1a850917181da5f97527642c5cb` |
| 17:34:22 | `2bde8d6860672a45c0ecf5df8c6c7fc13503185df43117bc3b0752fd671602fc` |
| 17:36:56 | `d438e96c00455101a8847a4915197290e1ca95a3b917a3955fad028efeafc9cb` |
| 17:37:07 | `afe0fb04412ce5c08db7fcff51fcfd6f7317c6a06c66527aa660226e609cb228` |
| 17:37:19 | `1cd63d8e704098fa1db6aee90d0ce548a1eedff5bead71f74bd8471c432616d3` |
| 17:37:33 | `d69cf2246faa4ded936247f41592dbd8bb7df3cfe4202b0f211e0753346ad262` |

## Próximo alvo de recuperação

O material visual já preserva uma fração importante do estado observado. O próximo passo técnico, sem apagar dados do iPhone, é tentar extrair Cache Storage/service worker, Local Storage e IndexedDB para recuperar dados estruturados além das telas.
