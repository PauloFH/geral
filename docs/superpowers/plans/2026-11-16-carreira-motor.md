# Carreira — PR 1: motor, dados e API — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline, regra do harness) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Motor determinístico da carreira (draft de lendas → temporadas → escolhas → final), alimentado por TOMLs editáveis, exposto em duas rotas JSON sem estado.

**Architecture:** Pacote `src/geral/games/carreira/` puro (sem web): `dados.py` lê e valida os TOMLs, `regras.py` tem atributos e pesos, `draft.py` a oferta e a montagem, `motor.py` a simulação, `final.py` rótulo e "parecido com", `codigo.py` o link compartilhável. As rotas ficam em `web/app.py`, como as dos outros joguinhos. Toda aleatoriedade sai de `random.Random(str)` com a semente; nada de `random` global nem relógio.

**Tech Stack:** Python 3.12, tomllib, pydantic, FastAPI, pytest.

**Spec:** `docs/features/carreira.md`

## Global Constraints

- Commits: conventional sem escopo, uma linha, em pt-BR, sem trailer de coautoria.
- Antes de cada commit: `uv run ruff check . && uv run ruff format --check . && uv run pytest`.
- Textos para o torcedor (manchetes, escolhas, rótulos) em pt-BR; nomes de módulo seguem o domínio em pt como em `games/velha/`.
- Atributos (exatos): `velocidade, finalizacao, passe, drible, marcacao, fisico, cabeceio, lideranca`, notas inteiras de 1 a 99.
- Posições (exatas): `zagueiro, lateral, volante, meia, atacante`. Sem goleiro.
- Mesma entrada → mesma carreira (semente da carreira independente da do draft).
- Não tocar em `store.py`, bolão, Urubu nem `web/announce.py`.

## Review Focus

1. **Escolhas em prefixo:** simular com `escolhas=[a]` e depois `[a, b]` precisa repetir exatamente as temporadas até a 2ª escolha — senão a carreira "muda" na frente do torcedor. Teste no Task 3.
2. **Carreira infinita ou vazia:** qualquer draft (o mais fraco: tudo 1) termina com aposentadoria entre 30 e 42 anos e ≥ 1 temporada profissional. Teste no Task 3.
3. **Escolha fora do alcance:** índice negativo, ≥ número de opções, ou escolhas sobrando depois do fim → 422, nunca 500. Teste no Task 6.
4. **Código adulterado:** `c/{codigo}` com base64 inválido, JSON truncado ou campos trocados → erro tratado (`CodigoInvalido`), nunca exceção crua. Teste no Task 5.
5. **Nome do craque com HTML/emoji/200 caracteres:** limitado a 24 caracteres na API (422 acima); manchetes interpolam o nome cru (o escape é do template no PR 2). Teste no Task 6.

---

### Task 1: Regras e dados base (lendas e mundo)

**Files:**
- Create: `src/geral/games/carreira/__init__.py`, `regras.py`, `dados.py`, `lendas.toml`, `mundo.toml`
- Test: `tests/test_carreira_dados.py`

**Interfaces:**
- Produces: `regras.ATRIBUTOS: tuple[str, ...]`, `regras.POSICOES: tuple[str, ...]`, `regras.PESOS: dict[str, dict[str, float]]` (soma 1 por posição), `regras.geral(notas: dict[str, int], posicao: str) -> int` (média ponderada arredondada, 1–99).
- Produces: dataclasses congeladas em `dados.py`: `Lenda(nome, wikidata, edicoes: tuple[str, ...], notas: dict)`, `Liga(id, pais, divisao: int, forca: int)`, `Clube(id, nome, liga, prestigio: int, time: str | None, wikidata: str | None)`, e `Dados(lendas, ligas: dict, clubes: dict, eventos, escolhas, finais, versao: str)`; `carregar(pasta: Path = PASTA) -> Dados` com cache por pasta (`functools.cache`); `versao` = 8 primeiros hex do sha256 dos bytes de todos os `*.toml` em ordem de nome. Erro de dado → `ValueError` com arquivo e item.
- `mundo.toml`: `[[liga]] id, pais, divisao, forca` e `[[clube]] id, nome, liga, prestigio, time?, wikidata?`. ≈ 15 ligas do spec; Brasil A/B/C com os clubes reais de 2026 (A e B completas, C ≥ 12), `time` = slug do `teams.toml` quando o clube tem edição, `wikidata` igual ao de `velha/clubes.toml` quando existir. Exterior: 6–10 clubes por liga, prestígio coerente (Real Madrid ≫ Getafe).
- `lendas.toml`: ~40 lendas `edicoes = ["geral", ...]` (ídolos dos times com Craque do dia + nomes de seleção), notas por atributo, todas com `wikidata`. **Rascunho: o dev revisa antes do merge** (comentário no topo do arquivo).

