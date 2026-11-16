# Carreira: monte um craque e viva a carreira dele

- **Data:** 2026-11-16
- **Status:** proposta
- **ADRs:** —

## Objetivo

Quinto joguinho, inspirado nos virais de navegador (The Fenômeno, El Ídolo, Destiny Eleven, Copero):
o torcedor monta um craque roubando um atributo de cada uma de 8 lendas e assiste à carreira dele
dos 16 anos à aposentadoria, em 3 a 5 minutos, com 2 a 4 escolhas no caminho e um card final para
compartilhar. **Livre** (joga quantas vezes quiser, sorteio novo a cada vez). Requisito central:
**variedade** — duas carreiras raramente contam a mesma história.

## Fora de escopo

- Lances jogáveis (minijogos ao estilo GAMBETA), Carreira do dia, ranking, goleiro (fica para depois;
  o motor já guarda a semente para a Carreira do dia sair barata).
- O 7a0 do clube (outro desenho, depois deste).

## Contratos

- **Atributos** (8, de 1 a 99): `velocidade, finalizacao, passe, drible, marcacao, fisico, cabeceio,
  lideranca`. Posições: `zagueiro, lateral, volante, meia, atacante`; o peso de cada atributo na
  nota geral depende da posição (tabela em `carreira/regras.py`).
- **Lendas** (`src/geral/games/carreira/lendas.toml`): `[[lenda]] nome, wikidata, edicoes = ["geral",
  "vasco"], notas = {…8…}`. Rascunho das notas por Claude, **revisão do dev antes de ir ao ar**
  (como o Craque do dia). Edições = `geral` + os times visíveis no catálogo com ≥ 1 lenda própria
  (o Flamengo segue a mesma chave que o esconde hoje); o draft prioriza as próprias e completa as
  9 com lendas da `geral` (o ABC entra assim).
- **Mundo** (`carreira/mundo.toml`, à mão): ligas `{id, pais, divisao, forca 1–100}` e clubes `{nome,
  liga, prestigio 1–100}` — Brasil A/B/C, Argentina, Portugal, Espanha, Inglaterra, Itália, Alemanha,
  França, Holanda, Turquia, Arábia, Japão, EUA, México (≈ 15 ligas, ≈ 150 clubes). Na edição de um
  time a carreira começa na base dele; na `geral`, o torcedor escolhe o clube brasileiro de partida.
- **Variedade, de onde vem** (tudo dado em TOML, não código; fácil de crescer):
  - `carreira/eventos.toml`: ≥ 60 eventos com condição (idade, posição, nota, força da liga, fase da
    carreira, evento anterior) e peso: lesão grave, artilharia, rebaixamento, título, convocação,
    Copa, gol de título em clássico, briga com o técnico, volta por cima, ídolo da torcida…
    Cada um com 2+ manchetes no estilo de jornal (`"{nome} decide o clássico e vira ídolo"`).
  - `carreira/escolhas.toml`: ≥ 15 decisões que aparecem conforme a fase (renovar ou sair, Europa ou
    ficar e virar ídolo, empréstimo para jogar, dinheiro da Arábia, voltar para casa, mais um ano ou
    parar). Cada opção muda probabilidades, não garante resultado.
  - Finais: ≥ 12 rótulos (`Bandeira`, `Cigano da bola`, `Promessa que não vingou`, `Rei da Europa`,
    `Artilheiro`, `Herói de uma Copa`…) + "Sua carreira lembra a de ___": o jogador da `velha/base.json`
    de trajetória mais parecida (clubes e países em comum, fama).
- **Motor** (`src/geral/games/carreira/`, puro e determinístico):
  `oferta(edicao, semente_draft) -> list[Lenda]` (9: as 8 do draft e 1 reserva para o único
  "sortear de novo", que troca uma lenda pela reserva); `simular(edicao, semente, craque, roubos,
  escolhas) -> Carreira` — a semente da carreira é **outra**, independente da do draft com `temporadas` (idade, clube,
  jogos, gols, assistências, títulos, manchete), `pendente: Escolha | None` e `final: Final | None`
  (nota 0–100, rótulo, títulos, parecido-com). Mesma entrada → mesma carreira, sempre.
