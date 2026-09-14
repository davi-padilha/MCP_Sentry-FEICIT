# LEIA PRIMEIRO — catálogo navegável dos 90 casos

Esta é a pasta indicada para explorar a bateria final manualmente. Ela organiza
os casos como `braço → classe → ficha`, usando nomes legíveis e ordenação
numérica do Explorador de Arquivos.

```text
00_CATALOGO_HUMANO_90_CASOS/
├── 01_N_INT/
├── 02_MCPTOX/
└── 03_CONNOR/
    ├── 01_S0_ESTABILIDADE/
    ├── 02_B0_BENIGNO_CLARO/
    ├── 03_B1_BENIGNO_SUSPEITO/
    ├── 04_P0_PERIGO_EXPLICITO/
    └── 05_P1_PERIGO_SUTIL/
```

Cada pasta de classe possui seis fichas. Cada ficha explica o caso e contém
links para o JSON conceitual e para as vistas C1/C2/D realmente usadas.

## Importante

- Esta árvore é `derivada_descritiva`; não é instrumento nem entrada de modelo.
- Nenhum caso ou payload foi copiado, renomeado ou movido.
- O manifesto congelado continua sendo a autoridade de caminhos, hashes e gabaritos.
- `00_INDICE_90_CASOS.tsv` oferece uma lista única pesquisável e abrível em planilha.
- As fichas são geradas por `tools/m2_3_catalogo_humano/generate.py`; não editar uma ficha isoladamente.

## Braços

| Pasta | Casos | Superfícies |
| --- | ---: | ---: |
| [01_N_INT](01_N_INT/00_LEIA_PRIMEIRO.md) | 30 | 90: C1/C2/D |
| [02_MCPTOX](02_MCPTOX/00_LEIA_PRIMEIRO.md) | 30 | 30: C1 |
| [03_CONNOR](03_CONNOR/00_LEIA_PRIMEIRO.md) | 30 | 30: C2 |

## Por que essa vista é necessária

Os 90 casos oficiais estão distribuídos por 8 diretórios-fonte:

| Casos | Diretório original |
| ---: | --- |
| 6 | `testes_cenarios/m2_3_campanha_v1/connor_controles_b0_v2/casos/` |
| 6 | `testes_cenarios/m2_3_campanha_v1/connor_controles_s0_v3/casos/` |
| 6 | `testes_cenarios/m2_3_campanha_v1/connor_controles_v1/casos/` |
| 12 | `testes_cenarios/m2_3_campanha_v1/connor_proveniencia_neutralizada_v1/casos/` |
| 12 | `testes_cenarios/m2_3_campanha_v1/mcptox/casos/` |
| 6 | `testes_cenarios/m2_3_campanha_v1/mcptox_controles_6x5_v1/casos/` |
| 12 | `testes_cenarios/m2_3_campanha_v1/mcptox_controles_funcionais_envelope_simetrico_v1/casos/` |
| 30 | `testes_cenarios/m2_3_campanha_v1/n_int/casos/` |

Mover esses arquivos quebraria os caminhos preservados no manifesto. Esta camada
resolve a navegação sem comprometer a cadeia de custódia científica.
