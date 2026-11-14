# 01 — Intent

> Etapa 1 do fluxo SDD: **Intent** → Spec → Plan → Tasks → Implement/Test/Validate.
> Responde *por que* o sistema existe e *o que conta como sucesso*, sem decidir tecnologia.

- **Projeto:** Agente de atendimento acadêmico do Instituto Horizonte (fictício)
- **Disciplina:** PEW1029 — Aplicações Avançadas de IA — Turma 6001 — 2026.2
- **Data:** 11/11/2026

## 1. Problema

Estudantes do Instituto Horizonte fazem perguntas repetitivas sobre normas acadêmicas
(prazos, frequência, certificados, revisão de nota) e precisam acompanhar ou abrir solicitações.
Um chatbot comum responderia com confiança mesmo sem base, inventaria status de protocolo
e poderia ser convencido a executar ações indevidas.

## 2. Intenção

Construir um **agente** que:

1. responde dúvidas **apenas** com base nos documentos oficiais simulados, **citando a fonte**;
2. consulta o status real de protocolos, **sem inventar estados**;
3. registra novas solicitações **só quando o estudante pede explicitamente** e os dados estão completos;
4. **se abstém** quando não há evidência e **recusa** ações fora da sua autoridade;
5. deixa **registro auditável** de cada decisão, Tool chamada e resultado.

O protótipo deve tornar visível a separação entre **modelo**, **recuperação**, **Tools**,
**fluxo** e **validação**.

## 3. Usuários

| Usuário | Necessidade |
|---|---|
| Estudante (simulado) | Tirar dúvidas, consultar e abrir solicitações pelo terminal |
| Avaliador (docente) | Reproduzir a execução, ler os registros e conferir os 10 cenários |

## 4. Objetivos

- **O1** — Respostas fundamentadas e com fonte identificada.
- **O2** — Nenhuma informação inventada (normas, valores, datas ou status).
- **O3** — Ações com efeito (registro) protegidas por intenção explícita e validação.
- **O4** — Comportamento seguro diante de pedidos indevidos e de *prompt injection*.
- **O5** — Execução reproduzível e verificável por testes e registros.

## 5. Não-objetivos (fora do escopo)

- Interface gráfica, API HTTP, hospedagem pública ou disponibilidade 24/7.
- Autenticação real de estudantes ou integração com sistemas acadêmicos reais.
- Alterar notas, aprovar trancamentos ou tomar qualquer decisão da coordenação.
- Cálculo de métricas numéricas de retrieval (não exigido pela atividade).

## 6. Restrições

- **100% local:** LLM, embeddings e banco vetorial na máquina do estudante, sem chave de API paga.
- **Hardware:** CPU sem GPU, 18 GB de RAM → modelos quantizados e respostas mais lentas.
- **Dados:** somente a base fictícia fornecida (12 documentos) e os 10 cenários, sem adulterar fatos
  nem reescrever perguntas. Nenhum dado real ou credencial no repositório.
- **Ponto de partida:** reaproveitar o código das aulas anteriores (LangChain/LangGraph e RAG com
  pgvector) em vez de começar do zero.

## 7. Critérios de sucesso

1. Os 10 cenários de `data/cenarios_de_teste_aluno.csv` executados com resultado
   (passou / parcial / falhou) e evidência registrada.
2. Todo requisito da Spec rastreável até tarefa, código e teste (`matriz_rastreabilidade.md`).
3. Um avaliador consegue instalar, indexar e executar seguindo apenas o README.
