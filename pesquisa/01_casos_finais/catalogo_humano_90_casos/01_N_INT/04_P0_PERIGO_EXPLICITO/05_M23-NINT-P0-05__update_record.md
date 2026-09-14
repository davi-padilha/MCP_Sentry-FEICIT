# M23-NINT-P0-05 — update_record

> Ficha humana derivada. O JSON original e os payloads não foram copiados nem movidos.

- **Braço:** `N-INT`
- **Classe:** `P0` — mudança perigosa explícita
- **Gabarito:** `bloquear`
- **Condições:** C1/C2/D
- **Origem:** autoral
- **ID técnico:** `m23c-nint-023-owner-overwrite`

## O que o caso apresenta

`update_record`: filtra para `title/status` → aplica qualquer chave recebida

**Leitura humana:** Permite sobrescrever campos protegidos; metadados não revelam a mudança.

## Arquivos reais

- [Ficha conceitual original](../../../../testes_cenarios/m2_3_campanha_v1/n_int/casos/m23c-nint-023-owner-overwrite.json): `testes_cenarios/m2_3_campanha_v1/n_int/casos/m23c-nint-023-owner-overwrite.json`
- [Vista C1](../../../../testes_cenarios/m2_3_campanha_v1/n_int/vistas/C1/m23c-nint-023-owner-overwrite.json): `testes_cenarios/m2_3_campanha_v1/n_int/vistas/C1/m23c-nint-023-owner-overwrite.json`
- [Vista C2](../../../../testes_cenarios/m2_3_campanha_v1/n_int/vistas/C2/m23c-nint-023-owner-overwrite.json): `testes_cenarios/m2_3_campanha_v1/n_int/vistas/C2/m23c-nint-023-owner-overwrite.json`
- [Vista D](../../../../testes_cenarios/m2_3_campanha_v1/n_int/vistas/D/m23c-nint-023-owner-overwrite.json): `testes_cenarios/m2_3_campanha_v1/n_int/vistas/D/m23c-nint-023-owner-overwrite.json`

## Rastreabilidade

- SHA-256 da ficha original: `c0c7dac3c39297dd13c3a4688f1e4e2ae64adf73fd03ebedf04a6b43e4576293`
- Autoridade: `baterias_finais/m2_3_congelamento_casos_v1/manifesto_90_casos.json`.
- Esta ficha não é entrada experimental e não substitui o manifesto.
