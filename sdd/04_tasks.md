# 04 — Tasks

> Etapa 4 do fluxo SDD: Intent → Spec → Plan → **Tasks** → Implement/Test/Validate.
> Quebra o Plan em tarefas pequenas e verificáveis. Cada tarefa aponta para os requisitos que atende
> e tem um critério de pronto. O status é atualizado durante a implementação.

**Legenda de status:** ⬜ pendente · 🔄 em andamento · ✅ concluída · ⚠️ concluída com ressalva
**Mensagens de commit:** começam pelo ID da tarefa, ex.: `TK-07: nó validar (RF-01, RNF-02)`.

> Os IDs das tarefas usam o prefixo `TK-` para não confundir com os cenários oficiais `T01..T10`.

## Fase 1 — Fundação

| ID | Tarefa | Requisitos | Arquivos | Critério de pronto | Status |
|---|---|---|---|---|---|
| **TK-01** | Criar `compose.yaml` com `llm`, `embeddings` e `pgvector` (portas 8091/8092/5434, `MODELOS_DIR`, healthchecks) e remover `docker-compose.rag.yml` | RNF-01, RNF-07 | `compose.yaml`, `sql/init.sql` | `docker compose up -d` deixa os 3 serviços *healthy* | ✅ |
| **TK-02** | Adaptar `settings.py`: remover Pinecone e provedores cloud, manter provedores locais (padrão `llamacpp`), adicionar embeddings, `PG_DSN`, `TOP_K`, `SCORE_MINIMO`, `MAX_RODADAS`, caminhos de dados e logs; criar `.env.example` | RNF-01, RNF-03, RNF-04, RNF-07 | `settings.py`, `.env.example` | Importa sem `.env`; valores inválidos geram erro claro | ✅ |
| **TK-03** | Adaptar `llm.py`: `criar_modelo()` apontando para o llama.cpp (temperatura 0, timeout, retries) e `criar_cliente_embeddings()` | RNF-01, RNF-05 | `llm.py` | `00_testar_llm.py` responde e solicita `tool_calls` | ✅ |
| **TK-04** | Atualizar `requirements.txt`: sai `pinecone`, `fastapi`, `uvicorn`, `huggingface-hub`; entram `psycopg[binary]`, `pydantic`, `openai` | RNF-07 | `requirements.txt` | `pip install -r requirements.txt` em venv limpo sem erro | ✅ |

## Fase 2 — Recuperação (RAG)

| ID | Tarefa | Requisitos | Arquivos | Critério de pronto | Status |
|---|---|---|---|---|---|
| **TK-05** | `sql/init.sql`: extensão `vector` + tabela `documentos(id, titulo, categoria, conteudo, embedding vector(1024))` | RNF-03 | `sql/init.sql` | Tabela criada na primeira subida do pgvector | ✅ |
| **TK-06** | Adaptar `rag_utils.py`: embedding de documento e de consulta (com instrução de consulta), busca com `TOP_K`, filtro opcional por categoria, retorno com `fonte/titulo/categoria/trecho/score`, corte por `SCORE_MINIMO`, erro de banco tratado | RF-01, RF-02, RNF-03, RNF-05 | `rag_utils.py` | Função retorna evidências ordenadas por score; banco fora do ar gera erro controlado | ✅ |
| **TK-07** | Adaptar `12_ingestao.py`: ler a base oficial, *upsert* idempotente por `id`, indexar os 12 documentos, imprimir resumo | RNF-03 | `12_ingestao.py` | Rodar duas vezes mantém 12 linhas na tabela | ✅ |
| **TK-08** | Adaptar `13_busca_semantica.py`: busca sem LLM para uma pergunta ou para os 10 cenários, mostrando top-K e scores; usar para calibrar `SCORE_MINIMO` | RF-02, RNF-03 | `13_busca_semantica.py` | Saída com fontes e scores dos 10 cenários; limiar escolhido registrado em `05_validacao.md` | ✅ |

