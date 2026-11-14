# Matriz de rastreabilidade

> Liga cada requisito de `02_spec.md` às tarefas (`04_tasks.md`), aos commits ([`historico_commits.md`](historico_commits.md)), ao código,
> aos testes automatizados (`tests/`) e aos cenários reais (`resultados/execucao_20261114-175041/`, 5ª execução, mesmo placar da 3ª e da 4ª).
> **Commits:** os hashes são do repositório original, cujo histórico foi exportado para
> `historico_commits.md` antes de o git ser recriado (14/11/2026). A TK-28 foi feita depois da exportação e
> não tem hash; está descrita em `04_tasks.md` e no `RELATORIO.md` (seção 5.6).
> **Status:** ✅ verificado · ⚠️ verificado com ressalva (ver `RELATORIO.md`).

## Requisitos funcionais

| Req. | Tarefas | Commits | Código | Testes automatizados | Cenários reais | Status |
|---|---|---|---|---|---|---|
| **RF-01** responder com fonte | TK-06, TK-11, TK-12, TK-14, TK-15 | 1079f2a, 39568db, 7a58d8c, fd028bb, e91257f, fdd9cef, c4bca34 | `rag_utils.buscar_contexto`, `tool_agente.buscar_normas`, `graph.forcar_busca`, `graph.aplicar_invariantes` | `test_fluxo_rag_com_fonte`, `test_validar_remove_fonte_nao_recuperada`, `test_busca_forcada_quando_o_modelo_responde_sem_tool`, `test_codigo_citado_no_texto_sem_evidencia_e_removido`, `test_buscar_normas_refaz_sem_filtro_quando_categoria_nao_tem_resultado` | T01, T02, T03, T06, T07, T08, X04 | ⚠️ T08 citou fonte secundária recuperada |
| **RF-02** abster-se sem evidência | TK-06, TK-08, TK-15 | 1079f2a, c166277, c4bca34 | `SCORE_MINIMO` em `rag_utils`, invariante `abstencao` em `graph.aplicar_invariantes` | `test_resposta_sem_evidencia_vira_abstencao`, `test_buscar_normas_ok_sem_evidencia_e_erro` | T09 | ✅ |
| **RF-03** consultar protocolo sem inventar | TK-10, TK-11, TK-15 | fd479d2, 39568db, fd028bb | `sistema_chamados.consultar_protocolo_local`, `tool_agente.consultar_protocolo` | `test_consulta_protocolos_iniciais`, `test_consultar_protocolo_tool`, `test_validar_corrige_status_da_consulta`, `test_protocolo_em_formato_invalido_vira_erro_com_orientacao` | T04, X03 | ✅ |
| **RF-04** registrar só com pedido explícito | TK-11, TK-14, TK-28 | 39568db, fd028bb | `graph.detectar_intencao_registro`, nó `entrada`, `InjectedState` em `registrar_solicitacao` | `test_detectar_intencao_registro` (16 casos, inclusive verbo de pedido dentro de pergunta), `test_detectar_confirmacao`, `test_bloqueado_com_status_dados_pendentes_vira_recusado_e_so_confirmacao_libera`, `test_bloqueado_seguido_de_recusa_ou_assunto_novo_nao_libera`, `test_dados_pendentes_inventado_pelo_modelo_nao_libera_o_turno_seguinte`, `test_registrar_sem_intencao_e_bloqueado`, `test_registro_sem_intencao_e_bloqueado_mesmo_se_o_modelo_tentar`, `test_intencao_nao_aparece_no_schema_do_llm` | T07 (sem registro), T05/X01 (com pedido) | ✅ |
| **RF-05** validar dados, pedir os faltantes e persistir | TK-10, TK-11, TK-28 | fd479d2, 39568db | `sistema_chamados.campos_faltando`, `registrar_solicitacao_local` (escrita atômica), `graph.aplicar_invariantes` (mantém `dados_pendentes`) | `test_registro_com_dados_genericos_fica_pendente_e_nao_persiste`, `test_registro_descricao_curta_fica_pendente`, `test_registro_sequencial_persiste_e_sobrevive_a_recarga`, `test_dados_pendentes_e_continuacao_no_turno_seguinte`, `test_registro_com_intencao_persiste`, `test_dados_pendentes_prevalece_sobre_status_errado_do_modelo`, `test_dados_pendentes_sem_tool_vale_quando_houve_pedido_explicito` | T05, X01 | ✅ |
| **RF-06** recusar ações fora da autoridade | TK-12, TK-14 | 7a58d8c, fd028bb | `prompts.SYSTEM_PROMPT`; não existe Tool de alteração; trava da Tool de ação | `test_tool_desconhecida_e_argumento_invalido_sao_rejeitados` | T10 | ✅ |
| **RF-07** nunca pedir/repassar credenciais | TK-11, TK-12, TK-13 | 8d48424, a5c19cc, fdd9cef, 4e63d19 | `observabilidade.contem_credencial`/`mascarar`, validadores em `schemas`, `prompts` | `test_args_buscar_normas_rejeita_credencial_e_categoria_invalida`, `test_registrar_rejeita_credencial`, `test_mascarar_e_detectar_credenciais`, `test_busca_forcada_mascara_senha_da_pergunta` | T06, X04 | ✅ |
| **RF-08** modo interativo e em lote | TK-16, TK-18 | efcc167, 4e63d19 | `main.py`, `executar_cenarios.py` | — (execução manual) | 5 execuções em `resultados/` | ✅ |

