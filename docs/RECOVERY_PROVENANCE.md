# Flynn — proveniência da retomada

## Checkout

- Diretório: /home/tonyus-dev/Documents/ChatGPT/FLYNN
- Estado encontrado: branch master sem commits e sem remoto.
- Arquivos locais preservados: código da Caverna/Lethe, artefatos do closed
  loop, traços JSON e superfície web.
- Resíduos excluídos do pacote: bytecode Python, bancos SQLite e estado de
  execução.

## Recuperação dos registros

O Git local ainda continha árvores órfãs, embora não houvesse commits:

- tree 8359c852a9d88fe10b45fa9f870834586990fb7b: snapshot amplo do código e
  dos artefatos de validação;
- tree 293b7dd06bc1bde071fcdfc643b14f3d2ffbaa3d: runner e URDF do E01;
- tree 68365af490e3d8b804c16084f7f8049bba789526: análise auxiliar R01.

O runner e o URDF do E01 foram recuperados dessa árvore e reescritos no kit
parametrizado em research/e01/. A versão atual elimina caminhos fixos da VM,
mantém initialize e health na mesma conexão IPC e falha de forma explícita
quando o host ou Pinocchio não estão disponíveis.

## Registros operacionais usados

- Rollout E01: 01a0a259-efb3-73e0-a759-a5821e6ce2d4.
- Investigação Lethe/Caverna: 01a0aaa9-51a2-7201-b99d-c7978f0dc112.
- Protocolo E01: referência de 2026-09-14.
- Protocolo E01-R: reconciliação posterior, sem promoção para E02.

## Resultado da retomada

REPLICABLE_KIT=READY
PINOCCHIO_BODY=PASS
FAIL_CLOSED_CASES=PASS
REAL_ZEROCLAW_SESSION=BLOCKED_HOST_UNREACHABLE
RESIDENT_REPLICATION=BLOCKED
E01=PARTIAL
E01_R=UNRESOLVED
E02=NOT_READY

Nenhum resultado histórico de MAX foi convertido em prova atual. A retomada
da residente exige recuperar o host, volume ou backup original e repetir a
prova de processo, banco, SHA e fluxo manual.