- [ ] **Step 1: testes falhando** — `test_pesos_somam_um_por_posicao`; `test_geral_pondera_pela_posicao` (atacante com finalização 99 e marcação 1 > zagueiro com as mesmas notas); `test_carregar_le_os_arquivos_reais` (≥ 40 lendas na `geral`, ≥ 15 ligas, ≥ 150 clubes, ≥ 20 clubes na liga `bra-a`); `test_nota_fora_de_1_a_99_ou_atributo_desconhecido_e_erro` (pasta `tmp_path` com um TOML ruim → `ValueError` citando o nome); `test_clube_com_liga_desconhecida_e_erro`; `test_versao_muda_quando_um_toml_muda`.
- [ ] **Step 2:** `uv run pytest tests/test_carreira_dados.py -q` → FAIL (módulo ausente).
- [ ] **Step 3:** implementar `regras.py` e `dados.py`; escrever `mundo.toml` e `lendas.toml`. `eventos/escolhas/finais` ainda vazios (listas vazias se o arquivo não existir).
- [ ] **Step 4:** testes → PASS.
- [ ] **Step 5:** `git commit -m "feat: dados do joguinho da carreira (lendas e mundo)"`

### Task 2: Draft e edições

**Files:**
- Create: `src/geral/games/carreira/draft.py`
- Test: `tests/test_carreira_draft.py`

**Interfaces:**
- Consumes: `Dados`, `Lenda`, `regras.ATRIBUTOS`.
- Produces: `edicoes(dados, times: Iterable[str]) -> list[str]` (`"geral"` + cada slug de `times` com ≥ 1 lenda própria, na ordem recebida); `oferta(dados, edicao: str, semente_draft: str) -> list[Lenda]` (9, sem repetição; próprias primeiro, completando com `geral`, embaralhado por `Random(f"draft:{edicao}:{semente_draft}")`); `Roubo(lenda: str, atributo: str)` (pydantic); `montar(ofertadas: list[Lenda], roubos: list[Roubo]) -> dict[str, int]`; `class JogadaInvalida(ValueError)`.
- Regras do `montar`: exatamente 8 roubos, 8 atributos distintos, toda lenda dentre as 9 ofertadas, no máximo 8 lendas distintas (a 9ª só entra no lugar de uma das 8 primeiras: usar a reserva = "sortear de novo"); senão `JogadaInvalida` com mensagem em pt.

- [ ] **Step 1: testes falhando** — `test_oferta_e_estavel_e_tem_nove_sem_repetir`; `test_edicao_de_time_prioriza_as_proprias_e_completa_com_a_geral` (pasta de teste com 2 lendas `vasco` → as 2 estão na oferta do vasco); `test_edicoes_so_times_com_lenda_propria` (`edicoes(d, ["vasco", "abc"])` sem lenda do abc → `["geral", "vasco"]`); `test_steal_outside_offer_or_repeated_attribute_is_422` (aqui: `JogadaInvalida` para lenda fora, atributo repetido, 7 roubos, reserva + as 8 originais); `test_montar_devolve_as_notas_roubadas`.
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS.
- [ ] **Step 5:** `git commit -m "feat: draft de lendas da carreira"`

### Task 3: Motor da carreira

**Files:**
- Create: `src/geral/games/carreira/motor.py`, `eventos.toml`, `escolhas.toml` (esquema + ~10 eventos e ~5 escolhas iniciais)
- Modify: `dados.py` (ler `Evento`, `Escolha`, `Opcao`)
- Test: `tests/test_carreira_motor.py`

**Interfaces:**
- Consumes: `Dados`, `draft.oferta/montar`, `regras.geral`.
- Produces (pydantic, viram a resposta da API):
  - `Craque(nome: str ≤ 24, camisa: int 1–99, posicao, pe: Literal["direito","esquerdo","ambos"], clube: str | None)`
  - `Entrada(semente_draft, semente, craque: Craque, roubos: list[Roubo], escolhas: list[int])`
  - `Temporada(ano: int, idade, clube, liga, jogos, gols, assistencias, nota: int, titulos: list[str], manchete: str, eventos: list[str])`
  - `Escolha(id, pergunta, opcoes: list[str])`; `Carreira(temporadas, pendente: Escolha | None, final: Final | None)` (`Final` no Task 4; aqui `final` só com `nota` e `titulos`).
  - `simular(dados, edicao, entrada) -> Carreira`; levanta `JogadaInvalida` (escolha fora do alcance, escolhas sobrando, clube inexistente ou fora do Brasil na `geral`).