## Requisitos não funcionais

| Req. | Tarefas | Commits | Código | Testes automatizados | Evidência real | Status |
|---|---|---|---|---|---|---|
| **RNF-01** execução local | TK-01, TK-02, TK-03 | 7086f00, 7932bcc, 755f7fd | `compose.yaml`, `settings.py`, `llm.py` | — | `00_testar_llm.py` (Tool Calling OK); todas as execuções sem chave de API | ✅ |
| **RNF-02** saída estruturada validada | TK-09, TK-15 | 4e4a91f, fd028bb | `schemas.RespostaAgente`/`RespostaBruta`, nó `validar` | `test_resposta_invalida_levanta_validation_error` (8 casos), `test_reparo_de_schema`, `test_schema_invalido_apos_reparo_usa_status_derivado`, `test_extrair_json_tolera_cercas_e_texto` | `resultados.json` (todas as respostas no contrato) | ✅ |
| **RNF-03** indexação com metadados, Top-K, mesmo embedding | TK-05, TK-06, TK-07, TK-08 | 0d12183, 1079f2a, b3cb9c7, c166277 | `sql/init.sql`, `12_ingestao.py`, `rag_utils.py` | — (depende do pgvector) | `12_ingestao.py` (12 registros, 11 categorias, idempotente); `resultados/busca_semantica_cenarios.txt` | ✅ |
| **RNF-04** limite de rodadas | TK-14 | fd028bb | `MAX_RODADAS`, `rota_agente`, `recursion_limit` | `test_limite_de_rodadas` | X05 (evento `limite_rodadas`) | ✅ |
| **RNF-05** tratamento de erros | TK-03, TK-06, TK-14, TK-27 | 755f7fd, 1079f2a, fd028bb | `ErroRecuperacao`, captura de `openai.APIError` no nó `agente`, nó `entrada` | `test_llm_indisponivel`, `test_mensagem_vazia_nao_chama_o_llm`, `test_erro_de_servico_na_busca` | X02; T07 da 1ª execução (argumento inválido tratado); `resultados/indisponibilidade_20261112-092833/` (LLM e embeddings desligados: `erro_llm` e `erro_servico`) | ✅ |
| **RNF-06** observabilidade sem segredos | TK-13, TK-14, TK-18 | 8d48424, a5c19cc, fd028bb, 4e63d19 | `observabilidade.RegistroExecucao`, eventos em todos os nós | `test_registro_execucao_grava_jsonl_mascarado`, `test_limite_de_rodadas` (eventos) | logs `*.jsonl` das 5 execuções; 0 ocorrências da senha de teste | ✅ |
| **RNF-07** reprodutibilidade | TK-01, TK-02, TK-04, TK-22, TK-26 | 7086f00, 7932bcc, f83a7f3, e2bb64b | `README.md`, `.env.example`, `compose.yaml`, `requirements.txt`, `.gitignore` | — | instalação em venv limpo; URLs dos modelos conferidas | ✅ |
| **RNF-08** testes sem LLM + cenários reais | TK-17, TK-18, TK-19, TK-20, TK-21 | adfe704, efcc167, c4bca34, 6cc50c2, dc717d9, e7d7574 | `tests/`, `executar_cenarios.py`, `data/esperado_cenarios.json` | 80 testes | 5 execuções reais | ✅ |
| **RNF-09** só Tools autorizadas, argumentos validados | TK-09, TK-11, TK-14 | 4e4a91f, 39568db, fd028bb | `args_schema` Pydantic, `ToolNode(handle_tool_errors=True)` | `test_tool_desconhecida_e_argumento_invalido_sao_rejeitados`, `test_args_consultar_normaliza` | T07 da 1ª execução (categoria inválida rejeitada) | ✅ |

