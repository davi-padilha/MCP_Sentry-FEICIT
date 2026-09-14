# Congelamento candidato M23-B1

## Propósito

Esta é a fonte congelada candidata dos 90 casos que alimentará as baterias
finais. Deriva exclusivamente de I1/v6, sem modificar seus insumos. Contém 150
superfícies: C1=60, C2=60 e D=30. Nenhum portão de execução está aberto.

## Ordem de leitura

1. `manifesto_90_casos_v2_i1.json` — composição, proveniência e hashes de cada
   caso e superfície;
2. `manifestos/sha256.tsv` — ledger de integridade desta raiz;
3. `README.md` — esta fronteira humana.

## Fronteira

E2/E3 permanecem adiados condicionalmente pela decisão preservada em `27b2d89`.
Esta raiz não contém runner, credencial, preflight, resultado ou autorização de
modelo; eles não podem ser inferidos a partir dela.