- Dados: `Evento(id, peso, manchetes: tuple[str, ...], condicao: Condicao, efeito: Efeito, unico: bool)`; `Condicao` com `idade_min/max, posicoes, nota_min/max, forca_min/max, fases (inicio|auge|fim), requer, exclui` (todos opcionais); `Efeito` com `nota (delta), saida (prob. extra de transferência), titulo (nome da taça) , selecao (bool)`. `Escolha(id, pergunta, condicao, opcoes: [Opcao(texto, destino)])` com `destino ∈ {ficar, europa, maior, emprestimo, arabia, casa, aposentar, mais_um}` — o motor implementa cada destino.
- Algoritmo (decisões que o teste não fixa):
  - `rng = Random(f"carreira:{semente}")`, consumido só em ordem cronológica — uma escolha nunca altera o que veio antes dela (prefixo estável).
  - Nota começa em `geral(notas) - 25` aos 16 (mín. 30) e caminha para um teto = `geral(notas)` ± 8 sorteado; sobe até ~27, estável até ~31, cai depois; eventos somam `efeito.nota`.
  - Início: edição de time → o clube com `time == edicao`; `geral` → `craque.clube`. Base aos 16–17 (sem jogos), profissional dos 17–18.
  - Minutos = f(nota − nível do clube) onde nível = `(forca da liga + prestigio)/2`; gols e assistências por posição × atributos (`finalizacao`, `passe`) × minutos; títulos de liga/copa com prob. crescente com prestígio e nota.
  - Fim de temporada: se nota ≫ nível, propostas de clubes de nível maior; ~3 a cada carreira viram `Escolha` (sorteada entre as cuja condição casa, sem repetir id); fora delas, a transferência é automática pelo rng.
  - Aposentadoria entre 33 e 40 (antes se nota < 45); o `mais_um` estende 1 ano. Máximo absoluto 42.
  - 1–2 eventos por temporada, pesados, respeitando `condicao`, `unico` e `requer/exclui`; a manchete é a de maior destaque, interpolada com `{nome}`, `{clube}`, `{liga}`, `{gols}`, `{idade}`.

- [ ] **Step 1: testes falhando** — `test_same_input_gives_the_same_career`; `test_escolhas_em_prefixo_repetem_o_passado`; `test_better_draft_scores_higher_on_average` (200 sementes: média do draft das melhores notas > média do pior + 10, e o pior vence em ≥ 1 semente); `test_choices_change_the_story` (achar uma semente com `pendente`, opção `europa` × `ficar` → conjuntos de clubes diferentes); `test_team_edition_starts_in_its_youth_and_fills_draft_with_geral_legends` (vasco: 1ª temporada no clube `time="vasco"`, 0 jogos, idade 16); `test_geral_comeca_no_clube_escolhido_e_recusa_clube_de_fora`; `test_toda_carreira_termina_entre_30_e_42` (500 sementes, inclusive draft com notas 1).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS.
- [ ] **Step 5:** `git commit -m "feat: motor da carreira com temporadas, transferências e escolhas"`

### Task 4: Variedade — eventos, escolhas, finais e "parecido com"

**Files:**
- Create: `src/geral/games/carreira/final.py`, `finais.toml`
- Modify: `eventos.toml` (≥ 60), `escolhas.toml` (≥ 15), `motor.py` (preencher `final`)
- Test: `tests/test_carreira_variedade.py`

**Interfaces:**
- Consumes: `Carreira`, `velha.base.load() -> Base` (`Player.clubes`, `posicoes`, `selecao`, `copa`, `fama`).
- Produces: `Final(nota: int 0–100, rotulo: str, descricao: str, titulos: dict[str, int], clubes: list[str], jogos, gols, selecao: int, copa: bool, parecido: str)`; `final.rotular(dados, temporadas) -> tuple[str, str]` (primeiro de `finais.toml` em ordem de prioridade cuja condição casa; o último é sempre o curinga); `final.parecido(base, temporadas, posicao) -> str` (mesma família de posição; pontua clubes brasileiros em comum via `Clube.wikidata`, seleção, Copa e fama próxima da nota; desempate pelo nome).
- `finais.toml`: `[[final]] rotulo, descricao, prioridade, condicao` com campos `clubes_min/max, anos_um_clube_min, titulos_min, nota_min/max, europa_min (temporadas em liga de força ≥ 80), copa, gols_min`. ≥ 12 rótulos do spec.