- **Rotas** (sem estado no servidor, como os outros joguinhos):
  - `GET /jogos/carreira[/{edition}]` — a página; edições = `geral` + times com lendas.
  - `POST /api/jogos/carreira/{edition}/oferta {}` → `{semente_draft, lendas: [{nome, notas}] ×9}`.
  - `POST /api/jogos/carreira/{edition}/simular {semente_draft, semente, craque: {nome, camisa,
    posicao, pe, clube}, roubos: [{lenda, atributo}] ×8, escolhas: [int]}` → `Carreira` até a próxima
    escolha ou o fim (o servidor sorteia `semente` se vier vazia). `clube` só na `geral`: qualquer
    clube brasileiro do `mundo.toml` (A, B ou C); na edição de time é ignorado.
  - `GET /jogos/carreira/c/{codigo}` reabre uma carreira terminada. Código (base64url, nada guardado)
    = versão dos dados + entrada + resumo do card (rótulo, nota, títulos, clubes). Se os TOMLs mudaram
    desde então, o link mostra o card pelo resumo e oferece "jogar com o mesmo draft"; com a mesma
    versão, refaz a carreira inteira. Roubo fora da oferta, mais de uma troca, atributo repetido ou
    escolha inválida → 422; edição desconhecida ou time oculto → 404.
- **Página**: criar craque → draft (lendas uma a uma, notas visíveis, 1 sorteio de novo) → temporadas
  aparecendo uma a uma, pausando nas escolhas → card. Card desenhado em `<canvas>` (sem Pillow) e
  enviado pelo Web Share; texto de reserva `Carreira · Vasco · Bandeira 87 🏆×9` + link `c/{codigo}`.

## Critérios de aceite (como testes)

- [ ] `test_same_input_gives_the_same_career`: mesma semente, draft e escolhas → carreira idêntica.
- [ ] `test_careers_vary`: 500 sementes de carreira com o mesmo draft → ≥ 8 rótulos finais diferentes, ≥ 40
  clubes distintos visitados e nenhuma sequência de manchetes repetida em mais de 2% das carreiras.
- [ ] `test_better_draft_scores_higher_on_average`: draft forte supera draft fraco em média, mas não sempre.
- [ ] `test_choices_change_the_story`: mesma semente, escolha "Europa" × "ficar" → clubes diferentes.
- [ ] `test_team_edition_starts_in_its_youth_and_fills_draft_with_geral_legends`.
- [ ] `test_steal_outside_offer_or_repeated_attribute_is_422`.
- [ ] `test_career_code_reopens_the_exact_career` e `test_old_code_after_data_change_shows_the_card_summary`.
- [ ] `test_hidden_team_has_no_career_edition`.
- [ ] `test_every_event_and_choice_in_toml_is_reachable` (nenhum dado morto) e manchetes sem `{campo}` sobrando.

## Verificação ponta a ponta

```bash
uv run pytest && uv run uvicorn geral.web.app:create_app --factory
# Playwright, celular e desktop: carreira completa na geral e no Vasco; card baixado; link c/ reabre.
uv run python scripts/carreira_amostra.py 20   # 20 carreiras em texto para o dev ler a variedade
```

## Entregas (PRs)

1. Motor + mundo + eventos/escolhas/finais + lendas da `geral` (rascunho revisado) + rotas da API.
2. Página, draft, animação e card.
3. Lendas por time (Vasco, Palmeiras, Flamengo, Náutico, ABC) e cartão em `/jogos`.

## Riscos e dúvidas abertas

- As notas das lendas geram discussão de torcida: aceitável, é parte da graça; revisão do dev é obrigatória.
- Lendas da `geral`: ~40 nomes (ídolos dos times + nomes de seleção) e as notas, rascunho de Claude
  no PR 1, revisão do dev antes do merge.
