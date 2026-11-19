# Torcida na edição (CSA e a Mancha Azul)

- **Data:** 2026-11-19
- **Status:** implementada (aguardando PR)
- **ADRs:** —

## Objetivo

A Azulão News (CSA) fecha toda edição com um cartão da Mancha Azul: a logo da torcida e uma frase
fixa ("Uma das maiores torcidas do Nordeste. Aqui só tem guerreiro!"). Pedido do dono ao criar o
time; fica no catálogo, então outra torcida pode ganhar o seu cartão sem código novo.

## Fora de escopo

- Seção de **notícias** da torcida. Pesquisado em 2026-11-19: no Google News, quase tudo sobre a
  Mancha Azul é policial (homicídios, condenações, brigas com organizadas do CRB) e, desde
  setembro de 2026, a Justiça proíbe as organizadas de CRB, CSA e Sport nos estádios de Alagoas.
  Uma seção só dela viraria página policial ou sairia vazia; o dono escolheu o cartão fixo. Notícia
  da torcida que for notícia do clube continua entrando no corpo da edição, como hoje.
- A torcida "Mancha Azul" do Avaí: homônima, nada a ver.

## Contratos

```toml
[csa.supporters]
name = "Mancha Azul"
text = "Uma das maiores torcidas do Nordeste. Aqui só tem guerreiro!"
logo = "mancha-azul.png"  # em src/geral/static/csa/
```

- `Team.supporters: Supporters | None` (`name`, `text`, `logo`).
- `render()` mostra o cartão "Torcida" antes do rodapé (HTML e texto) quando o time tem
  `supporters`. A logo sai de `{page_url}/static/<slug>/<logo>` só se o arquivo existir; sem ele, o
  cartão fica só com o nome e a frase.

## Critérios de aceite (como testes)

- [x] `test_render_supporters_card_with_its_logo_once_the_file_is_there`
- [x] `test_render_supporters_card_without_the_logo_file_shows_the_text`
- [x] `test_render_no_supporters_card_for_teams_without_one`
- [x] `test_every_supporters_card_has_its_logo_file`

## Riscos e dúvidas abertas

- A logo (`src/geral/static/csa/mancha-azul.png`, 160×160, fundo transparente, mostrada a 80×80)
  veio do link mandado pelo dono (loja da torcida), recortada em quadrado.
- A logo é marca da torcida, e as newsletters evitam símbolos oficiais para não parecer canal
  oficial (`identidade-visual-times.md`); aqui é homenagem pedida pelo dono, no rodapé, não no
  cabeçalho.
