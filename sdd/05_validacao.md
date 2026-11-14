# 05 — Validação

> Etapa 5 do fluxo SDD: Intent → Spec → Plan → Tasks → **Implement/Test/Validate**.
> Registra como cada requisito foi verificado, com evidências reais. Preenchido durante a implementação.

## 1. Calibração do limiar de abstenção (TK-08, RF-02, ADR-07)

**Comando:** `python 13_busca_semantica.py --cenarios --top-k 4`
**Evidência completa:** [`resultados/busca_semantica_cenarios.txt`](../resultados/busca_semantica_cenarios.txt)
**Configuração:** Qwen3-Embedding-0.6B (Q8_0, 1024 dimensões), similaridade cosseno no pgvector, 12 documentos.

| Caso | 1º colocado | Score | Documento esperado (Spec 4.2) | Correto? |
|---|---|---|---|---|
| T01 | ACAD-001 | 0,8457 | ACAD-001 | ✅ |
| T02 | ACAD-002 | 0,7425 | ACAD-002 | ✅ |
| T03 | ACAD-003 | 0,8551 | ACAD-003 | ✅ |
| T04 | ACAD-008 | 0,3931 | — (consulta de protocolo) | ✅ abaixo do limiar |
| T05 | ACAD-005 | 0,8322 | ACAD-005 | ✅ |
| T06 | ACAD-006 | 0,6327 | ACAD-006 | ✅ |
| T07 | ACAD-007 | 0,7943 | ACAD-007 | ✅ |
| T08 | ACAD-008 | 0,6662 | ACAD-008 | ✅ |
| T09 | ACAD-009 | 0,3468 | — (sem evidência) | ✅ abaixo do limiar |
| T10 | ACAD-003 | 0,5873 | ACAD-003 (opcional) | ✅ |

**Leitura dos dados:**
- Menor score de um documento correto em 1º lugar: **0,6327** (T06).
- Maior score de uma pergunta sem resposta na base: **0,3931** (T04) e **0,3468** (T09).
- Documentos secundários ("ruído") ficaram entre **0,50 e 0,63** (ex.: ACAD-005 em T01 com 0,6044;
  ACAD-001 em T08 com 0,6260).

**Decisão:** `SCORE_MINIMO = 0.55`.
- Margem de ~0,20 acima das perguntas sem evidência (T09 abstém mesmo com variação de redação).
- Margem de ~0,08 abaixo do pior acerto (T06).
- 0,60 cortaria mais ruído, mas ficaria a 0,03 do T06; o ruído restante é tratado pelo nó `validar`,
  que só aceita fontes efetivamente recuperadas, e pelo prompt, que pede para citar só o que foi usado.

**Limitação:** calibração feita com apenas 10 perguntas; outras redações podem exigir novo ajuste
(`SCORE_MINIMO` é configurável no `.env`).

## 2. Testes automatizados (TK-19, TK-20, RNF-08)

**Comando:** `python -m pytest` → **80 passed** (≈3 s), sem LLM, embeddings ou banco: a busca no
pgvector é substituída por uma função falsa e o LLM por um modelo roteirizado que devolve `tool_calls`.

| Arquivo | Cobre |
|---|---|
| `tests/test_unidades.py` (57) | Contrato `RespostaAgente` e invariantes; argumentos das Tools; protocolos (consulta, pendências, persistência, escrita atômica); trava da Tool de ação; refazer a busca sem filtro; detecção de intenção (inclusive verbo de pedido dentro de pergunta) e de confirmação; extração de JSON; máscara de credenciais; log JSONL |
| `tests/test_grafo.py` (23) | Roteamento; correções do `validar` (inclusive `dados_pendentes` e protocolo em formato inválido); confirmação após registro bloqueado; abstenção; bloqueio sem intenção; continuação do registro no turno seguinte; limite de rodadas; reparo de schema; `forcar_busca`; LLM indisponível; mensagem vazia; Tool desconhecida; erro de serviço |

## 3. Execuções reais (TK-21)

| Execução | Oficiais (passou/parcial/falhou) | Extras | O que mudou depois |
|---|---|---|---|
| `execucao_20261111-155358` | 8 / 1 / 1 | 4 de 5 | Busca refeita sem filtro (T07); prompt (T06, X04) |
| `execucao_20261111-160107` | 8 / 1 / 1 | 5 de 5 | Nó `forcar_busca` + checagem de ACAD no texto (T06, T08) — ADR-08 |
| `execucao_20261111-161525` | 9 / 1 / 0 | 5 de 5 | Revisão final, TK-28: intenção em perguntas e status no `validar` |
| `execucao_20261114-170534` | 9 / 1 / 0 | 5 de 5 | TK-28 (c): confirmação explícita após registro bloqueado |
| `execucao_20261114-175041` | **9 / 1 / 0** | **5 de 5** | — (confirmação sem regressão) |

**Indisponibilidade real (TK-27):** com os containers desligados, T01 e T04 terminaram em `erro_llm` com mensagem segura, e `buscar_normas` devolveu `erro_servico`, sem exceção ([`resultados/indisponibilidade_20261112-092833/`](../resultados/indisponibilidade_20261112-092833/), `RELATORIO.md` 4.1).

Detalhes, respostas e análise das falhas: [`RELATORIO.md`](../RELATORIO.md).

## 4. Desvios em relação ao Plan

| Desvio | Motivo | Registrado em |
|---|---|---|
| Nó `auditar_tools` além dos 4 previstos | O `ToolNode` só devolve mensagens; o `validar` precisa das fontes e resultados no estado | `03_plan.md` 3.2 |
| Nó `forcar_busca` | O modelo pulou a busca em execuções reais (T06, T08); `tool_choice="required"` falhou no llama.cpp | `03_plan.md` ADR-08 |
| Chave `resultado` (em vez de `status`) na saída das Tools | Evitar confusão com o `status` do protocolo | `02_spec.md` 3.3 |
| Fallback do JSON usa texto livre com status derivado (em vez de sempre `erro`) | Não descartar uma resposta útil quando o estado permite derivar um status seguro | `03_plan.md` 5 |
| Busca filtrada sem resultado é refeita sem filtro | Falha do T07 na 1ª execução | `RELATORIO.md` 5.1 |
| Memória da conversa por sessão (`InMemorySaver`) | Permitir que o estudante informe a turma no turno seguinte ao `dados_pendentes` | `03_plan.md` 5 |
| Detecção de intenção ignora verbo solto em pergunta; `validar` respeita `dados_pendentes`/`formato_invalido` | Casos de borda achados na revisão final (TK-28) | `RELATORIO.md` 5.6 |
| `dados_pendentes` só com respaldo; confirmação explícita após `bloqueado` | Teste manual da CLI: o status escrito pelo modelo liberava a trava no turno seguinte (TK-28) | `RELATORIO.md` 5.7 |

## 5. Situação final dos requisitos

Todos os RF e RNF foram verificados (ver [`matriz_rastreabilidade.md`](matriz_rastreabilidade.md)).
Ressalva: **RF-01** no T08 (3ª, 4ª e 5ª execuções), que citou uma fonte secundária realmente recuperada (score 0,626)
além da correta; classificado como *parcial*.
