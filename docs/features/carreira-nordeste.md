# Carreira: o Nordeste em detalhe

- **Data:** 2026-11-16
- **Status:** proposta
- **ADRs:** —
- **Projeto 2 de 5** (base → **Nordeste** → veredito das torcidas → capa da Geral → desafio).

## Objetivo

O diferencial da Geral: o ABC e o Náutico, nichados nos outros sites, aqui têm peso. A Carreira
ganha o Nordeste com profundidade: mais clubes, os **estaduais**, a **Copa do Nordeste**, os
**clássicos com nome**, **ídolos regionais** no draft e **eventos** que só acontecem lá. Quem
começa no ABC vive uma carreira diferente de quem começa no Flamengo.

## Fora de escopo

- Placar das torcidas e veredito por clube (projeto 3; os clássicos daqui servem de base ao
  "traidor").
- Série D completa do país; só os nordestinos que fazem sentido.

## Contratos

- **Clubes** (`mundo.toml`): `Clube.estado` (UF) em todo clube brasileiro. Entram América-RN,
  Treze, Campinense, Sampaio Corrêa, Ferroviário, River-PI, Altos, Sergipe, Juazeirense, ABC já
  está; nova liga `bra-d` (Série D, força ~32) para quem não está em A/B/C. Prestígios revistos
  para a região (Bahia > Fortaleza > Sport ≈ Ceará > Vitória > Náutico ≈ CRB > ABC ≈ Santa Cruz…).
- **Estaduais** (`mundo.toml`, `[[estado]] uf, campeonato, regiao`): todo clube brasileiro
  disputa o estadual do seu estado (Carioca, Paulistão, Potiguar, Pernambucano, Cearense,
  Alagoano, Baiano, Paraibano, Sergipano, Maranhense, Piauiense…). Chance do título: o peso do
  clube entre os do mesmo estado (prestígio²), vezes a participação dele na temporada.
- **Copa do Nordeste**: clubes nordestinos de A, B, C e D; chance pelo prestígio entre os da
  região. Aparece como taça (selo, card, título no final; `finais.toml` ganha o rótulo
  **"Rei do Nordeste"**: ≥ 2 Copas do Nordeste).
- **Clássicos** (`[[classico]] nome, clubes = [a, b]`): Clássico-Rei (ABC × América-RN),
  Clássico dos Clássicos (Náutico × Sport), Clássico das Multidões (Sport × Santa Cruz),
  Clássico-Rei (Ceará × Fortaleza), Clássico das Multidões alagoano (CSA × CRB), Ba-Vi
  (Bahia × Vitória), Clássico Tradição (Treze × Campinense)… e os grandes do Sul/Sudeste
  (Fla-Flu, Clássico dos Milhões, Derby, Gre-Nal…). Eventos ganham `{classico}` e `{rival}` e a
  condição `classico = true`.
- **Eventos regionais** (condição `regioes = ["nordeste"]`): viagem longa de ônibus, calor do
  meio-dia, Arena lotada no Nordestão, ídolo da terra recebe proposta do Sul, festa junina na
  concentração, torcida no aeroporto… ≥ 12 eventos e ≥ 4 situações de dia a dia.
- **Ídolos regionais** (`lendas.toml`, `regiao = "nordeste"`): Alberi, Marinho Chagas, Kuki,
  Bita, Kieza e mais de Sport, Santa Cruz, Bahia, Vitória, Ceará, Fortaleza, CSA e CRB
  (rascunho de Claude, **revisão do dev**; ids conferidos na base do jogo da velha). O draft de
  quem começa num clube nordestino traz **pelo menos 2** ídolos da região entre as 9 lendas
  (`oferta` passa a receber o clube de partida).

## Critérios de aceite (como testes)

- [ ] `test_todo_clube_brasileiro_tem_estado_e_estadual`.
- [ ] `test_estadual_favorece_o_grande_do_estado` (1.000 temporadas: ABC ganha o Potiguar mais
  que o Santa Cruz ganha o Pernambucano contra o Sport, proporcional ao prestígio).
- [ ] `test_copa_do_nordeste_so_para_nordestinos`.
- [ ] `test_classico_aparece_com_nome_na_manchete` (carreira no ABC: "Clássico-Rei" aparece).
- [ ] `test_draft_de_quem_comeca_no_nordeste_tem_dois_idolos_da_regiao`.
- [ ] `test_eventos_regionais_so_no_nordeste` e o teste de alcance cobre os novos.

## Verificação ponta a ponta

`carreira_amostra.py` com 10 carreiras começando no ABC e 10 no Flamengo, lidas lado a lado; a
do ABC tem que ter cara de Nordeste (Potiguar, Clássico-Rei, Copa do Nordeste, ídolos).
