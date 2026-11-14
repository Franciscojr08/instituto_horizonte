# Uso de IA no desenvolvimento

Entregável da seção 5 do enunciado: quais IAs auxiliaram o desenvolvimento e duas decisões técnicas
revisadas pelo estudante. A seção 8 permite usar IA para planejar, codificar e revisar, desde que as
decisões sejam documentadas e o funcionamento seja comprovado por código e evidências verificáveis.

## 1. IAs utilizadas

| IA | Onde | Para quê |
|---|---|---|
| **Claude Code** (modelo Claude Opus 5.5, Anthropic) | Terminal, no repositório do projeto | Leitura do enunciado e dos materiais das aulas; redação dos documentos SDD (Intent, Spec, Plan, Tasks); adaptação do código reaproveitado; escrita dos testes, do README e do relatório; execução dos cenários e análise dos resultados |
| **Qwen3-30B-A3B-Instruct-2507** (local, llama.cpp) | Dentro do agente | É o LLM do próprio agente (decisão das Tools e redação das respostas). Não foi usado para escrever o código |
| **Qwen3-Embedding-0.6B** (local, llama.cpp) | Dentro do agente | Embeddings da ingestão e da consulta (RAG) |

**Como a IA de desenvolvimento foi usada:** cada etapa foi proposta pela IA e aprovada pelo estudante
antes de seguir (Intent/Spec → Plan → Tasks → implementação por fase). As escolhas de infraestrutura e o
reaproveitamento do código das aulas foram decisões do estudante. Cada tarefa virou um commit com o ID
`TK-xx` (TK-01 a TK-27). Esse histórico foi exportado para [`sdd/historico_commits.md`](sdd/historico_commits.md),
com hash, data e descrição de cada commit, antes de o repositório git ser recriado do zero em 14/11/2026;
é por esse arquivo que se audita o que foi feito em cada passo. A TK-28 (revisão final) foi feita depois da
exportação e está descrita em `sdd/04_tasks.md` e na seção 5.6 do `RELATORIO.md`.

**O que foi conferido com execução real, e não apenas aceito:** conexão e Tool Calling do modelo
(`00_testar_llm.py`), ingestão idempotente, scores de retrieval dos 10 cenários (calibração do
`SCORE_MINIMO`), comportamento das Tools (trava, pendências, persistência), 80 testes automatizados e a
execução dos cenários com o modelo local (`resultados/`).

## 2. Decisões técnicas revisadas pelo estudante

### Decisão 1 — Stack 100% local em vez de serviços em nuvem (ADR-01, ADR-02)

- **Proposta inicial da IA:** Python local + Pinecone (já usado na aula) + Groq ou Gemini como LLM, por
  serem mais rápidos e terem Tool Calling confiável.
- **Revisão do estudante:** optou por **tudo local** (modalidade E), sem chave de API nem dependência de
  cota gratuita. Entre os modelos locais, escolheu o **Qwen3-30B-A3B** no llama.cpp, em vez do qwen3-4b
  do LocalAI usado na aula.
- **Justificativa:** sem risco de esgotar o free tier no meio dos testes (seção 8 do enunciado), sem
  enviar nenhum dado para fora da máquina e com infraestrutura já validada no computador do estudante.
  O 30B é MoE (~3B parâmetros ativos): mais lento que um modelo em nuvem, porém bem mais confiável em
  Tool Calling que os modelos pequenos testados na aula.
- **Consequência aceita:** respostas de 15 s a 1 min em CPU e ~12 GB de RAM ocupados pelo LLM.

### Decisão 2 — Reaproveitar o código das aulas diretamente no projeto (ADR-03, ADR-04)

- **Proposta inicial da IA:** copiar os arquivos das aulas para uma pasta `referencia/` e escrever o
  agente do zero ao lado, consultando-os.
- **Revisão do estudante:** rejeitou a pasta de referência e determinou usar **os próprios arquivos das
  aulas como base do projeto**, mantendo os nomes (`settings.py`, `llm.py`, `rag_utils.py`,
  `tool_agente.py`, `sistema_chamados.py`, `graph.py`, `12_ingestao.py`, `13_busca_semantica.py`) e
  descartando apenas os redundantes. Também definiu manter os protocolos em **JSON**
  (`sistema_chamados.py` da aula) em vez de uma tabela no Postgres.
- **Justificativa:** demonstra continuidade com o conteúdo da disciplina, reduz código novo e deixa o
  reuso auditável: o primeiro commit guardou os arquivos originais e os seguintes registraram cada adaptação
  (ver `sdd/historico_commits.md` e a coluna "Origem" da tabela de estrutura do README).
- **Consequência aceita:** alguns nomes herdados não descrevem perfeitamente o novo domínio
  (ex.: `sistema_chamados.py` guarda protocolos acadêmicos).

## 3. Cuidados

- Nenhuma credencial, documento privado ou dado acadêmico real foi enviado à IA de desenvolvimento ou ao
  repositório; a base e os cenários são os fictícios fornecidos.
- O LLM do agente roda localmente: as perguntas de teste não saem da máquina.
