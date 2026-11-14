# Histórico de commits

Exportado de `git log` para que a rastreabilidade (hashes citados na matriz) possa ser seguida mesmo pelo ZIP, que não inclui a pasta `.git`. Ordem cronológica; cada commit traz o ID da tarefa (TK-xx) e os requisitos atendidos.

> **Situação do repositório:** em 14/11/2026 o repositório git foi recriado do zero (a pasta `.git` original
> foi apagada). Este arquivo passou a ser o registro do histórico de desenvolvimento: os hashes abaixo são os
> do repositório original e não existem no repositório atual. A última entrada (TK-28) foi feita depois
> disso e por isso não tem hash.

## 0f92d05 — Base: código reaproveitado das aulas e SDD (intent, spec, plan, tasks)

11/11/2026 15:39

Arquivos .py, compose e requirements copiados sem alteração das aulas
"pinecone" e "20260926", mais os dados oficiais da atividade. As
adaptações vêm nos próximos commits, identificadas pelo ID da tarefa (TK-xx).

## f83a7f3 — TK-04: dependências do agente local (RNF-07)

11/11/2026 15:42

## 0d12183 — TK-05: tabela documentos com id, título e categoria (RNF-03)

11/11/2026 15:42

## 7932bcc — TK-02: configuração local via .env, sem Pinecone (RNF-01, RNF-03, RNF-04, RNF-07)

11/11/2026 15:42

## 755f7fd — TK-03: ChatOpenAI e embeddings apontando para o llama.cpp (RNF-01, RNF-05)

11/11/2026 15:42

## 7086f00 — TK-01: compose com llama.cpp (LLM e embeddings) e pgvector locais (RNF-01, RNF-07)

11/11/2026 15:42

Substitui o docker-compose.rag.yml da aula (removido no commit do TK-04).

## 1079f2a — TK-06: busca no pgvector com metadados, Top-K, filtro e score mínimo (RF-01, RF-02, RNF-03, RNF-05)

11/11/2026 15:44

## b3cb9c7 — TK-07: ingestão idempotente dos 12 documentos com id e categoria (RNF-03)

11/11/2026 15:44

## c166277 — TK-08: busca sem LLM e calibração do SCORE_MINIMO em 0,55 (RF-02, RNF-03)

11/11/2026 15:44

## 8d48424 — TK-13: log JSON Lines por sessão e mascaramento de credenciais (RNF-06, RF-07)

11/11/2026 15:46

## 4e4a91f — TK-09: contratos Pydantic da resposta, das Tools e do protocolo (RNF-02, RNF-09)

11/11/2026 15:46

## fd479d2 — TK-10: protocolos SOL em JSON com dados iniciais, validação por tipo e escrita atômica (RF-03, RF-05)

11/11/2026 15:46

## 39568db — TK-11: buscar_normas, consultar_protocolo e registrar_solicitacao com trava por InjectedState (RF-01..07, RNF-09)

11/11/2026 15:46

## 7a58d8c — TK-12: system prompt com fontes, limites de autoridade, regras das Tools e JSON final (RF-01..07)

11/11/2026 15:52

## fd028bb — TK-14, TK-15: StateGraph com entrada, auditar_tools, validar, limite de rodadas e erros do LLM (RF-04, RNF-02, RNF-04, RNF-05, RNF-06)

11/11/2026 15:52

## a5c19cc — TK-13: máscara reconhece 'senha do portal é X' sem pegar frases comuns (RNF-06, RF-07)

11/11/2026 15:55

## adfe704 — TK-19, TK-20: 51 testes de contratos, protocolos, Tools e grafo com modelo simulado (RNF-08)

11/11/2026 15:55

## efcc167 — TK-16, TK-17, TK-18: CLI, resultado esperado dos cenários e runner com pré-classificação (RF-08, RNF-08)

11/11/2026 16:01

Inclui 5 casos extras (X01-X05) para CA-04, CA-07, CA-09, CA-10 e CA-11.

## 6cc50c2 — TK-21: 1ª execução real dos cenários (12 passou, 1 parcial, 2 falhou)