- [ ] **Step 1: testes falhando** — `test_careers_vary` (500 sementes de carreira, mesmo draft médio, escolhas pela opção 0: ≥ 8 rótulos, ≥ 40 clubes distintos, nenhuma sequência completa de manchetes em > 2% das carreiras); `test_every_event_and_choice_in_toml_is_reachable` (2.000 sementes × drafts e posições variados × escolhas pela semente: todo `Evento.id` e `Escolha.id` aparece ≥ 1 vez); `test_manchetes_sem_campo_sobrando` (nenhuma manchete gerada contém `{` ou `}`); `test_parecido_prefere_quem_passou_pelos_mesmos_clubes` (base falsa via `velha_fakes`); `test_rotulo_bandeira_para_quem_ficou_no_mesmo_clube` (temporadas montadas à mão).
- [ ] **Step 2:** FAIL. **Step 3:** escrever o conteúdo e `final.py`; rodar `uv run python scripts/carreira_amostra.py 20` (Task 7 cria; aqui basta um loop no REPL) e ajustar pesos até os testes passarem sem afrouxar os limites. **Step 4:** PASS.
- [ ] **Step 5:** `git commit -m "feat: eventos, escolhas e finais variados na carreira"`

### Task 5: Código compartilhável

**Files:**
- Create: `src/geral/games/carreira/codigo.py`
- Test: `tests/test_carreira_codigo.py`

**Interfaces:**
- Produces: `Resumo(rotulo, nota, titulos: int, clubes: list[str], nome, posicao)`; `codificar(versao: str, edicao: str, entrada: Entrada, resumo: Resumo) -> str` (JSON compacto → zlib → base64url sem `=`); `decodificar(codigo: str) -> Compartilhado(versao, edicao, entrada, resumo)`; `class CodigoInvalido(ValueError)`. Limite 2.000 caracteres.

- [ ] **Step 1: testes falhando** — `test_career_code_reopens_the_exact_career` (codificar → decodificar → `simular` dá o mesmo `final`); `test_old_code_after_data_change_shows_the_card_summary` (versão diferente: o `Resumo` volta intacto e o chamador sabe que a versão mudou); `test_codigo_adulterado_e_codigo_invalido` (lixo, base64 válido de JSON quebrado, campo faltando, > 2.000 chars).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS.
- [ ] **Step 5:** `git commit -m "feat: código compartilhável da carreira"`

### Task 6: Rotas da API

**Files:**
- Modify: `src/geral/web/app.py` (modelos `OfertaIn`, `SimularIn` perto dos outros `*In`; rotas perto das do `quem-e`)
- Test: `tests/test_web_carreira.py`

**Interfaces:**
- Consumes: `carregar`, `edicoes(dados, listed)`, `oferta`, `simular`, `codificar`.
- Produces:
  - `POST /api/jogos/carreira/{edition}/oferta` `{}` → `{semente_draft, lendas: [{nome, notas}] ×9}` (semente nova: `secrets.token_urlsafe(8)`).
  - `POST /api/jogos/carreira/{edition}/simular` `SimularIn{semente_draft, semente?: str, craque, roubos ×8, escolhas ≤ 10}` → `{semente, versao, carreira: Carreira, codigo: str | None}` (`codigo` só com `final`). `JogadaInvalida` → 422 `{detail}`; edição fora de `edicoes(dados, listed)` → 404.

- [ ] **Step 1: testes falhando** — `test_oferta_e_simulacao_ate_o_fim` (escolhe sempre a opção 0 até `final`); `test_edicao_desconhecida_e_404` (`xyz`); `test_hidden_team_has_no_career_edition` (time com `listed = false` e lenda própria → 404); `test_roubo_invalido_escolha_fora_e_escolha_sobrando_sao_422`; `test_nome_longo_e_422` (25 caracteres).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS.
- [ ] **Step 5:** `git commit -m "feat: rotas da api da carreira"`

### Task 7: Amostra para o dev e fechamento

**Files:**
- Create: `scripts/carreira_amostra.py`
- Modify: `docs/features/carreira.md` (marcar os critérios do PR 1)

- [ ] **Step 1:** `scripts/carreira_amostra.py N [--edicao geral] [--posicao atacante]` imprime N carreiras em texto (draft, uma linha por temporada com manchete, escolhas tomadas ao acaso, final). Sem teste: é ferramenta de leitura.
- [ ] **Step 2:** `uv run python scripts/carreira_amostra.py 20 > /tmp/...` e ler: a variedade tem que ser visível a olho, não só nos números. Ajustar conteúdo se não for.
- [ ] **Step 3:** portões: `uv run ruff check . && uv run ruff format --check . && uv run pytest`.
- [ ] **Step 4:** `git commit -m "chore: amostra de carreiras para revisar a variedade"`; revisão em contexto limpo da branch; PR com a lista de lendas e notas destacada para revisão do dev.