## Fase 3 — Protocolos e Tools

| ID | Tarefa | Requisitos | Arquivos | Critério de pronto | Status |
|---|---|---|---|---|---|
| **TK-09** | Criar `schemas.py`: `RespostaAgente` (com invariantes), argumentos das 3 Tools, `Protocolo`, enums de status e tipos | RNF-02, RNF-09 | `schemas.py` | Instâncias inválidas levantam `ValidationError` | ✅ |
| **TK-10** | Adaptar `sistema_chamados.py`: protocolos `SOL-xxxx` em `data/protocolos.json`, dados iniciais (SOL-1001..1003), consulta, registro sequencial com escrita atômica, validação de campos por tipo (valores genéricos contam como ausentes) | RF-03, RF-05 | `sistema_chamados.py` | Consulta exata; registro persiste após reinício; pendências listadas | ✅ |
| **TK-11** | Adaptar `tool_agente.py`: `buscar_normas`, `consultar_protocolo`, `registrar_solicitacao` com `args_schema` Pydantic; `InjectedState` para intenção; rejeição de argumentos com aparência de credencial; saída JSON estruturada | RF-01..07, RNF-09 | `tool_agente.py` | Sem intenção → `bloqueado`; dados faltando → `dados_pendentes`; argumento inválido → erro estruturado | ✅ |

## Fase 4 — Fluxo (LangGraph) e saída

| ID | Tarefa | Requisitos | Arquivos | Critério de pronto | Status |
|---|---|---|---|---|---|
| **TK-12** | Criar `prompts.py`: system prompt com uso de fontes, limites de autoridade, regras das Tools, abstenção, segurança de credenciais, documentos como dados (não instruções) e formato JSON final | RF-01..07 | `prompts.py` | Prompt revisado contra a Spec | ✅ |
| **TK-13** | Criar `observabilidade.py`: logger JSON Lines por execução em `logs/` e `mascarar()` | RNF-06, RF-07 | `observabilidade.py` | Eventos gravados; padrões de senha/token mascarados | ✅ |
| **TK-14** | Adaptar `graph.py`: `EstadoAgente`, nós `entrada`, `agente`, `tools`, `validar`, roteamento condicional, `MAX_RODADAS`, `recursion_limit`, tratamento de erro do LLM, eventos de log | RF-04, RNF-02, RNF-04, RNF-05, RNF-06 | `graph.py` | Grafo compila; diagrama Mermaid exportável | ✅ |
| **TK-15** | Implementar o nó `validar`: parse Pydantic, 1 reparo, fallback, invariantes da Spec 3.5 (fontes ⊆ recuperadas, status coerente com as Tools) | RF-01..03, RNF-02 | `graph.py` | Testes do TK-19 passam | ✅ |

## Fase 5 — Interfaces

| ID | Tarefa | Requisitos | Arquivos | Critério de pronto | Status |
|---|---|---|---|---|---|
| **TK-16** | Criar `main.py`: CLI interativa (pergunta → resposta formatada com status, fontes e protocolo; `/sair`) | RF-08 | `main.py` | Conversa no terminal funciona e gera log | ✅ |
| **TK-17** | Criar `data/esperado_cenarios.json` a partir da Spec 4.2 (sem alterar as perguntas) | RNF-08 | `data/esperado_cenarios.json` | Um registro por cenário: status, fontes e Tools esperadas | ✅ |
| **TK-18** | Criar `executar_cenarios.py`: roda T01–T10 com estado novo por caso, compara com o esperado (pré-classificação passou/parcial/falhou), grava `resultados/cenarios_<data>.json` e `.md` | RF-08, RNF-08 | `executar_cenarios.py` | Execução completa gera os dois arquivos e os logs | ✅ |

## Fase 6 — Testes automatizados