## Critérios de aceite → evidência

| CA | Evidência real (5ª execução) | Teste automatizado |
|---|---|---|
| CA-01 | T01, T02, T03, T06, T07 (T08 parcial) | `test_fluxo_rag_com_fonte` |
| CA-02 | T09 | `test_resposta_sem_evidencia_vira_abstencao` |
| CA-03 | T04 | `test_consulta_protocolos_iniciais` |
| CA-04 | X03 | `test_consulta_protocolos_iniciais` |
| CA-05 | T07 | `test_registro_sem_intencao_e_bloqueado_mesmo_se_o_modelo_tentar` |
| CA-06 | T05 | `test_registro_com_dados_genericos_fica_pendente_e_nao_persiste` |
| CA-07 | X01 | `test_registro_sequencial_persiste_e_sobrevive_a_recarga` |
| CA-08 | T10 | `test_tool_desconhecida_e_argumento_invalido_sao_rejeitados` |
| CA-09 | X05 | `test_limite_de_rodadas` |
| CA-10 | X02; T01/T04 com o LLM desligado | `test_llm_indisponivel`, `test_mensagem_vazia_nao_chama_o_llm` |
| CA-11 | X04 (log e resultados mascarados) | `test_registro_execucao_grava_jsonl_mascarado` |

## Decisões (ADR) → onde aparecem

| ADR | Código | Evidência |
|---|---|---|
| ADR-01 llama.cpp local | `compose.yaml`, `llm.py` | `00_testar_llm.py` |
| ADR-02 Qwen3-30B-A3B | `compose.yaml`, `settings.py` | 3 execuções |
| ADR-03 pgvector com SQL próprio | `rag_utils.py`, `12_ingestao.py` | `busca_semantica_cenarios.txt` |
| ADR-04 protocolos em JSON | `sistema_chamados.py` | `protocolos.json` de cada execução |
| ADR-05 trava no código | `tool_agente.registrar_solicitacao` | T07, X04 sem registro |
| ADR-06 JSON + Pydantic + reparo | `graph.validar` | `test_reparo_de_schema` |
| ADR-07 limiar + invariantes | `rag_utils`, `graph.aplicar_invariantes` | T09; correções do `validar` na 1ª e 2ª execuções |
| ADR-08 busca obrigatória pelo grafo | `graph.forcar_busca` | eventos `busca_forcada` em T06, T08 e T10 (3ª, 4ª e 5ª execuções) |