11/11/2026 16:01

T06 parcial: respondeu sem buscar a norma (sem fonte ACAD-006).
T07 falhou: o modelo filtrou pela categoria errada ('suporte'; a ACAD-007 é 'servicos') e se absteve.
X04 falhou: com uma senha na mensagem, recusou também a dúvida legítima (senha mascarada no log).

## e91257f — TK-11: busca refeita sem filtro quando a categoria escolhida não tem resultado; categorias na descrição (RF-01)

11/11/2026 16:01

Correção da falha do T07 na 1ª execução.

## fdd9cef — TK-12: prompt exige buscar a norma mesmo em resposta óbvia e não recusar a dúvida quando o estudante revela a senha (RF-01, RF-07)

11/11/2026 16:01

Correção de T06 (parcial) e X04 (falhou) na 1ª execução.

## e2bb64b — TK-22: README com arquitetura, modelos, comandos reproduzíveis e configuração (RNF-07)

11/11/2026 16:01

## 68f6b8c — TK-24: IAs usadas e duas decisões técnicas revisadas pelo estudante

11/11/2026 16:01

## dc717d9 — TK-21: 2ª execução real (13 passou, 1 parcial, 1 falhou)

11/11/2026 16:15

T07 e X04 corrigidos. T06 continua parcial: respondeu sem buscar e citou ACAD-001 no texto.
T08 falhou: o modelo não chamou buscar_normas e perguntou se deveria buscar.

## c4bca34 — TK-14, TK-15: nó forcar_busca e remoção de códigos ACAD não recuperados no texto (RF-01, RF-02, ADR-08)

11/11/2026 16:15

Correção de T06 e T08 da 2ª execução. tool_choice=required foi testado e descartado (geração disparou no llama.cpp).

## e219b90 — TK-22: README com o nó forcar_busca e 55 testes

11/11/2026 16:15

## e7d7574 — TK-21: 3ª execução real (14 passou, 1 parcial, 0 falhou)

11/11/2026 16:23

forcar_busca atuou em T06, T08 e T10. T08 parcial: citou ACAD-001 (recuperada com score 0,626) além da ACAD-008.

## 4e63d19 — TK-18: perguntas mascaradas também em resultados.json/.md (RNF-06, CA-11)

11/11/2026 16:24

A senha fictícia do caso X04 aparecia na pergunta gravada nos resultados (o log JSONL já estava mascarado).

## a8b3648 — TK-23: relatório dos 10 cenários, extras, evolução das 3 execuções e análise de falhas

11/11/2026 16:27

## c99222e — TK-25: validação e matriz de rastreabilidade RF/RNF -> tarefas, commits, código, testes e cenários

11/11/2026 16:27

## d2b3148 — TK-26: log do teste manual da CLI nas evidências e varredura de segredos

11/11/2026 16:27

## ebf1cfe — TK-26: histórico de commits exportado para seguir a rastreabilidade pelo ZIP

11/11/2026 16:27

## b7b3b84 — TK-27: evidência real de indisponibilidade do LLM e dos embeddings (RNF-05, item 4.5)

12/11/2026 09:29

Com os containers desligados, T01 e T04 terminaram em erro_llm com mensagem
segura e buscar_normas devolveu erro_servico, sem exceção. Relatório (4.1),
validação e matriz atualizados.

## d5291a5 — TK-27: histórico de commits atualizado

12/11/2026 09:29

## (sem hash) — TK-28: revisão final, intenção em perguntas e status no nó validar (RF-04, RF-05, RNF-02)

14/11/2026

Verbo de pedido solto dentro de pergunta ("qual o prazo para registrar...?") não abre mais a trava de
registro; o nó validar mantém dados_pendentes e trata protocolo em formato inválido quando o modelo marca
outro status; dados_pendentes só é aceito com respaldo da Tool ou pedido explícito, e depois de um
registro bloqueado só uma confirmação ("sim") libera a trava. 80 testes; 4ª e 5ª execuções dos cenários
sem regressão.
Relatório (5.6), validação e matriz atualizados. Feita depois da recriação do repositório git.
