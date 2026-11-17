# Carreira — o Nordeste em detalhe — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Estaduais, Copa do Nordeste, clássicos com nome, clubes e ídolos nordestinos e eventos regionais na Carreira.

**Architecture:** Tudo como dado novo em `mundo.toml`/`lendas.toml`/`eventos.toml`/`rotina.toml`; o motor lê `estado` do clube para o estadual e a região, `classico` para as manchetes; `oferta` recebe o clube de partida.

**Tech Stack:** Python, TOML, pytest.

**Spec:** `docs/features/carreira-nordeste.md`

## Global Constraints

- Commits conventional sem escopo, pt-BR, sem coautoria; portões antes de cada commit.
- Id de clube nunca muda (códigos compartilhados guardam o id); clube novo ganha id novo.
- Notas dos ídolos regionais são rascunho: comentário no topo pedindo revisão do dev.

## Review Focus

1. Clube sem estado ou estado sem campeonato → erro ao carregar, não 500 no meio da carreira.
2. Clássico de clube que não existe no mundo → erro ao carregar.
3. `{classico}`/`{rival}` só em eventos com `classico = true` (manchete nunca sai com campo vazio).
4. Oferta antiga (sem clube) continua válida para códigos já compartilhados.
5. Estadual não pode render dois títulos estaduais na mesma temporada.

---

### Task 1: Mundo com estados, Série D, clubes e clássicos
- [ ] Testes `test_todo_clube_brasileiro_tem_estado_e_estadual`, `test_classico_com_clube_desconhecido_e_erro`.
- [ ] `Clube.estado`, `Estado(uf, campeonato, regiao)`, `Classico(nome, clubes)`; `Dados.estados`, `Dados.classicos`, `Dados.regiao(clube)`.
- [ ] Commit `feat: estados, série d e clássicos no mundo da carreira`.

### Task 2: Estaduais, Copa do Nordeste e clássicos na temporada
- [ ] Testes `test_estadual_favorece_o_grande_do_estado`, `test_copa_do_nordeste_so_para_nordestinos`, `test_classico_aparece_com_nome_na_manchete`, rótulo "Rei do Nordeste".
- [ ] Condição `classico`, `regioes`; campos `{classico}`, `{rival}`.
- [ ] Commit `feat: estaduais, copa do nordeste e clássicos na carreira`.

### Task 3: Ídolos regionais no draft
- [ ] Teste `test_draft_de_quem_comeca_no_nordeste_tem_dois_idolos_da_regiao`; `oferta(dados, edicao, semente, clube=None)`; API `oferta {clube}`; tela manda o clube.
- [ ] Commit `feat: ídolos do nordeste no draft da carreira`.

### Task 4: Eventos e dia a dia do Nordeste
- [ ] ≥ 12 eventos e ≥ 4 rotinas com `regioes = ["nordeste"]`; `test_eventos_regionais_so_no_nordeste`; alcance continua cobrindo tudo.
- [ ] Commit `feat: eventos e dia a dia do nordeste na carreira`.