| ID | Tarefa | Requisitos | Arquivos | Critério de pronto | Status |
|---|---|---|---|---|---|
| **TK-19** | Testes unitários: schemas e invariantes, protocolos (consulta, registro, pendências, persistência, formato inválido), Tools (bloqueio, credencial), `mascarar()` | RF-03..07, RNF-02, RNF-06, RNF-09 | `tests/` | `pytest` verde sem serviços ligados | ✅ |
| **TK-20** | Testes do grafo com modelo simulado: roteamento, limite de rodadas, bloqueio sem intenção, reparo de schema, LLM indisponível, mensagem vazia | RNF-04, RNF-05, RNF-08 | `tests/` | `pytest` verde sem serviços ligados | ✅ |

## Fase 7 — Execução real e entregáveis

| ID | Tarefa | Requisitos | Arquivos | Critério de pronto | Status |
|---|---|---|---|---|---|
| **TK-21** | Executar os 10 cenários com os serviços locais, revisar cada resultado e analisar ao menos uma falha/limitação | todos os CA | `resultados/`, `logs/` | Resultados e logs reais salvos | ✅ |
| **TK-22** | `README.md`: arquitetura, modalidade, serviços, download dos modelos, comandos para instalar, subir, indexar, executar, testar | RNF-07 | `README.md` | Executável do zero seguindo só o README | ✅ |
| **TK-23** | `RELATORIO.md`: tabela dos 10 cenários com resultado e evidência, análise de falha/limitação | RNF-08 | `RELATORIO.md` | Todos os cenários com evidência | ✅ |
| **TK-24** | `USO_DE_IA.md`: IAs usadas e para quê; duas decisões técnicas revisadas (a partir das ADRs) | entregável 5 | `USO_DE_IA.md` | Documento completo | ✅ |
| **TK-25** | `sdd/05_validacao.md` e `sdd/matriz_rastreabilidade.md` com as evidências reais | SDD | `sdd/` | Todo RF/RNF ligado a tarefa, código e teste | ✅ |
| **TK-26** | Empacotamento: `.gitignore` (`.env`, `logs/`, `.venv`, `modelos/`), conferência de que não há segredos, ZIP ou repositório | RNF-07 | raiz | Varredura de segredos limpa; ZIP gerado | ✅ |
| **TK-27** | Evidência real de indisponibilidade (item 4.5 do enunciado): executar cenários e a Tool `buscar_normas` com os serviços locais desligados | RNF-05, RNF-06 | `resultados/indisponibilidade_*/`, `RELATORIO.md` | Evento `erro_llm` e resultado `erro_servico` gravados contra os serviços reais fora do ar | ✅ |
| **TK-28** | Correções da revisão final: (a) verbo de pedido solto dentro de pergunta ("qual o prazo para registrar...?") não abre a trava de registro; (b) o `validar` mantém `dados_pendentes` e trata protocolo em formato inválido quando o modelo marca outro status; (c) `dados_pendentes` só é aceito com respaldo da Tool ou pedido explícito, e depois de um `bloqueado` só uma confirmação ("sim") libera a trava (achado num teste manual da CLI); novas execuções dos cenários | RF-04, RF-05, RNF-02 | `graph.py`, `tests/`, `resultados/`, `RELATORIO.md`, `sdd/` | Testes novos passando; cenários reexecutados sem regressão | ✅ |

## Ordem e dependências

```
TK-01 → TK-02 → TK-03 → TK-04
          ↓
TK-05 → TK-06 → TK-07 → TK-08
          ↓
TK-09 → TK-10 → TK-11
          ↓
TK-12, TK-13 → TK-14 → TK-15
          ↓
TK-16, TK-17 → TK-18
          ↓
TK-19, TK-20 (podem começar junto com as fases 3 e 4)
          ↓
TK-21 → TK-23 → TK-25
TK-22, TK-24, TK-26 (ao final) → TK-27 → TK-28
```
