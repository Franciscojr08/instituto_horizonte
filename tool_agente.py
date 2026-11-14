"""As três Tools tipadas do agente (TK-11): conhecimento, consulta e ação.

Reaproveitado da aula "pinecone" (buscar_conhecimento, consultar_chamado, abrir_chamado).
Mudanças: contratos Pydantic (`args_schema`), saída JSON com a chave `resultado`, erros de
serviço devolvidos como dados, e a trava da Tool de ação no código: ela recebe do estado do
grafo se houve pedido explícito (`InjectedState`), valor que o LLM não vê nem consegue forjar.
"""
import json
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from rag_utils import ErroRecuperacao, buscar_contexto
from schemas import ArgsBuscarNormas, ArgsConsultarProtocolo, ArgsRegistrarSolicitacao
from sistema_chamados import consultar_protocolo_local, registrar_solicitacao_local


def _json(dados: dict) -> str:
    return json.dumps(dados, ensure_ascii=False)


@tool("buscar_normas", args_schema=ArgsBuscarNormas)
def buscar_normas(pergunta: str, categoria: str | None = None) -> str:
    """Pesquisa as normas acadêmicas oficiais do Instituto Horizonte (prazos, documentos,
    certificados, frequência, notas, matrícula, biblioteca, suporte, segurança, financeiro).
    Use SEMPRE antes de responder qualquer dúvida sobre regras ou procedimentos."""
    filtro_ignorado = False
    try:
        evidencias = buscar_contexto(pergunta, categoria=categoria)
        if not evidencias and categoria:
            # O modelo pode escolher a categoria errada (falha observada no T07 da 1ª execução:
            # "suporte" em vez de "servicos"); sem resultado, repete a busca em toda a base.
            evidencias, filtro_ignorado = buscar_contexto(pergunta), True
    except ErroRecuperacao as erro:
        return _json({"resultado": "erro_servico", "mensagem": str(erro)})
    if not evidencias:
        return _json({
            "resultado": "sem_evidencia", "evidencias": [],
            "orientacao": "Nenhuma norma da base trata disso. Não responda com suposições: abstenha-se.",
        })
    saida = {"resultado": "ok", "evidencias": [e.como_dict() for e in evidencias]}
    if filtro_ignorado:
        saida["observacao"] = f"Nada encontrado na categoria '{categoria}'; busca refeita em toda a base."
    return _json(saida)


@tool("consultar_protocolo", args_schema=ArgsConsultarProtocolo)
def consultar_protocolo(protocolo: str) -> str:
    """Consulta o status atual de um protocolo de solicitação acadêmica (formato SOL-0000).
    Use sempre que o estudante perguntar sobre um protocolo; nunca deduza o status."""
    return _json(consultar_protocolo_local(protocolo))


class _ArgsRegistrarComEstado(ArgsRegistrarSolicitacao):
    # Injetado pelo ToolNode a partir do estado; não aparece no schema enviado ao LLM.
    intencao_registro: Annotated[bool, InjectedState("intencao_registro")] = False


@tool("registrar_solicitacao", args_schema=_ArgsRegistrarComEstado)
def registrar_solicitacao(
    tipo: str,
    descricao: str,
    turma: str | None = None,
    justificativa: str | None = None,
    intencao_registro: bool = False,
) -> str:
    """Registra uma NOVA solicitação no atendimento acadêmico e devolve o número do protocolo.
    Use SOMENTE quando o estudante pedir explicitamente para abrir/registrar uma solicitação.
    Preencha turma e justificativa apenas com o que o estudante informou; nunca invente.
    Se a resposta for 'dados_pendentes', peça ao estudante os campos faltando."""
    if not intencao_registro:
        return _json({
            "resultado": "bloqueado",
            "motivo": "O estudante não pediu explicitamente a abertura de uma solicitação. "
                      "Oriente sobre o procedimento e pergunte se ele deseja registrar.",
        })
    return _json(registrar_solicitacao_local(tipo, descricao, turma, justificativa))


TOOLS = [buscar_normas, consultar_protocolo, registrar_solicitacao]
NOMES_TOOLS = {t.name for t in TOOLS}
