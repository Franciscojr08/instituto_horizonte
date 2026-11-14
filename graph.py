"""Orquestração com LangGraph (TK-14, TK-15).

Reaproveitado da aula "pinecone" (agente -> ToolNode -> agente | END). Acrescentado:
estado explícito, nó `entrada` (mensagem vazia e intenção de registro), nó `auditar_tools`
(fontes recuperadas e Tools executadas), nó `validar` (Pydantic + invariantes + reparo),
limite de rodadas, tratamento de erro do LLM e eventos de log em cada nó.

    START -> entrada -> agente -> (tools -> auditar_tools -> agente)* -> validar -> END
                         agente -> forcar_busca -> tools   (respondeu sem nenhuma Tool: 1x por turno)
                  \\-> validar (mensagem vazia)          validar -> agente (1 reparo de JSON)

Uso: python graph.py --mermaid   (imprime o diagrama do grafo)
"""
import json
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from pydantic import ValidationError

from observabilidade import RegistroExecucao, RegistroNulo, mascarar, resumir
from prompts import (
    PEDIDO_REPARO, SYSTEM_PROMPT, TEXTO_ABSTENCAO, TEXTO_ERRO_LLM, TEXTO_LIMITE_RODADAS,
    TEXTO_MENSAGEM_VAZIA, TEXTO_PROTOCOLO_NAO_CONSULTADO, TEXTO_REGISTRO_NAO_CONFIRMADO,
)
from schemas import PADRAO_FONTE, RespostaAgente, RespostaBruta
from settings import MAX_RODADAS
from tool_agente import NOMES_TOOLS, TOOLS

STATUS_VALIDOS = set(RespostaAgente.model_fields["status"].annotation.__args__)


# --- Estado e contexto ---------------------------------------------------------------

class EstadoAgente(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    pergunta: str                    # mensagem atual do estudante
    intencao_registro: bool          # pedido explícito de registro (lido pela Tool de ação)
    rodadas: int                     # chamadas ao LLM neste turno (RNF-04)
    fontes_recuperadas: list[str]    # ACAD-xxx devolvidos por buscar_normas neste turno
    tools_executadas: list[dict]     # nome, argumentos, resultado e protocolo de cada Tool
    busca_forcada: bool              # o código já forçou buscar_normas neste turno
    tentativas_reparo: int           # reparos de JSON já feitos (máx. 1)
    reparo_pendente: bool
    erro: str | None                 # falha do LLM neste turno
    resposta_final: dict | None      # RespostaAgente validada
    correcoes: list[str]             # ajustes feitos pelo nó validar
    motivo_termino: str


@dataclass
class Contexto:
    registro: RegistroExecucao = field(default_factory=RegistroNulo)
    max_rodadas: int = MAX_RODADAS


# --- Intenção explícita de registro (RF-04) -----------------------------------------

def _simplificar(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


_VERBO_PEDIDO = re.compile(
    r"\b(abr[ae]|abrir|registr[ea]|registrar|cri[ea]|criar|faca|fazer|quero (abrir|registrar|solicitar)"
    r"|gostaria de (abrir|registrar|solicitar)|solicito a abertura|preciso (abrir|registrar))\b"
)
_OBJETO_PEDIDO = re.compile(
    r"\b(solicitac(ao|oes)|pedido|protocolo|chamado|requerimento|ocorrencia|segunda via|declaracao)\b"
)
_NEGACAO = re.compile(r"\bnao (quero|preciso|precisa|desejo|vou)?\s*(abrir|registrar|criar|solicitar)\b")
_INICIO_ORACAO = r"(?:^|[.!?,;:]\s*)"
# Pedido direto: imperativo no início da oração ("Abra...", "Por favor, registre...") ou desejo/pedido
# educado seguido do verbo ("quero abrir", "pode registrar"). Vale mesmo em forma de pergunta.
_PEDIDO_DIRETO = re.compile(
    _INICIO_ORACAO + r"(?:por favor,?\s+)?(?:abra|abre|registre|registra|crie|cria|faca)\b"
    r"|\b(?:quero|gostaria de|preciso|desejo|pode|poderia|podem|poderiam)\s+(?:me\s+)?"
    r"(?:abrir|registrar|criar|fazer|solicitar)\b"
    r"|\bsolicito a abertura\b"
)
# Pergunta sobre o procedimento ("Qual o prazo para registrar...?", "Como fazer a declaração?")
_PERGUNTA = re.compile(
    r"\?|" + _INICIO_ORACAO + r"(?:como|qual|quais|quando|onde|quanto|quantos|quantas|o que|por que|porque"
    r"|posso|e possivel|existe)\b"
)


def detectar_intencao_registro(texto: str) -> bool:
    """Pedido explícito = verbo de pedido + objeto (solicitação, protocolo...) e sem negação.

    Verbo solto ("registrar", "fazer") dentro de uma pergunta é dúvida sobre o procedimento, não
    pedido: só conta o pedido direto (imperativo ou "quero/pode abrir...").
    """
    simples = _simplificar(texto)
    if _NEGACAO.search(simples) or not _OBJETO_PEDIDO.search(simples):
        return False
    if _PEDIDO_DIRETO.search(simples):
        return True
    return bool(_VERBO_PEDIDO.search(simples)) and not _PERGUNTA.search(simples)


_RECUSA = re.compile(  # "não", "não, obrigado", "cancela", "deixa pra lá" (mas não "não sei a turma, é 6001")
    r"^\W*(nao\W*$|nao\W+(obrigad|quero|precis|desej|mais)\w*|cancel\w*|desist\w*|deixa (pra|para) la|esquece)"
)
_CONFIRMACAO = re.compile(
    r"^\W*(sim|s|quero|pode|podes|confirmo|confirmado|confirma|claro|isso|ok|okay|por favor|favor|desejo"
    r"|gostaria|abra|abre|registre|registra)\b"
)


def detectar_confirmacao(texto: str) -> bool:
    """Resposta afirmativa ("sim", "pode abrir") à pergunta "deseja abrir uma solicitação?"."""
    simples = _simplificar(texto)
    return bool(_CONFIRMACAO.search(simples)) and not _RECUSA.search(simples) and not _NEGACAO.search(simples)


def continua_registro_anterior(state: "EstadoAgente", texto: str) -> bool:
    """A mensagem atual continua um registro iniciado no turno anterior?

    - Turno anterior em `dados_pendentes` (o `validar` só aceita esse status se a Tool pediu dados ou se
      houve pedido explícito): a mensagem traz os dados, salvo se for uma desistência.
    - Turno anterior com a Tool de registro `bloqueado` (o agente perguntou se o estudante quer abrir):
      só uma confirmação explícita ("sim", "pode abrir") libera a trava.
    """
    simples = _simplificar(texto)
    if _RECUSA.search(simples):
        return False
    if (state.get("resposta_final") or {}).get("status") == "dados_pendentes":
        return True
    bloqueado = any(t["resultado"] == "bloqueado" for t in _resultados(state, "registrar_solicitacao"))
    return bloqueado and detectar_confirmacao(texto)


# --- Utilidades do nó validar -----------------------------------------------------

def _texto(mensagem: AnyMessage) -> str:
    conteudo = mensagem.content
    if isinstance(conteudo, list):
        conteudo = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in conteudo)
    return re.sub(r"<think>.*?</think>", "", conteudo or "", flags=re.S).strip()


def extrair_json(texto: str) -> dict | None:
    """Objeto JSON da resposta do modelo, tolerando cercas de código e texto ao redor."""
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip())
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim <= inicio:
        return None
    try:
        dados = json.loads(texto[inicio:fim + 1])
    except json.JSONDecodeError:
        return None
    return dados if isinstance(dados, dict) else None


def _ultimo_ai(state: EstadoAgente) -> AIMessage | None:
    for mensagem in reversed(state.get("messages", [])):
        if isinstance(mensagem, AIMessage):
            return mensagem
    return None


def _resultados(state: EstadoAgente, nome: str) -> list[dict]:
    return [t for t in state.get("tools_executadas", []) if t["nome"] == nome]


def derivar_status(state: EstadoAgente) -> str:
    """Status coerente com o que as Tools realmente devolveram neste turno."""
    registros = [t["resultado"] for t in _resultados(state, "registrar_solicitacao")]
    if "registrado" in registros:
        return "solicitacao_registrada"
    if "dados_pendentes" in registros:
        return "dados_pendentes"
    if any(t["resultado"] in {"encontrado", "nao_encontrado"} for t in _resultados(state, "consultar_protocolo")):
        return "protocolo_consultado"
    if state.get("fontes_recuperadas"):
        return "respondido"
    if any(t["resultado"] in {"erro_servico", "formato_invalido"} for t in state.get("tools_executadas", [])):
        return "erro"
    return "abstencao"


def aplicar_invariantes(bruta: RespostaBruta, state: EstadoAgente) -> tuple[RespostaAgente, list[str]]:
    """Spec 3.5: corrige a resposta do modelo para ficar coerente com as evidências e Tools."""
    correcoes: list[str] = []
    resposta, status = bruta.resposta.strip(), bruta.status.strip().lower()
    recuperadas = state.get("fontes_recuperadas", [])

    if status not in STATUS_VALIDOS:
        novo = derivar_status(state)
        correcoes.append(f"status '{bruta.status}' inválido -> '{novo}'")
        status = novo

    # Fontes: só as recuperadas neste turno
    citadas = [f.strip().upper() for f in bruta.fontes]
    fontes = [f for f in dict.fromkeys(citadas) if PADRAO_FONTE.match(f) and f in recuperadas]
    removidas = [f for f in citadas if f not in fontes]
    if removidas:
        correcoes.append(f"fontes não recuperadas removidas: {removidas}")

    # Registro: só existe se a Tool devolveu "registrado"
    registrados = [t for t in _resultados(state, "registrar_solicitacao") if t["resultado"] == "registrado"]
    protocolo = None
    if registrados:
        protocolo = registrados[-1]["protocolo"]
        if status != "solicitacao_registrada":
            correcoes.append(f"status '{status}' -> 'solicitacao_registrada' (Tool registrou {protocolo})")
            status = "solicitacao_registrada"
    elif status == "solicitacao_registrada":
        novo = "dados_pendentes" if derivar_status(state) == "dados_pendentes" else "recusado"
        correcoes.append(f"modelo afirmou registro sem confirmação da Tool -> '{novo}'")
        status, resposta = novo, TEXTO_REGISTRO_NAO_CONFIRMADO

    # Consulta: só vale se a Tool foi executada
    consultas = [t for t in _resultados(state, "consultar_protocolo") if t["resultado"] in {"encontrado", "nao_encontrado"}]
    if status == "protocolo_consultado":
        if consultas:
            protocolo = consultas[-1]["protocolo"]
        else:
            correcoes.append("modelo informou status de protocolo sem consultar -> 'erro'")
            status, resposta = "erro", TEXTO_PROTOCOLO_NAO_CONSULTADO
    elif consultas and status in {"respondido", "abstencao"} and not fontes:
        correcoes.append(f"status '{status}' -> 'protocolo_consultado' (consulta executada)")
        status, protocolo = "protocolo_consultado", consultas[-1]["protocolo"]

    # `dados_pendentes` libera a trava no turno seguinte: só vale se a Tool pediu dados ou se o estudante
    # fez um pedido explícito neste turno (o modelo pode pedir os dados antes de chamar a Tool)
    if status == "dados_pendentes" and derivar_status(state) != "dados_pendentes" \
            and not state.get("intencao_registro"):
        bloqueado = any(t["resultado"] == "bloqueado" for t in _resultados(state, "registrar_solicitacao"))
        novo = "recusado" if bloqueado else derivar_status(state)
        correcoes.append(f"status 'dados_pendentes' sem pedido da Tool nem pedido explícito -> '{novo}'")
        status = novo

    # Tool pediu algo ao estudante: o status segue a Tool, para o pedido não virar abstenção
    if status in {"respondido", "abstencao"} and not fontes and not registrados:
        if derivar_status(state) == "dados_pendentes":
            correcoes.append(f"status '{status}' -> 'dados_pendentes' (Tool pediu dados faltando)")
            status = "dados_pendentes"
        elif not consultas and any(t["resultado"] == "formato_invalido"
                                   for t in _resultados(state, "consultar_protocolo")):
            correcoes.append(f"status '{status}' -> 'erro' (protocolo em formato inválido)")
            status, resposta = "erro", TEXTO_PROTOCOLO_NAO_CONSULTADO

    # Fontes x status
    if status == "respondido" and not fontes:
        if recuperadas:
            fontes = list(recuperadas)
            correcoes.append(f"resposta sem fontes citadas -> usadas as recuperadas {fontes}")
        else:
            correcoes.append("resposta 'respondido' sem evidência -> 'abstencao'")
            status, resposta = "abstencao", TEXTO_ABSTENCAO
    if status == "abstencao" and fontes:
        correcoes.append("abstenção não cita fontes -> fontes removidas")
        fontes = []

    # Códigos ACAD citados no texto também precisam ter sido recuperados (falha do T06, 2ª execução)
    no_texto = set(re.findall(r"\bACAD-\d{3}\b", resposta.upper()))
    inventadas = sorted(no_texto - set(fontes))
    if inventadas:
        for codigo in inventadas:
            resposta = re.sub(rf"\s*\(?\b{codigo}\b\)?", "", resposta, flags=re.I)
        correcoes.append(f"códigos citados no texto sem evidência removidos: {inventadas}")
    if status not in {"protocolo_consultado", "solicitacao_registrada"}:
        protocolo = None
    if not resposta:
        resposta = TEXTO_ABSTENCAO if status == "abstencao" else "Não consegui formular a resposta."
        correcoes.append("resposta vazia substituída")

    return RespostaAgente(resposta=resposta, status=status, fontes=fontes, protocolo=protocolo), correcoes


# --- Grafo ------------------------------------------------------------------------

def criar_grafo(modelo: BaseChatModel | None = None, checkpointer: Any = None):
    """Monta e compila o StateGraph. `modelo` permite injetar um LLM simulado nos testes."""
    if modelo is None:
        from llm import criar_modelo
        modelo = criar_modelo()
    modelo_com_tools = modelo.bind_tools(TOOLS)

    def entrada(state: EstadoAgente, runtime: Runtime[Contexto]) -> dict:
        texto = (state.get("pergunta") or "").strip()
        # Continuação do turno anterior: estudante informa os dados pedidos ou confirma a abertura.
        # Lido antes do reset abaixo, enquanto o estado ainda guarda o turno anterior.
        continua_registro = bool(texto) and continua_registro_anterior(state, texto)
        intencao = bool(texto) and (detectar_intencao_registro(texto) or continua_registro)
        atualizacao = {
            "intencao_registro": intencao, "rodadas": 0, "fontes_recuperadas": [], "tools_executadas": [],
            "busca_forcada": False, "tentativas_reparo": 0, "reparo_pendente": False, "erro": None, "resposta_final": None,
            "correcoes": [], "motivo_termino": "",
        }
        if not texto:
            atualizacao["resposta_final"] = RespostaAgente(resposta=TEXTO_MENSAGEM_VAZIA, status="erro").model_dump()
            atualizacao["motivo_termino"] = "mensagem_vazia"
        runtime.context.registro.evento(
            "entrada", pergunta=texto, vazia=not texto, intencao_registro=intencao,
            continuacao_de_registro=continua_registro,
        )
        return atualizacao

    def agente(state: EstadoAgente, runtime: Runtime[Contexto]) -> dict:
        rodada = state.get("rodadas", 0) + 1
        inicio = time.perf_counter()
        try:
            resposta = modelo_com_tools.invoke([SystemMessage(content=SYSTEM_PROMPT), *state["messages"]])
        except (openai.APIConnectionError, openai.APITimeoutError, openai.APIStatusError) as erro:
            descricao = f"{type(erro).__name__}: {resumir(str(erro), 150)}"
            runtime.context.registro.evento("erro_llm", rodada=rodada, erro=descricao)
            return {"rodadas": rodada, "erro": descricao}
        runtime.context.registro.evento(
            "decisao_agente", rodada=rodada, segundos=round(time.perf_counter() - inicio, 1),
            tools=[{"nome": c["name"], "args": c["args"]} for c in resposta.tool_calls],
            conteudo=resumir(_texto(resposta)),
        )
        return {"messages": [resposta], "rodadas": rodada}

    def forcar_busca(state: EstadoAgente, runtime: Runtime[Contexto]) -> dict:
        """Controle de grounding: o modelo tentou responder sem executar nenhuma Tool no turno.

        Descarta essa resposta e executa buscar_normas com a pergunta do estudante (senhas mascaradas),
        para que a resposta final tenha evidência ou vire abstenção. Acontece no máximo uma vez por turno.
        """
        descartada = state["messages"][-1]
        consulta = mascarar(state.get("pergunta", ""))[:500]
        runtime.context.registro.evento(
            "busca_forcada", motivo="resposta sem nenhuma Tool executada no turno",
            resposta_descartada=resumir(_texto(descartada)), consulta=consulta,
        )
        chamada = {"name": "buscar_normas", "args": {"pergunta": consulta},
                   "id": f"forcada-{uuid.uuid4().hex[:8]}", "type": "tool_call"}
        return {"messages": [RemoveMessage(id=descartada.id), AIMessage(content="", tool_calls=[chamada])],
                "busca_forcada": True}

    def auditar_tools(state: EstadoAgente, runtime: Runtime[Contexto]) -> dict:
        ultimo_ai = _ultimo_ai(state)
        chamadas = {c["id"]: c for c in (ultimo_ai.tool_calls if ultimo_ai else [])}
        fontes = list(state.get("fontes_recuperadas", []))
        executadas = list(state.get("tools_executadas", []))
        for mensagem in reversed(state["messages"]):
            if not isinstance(mensagem, ToolMessage):
                break
            chamada = chamadas.get(mensagem.tool_call_id, {})
            try:
                dados = json.loads(mensagem.content)
            except (json.JSONDecodeError, TypeError):
                dados = {}
            resultado = dados.get("resultado") or ("erro_validacao" if mensagem.status == "error" else "desconhecido")
            protocolo = (dados.get("protocolo") or {}).get("id") if isinstance(dados.get("protocolo"), dict) \
                else dados.get("protocolo_informado")
            novas = [e["fonte"] for e in dados.get("evidencias", [])] if mensagem.name == "buscar_normas" else []
            fontes += [f for f in novas if f not in fontes]
            executadas.append({
                "nome": mensagem.name, "args": chamada.get("args", {}), "resultado": resultado,
                "protocolo": protocolo, "fontes": novas,
            })
            runtime.context.registro.evento(
                "tool", nome=mensagem.name, args=chamada.get("args", {}), resultado=resultado,
                autorizada=mensagem.name in NOMES_TOOLS, fontes=novas,
                scores=[e.get("score") for e in dados.get("evidencias", [])], protocolo=protocolo,
                saida=resumir(mensagem.content, 400),
            )
        return {"fontes_recuperadas": fontes, "tools_executadas": executadas}

    def validar(state: EstadoAgente, runtime: Runtime[Contexto]) -> dict:
        registro = runtime.context.registro
        atualizacao: dict = {"reparo_pendente": False}
        ultimo = state["messages"][-1] if state.get("messages") else None

        if state.get("resposta_final"):  # mensagem vazia, já resolvida na entrada
            final, motivo, correcoes = RespostaAgente(**state["resposta_final"]), state["motivo_termino"], []
        elif state.get("erro"):
            final, motivo, correcoes = RespostaAgente(resposta=TEXTO_ERRO_LLM, status="erro"), "erro_llm", []
        elif isinstance(ultimo, AIMessage) and ultimo.tool_calls:
            # Limite de rodadas com Tools pendentes: fecha as chamadas para o histórico seguir válido
            atualizacao["messages"] = [
                ToolMessage(content='{"resultado": "nao_executada", "motivo": "limite de rodadas"}',
                            tool_call_id=c["id"], name=c["name"]) for c in ultimo.tool_calls
            ]
            final, motivo, correcoes = RespostaAgente(resposta=TEXTO_LIMITE_RODADAS, status="erro"), "limite_rodadas", []
        else:
            dados = extrair_json(_texto(ultimo)) if isinstance(ultimo, AIMessage) else None
            bruta = None
            if dados is not None:
                try:
                    bruta = RespostaBruta.model_validate(dados)
                except ValidationError:
                    bruta = None
            if bruta is None or not bruta.resposta.strip():
                pode_reparar = state.get("tentativas_reparo", 0) < 1 and state.get("rodadas", 0) < runtime.context.max_rodadas
                if pode_reparar:
                    registro.evento("validacao", acao="reparo_solicitado", conteudo=resumir(_texto(ultimo)))
                    return {"reparo_pendente": True, "tentativas_reparo": state.get("tentativas_reparo", 0) + 1,
                            "messages": [HumanMessage(content=PEDIDO_REPARO)]}
                # Sem reparo possível: usa o texto livre (se houver) com status derivado do estado
                texto_livre = _texto(ultimo) if isinstance(ultimo, AIMessage) else ""
                bruta = RespostaBruta(resposta=texto_livre, status=derivar_status(state),
                                      fontes=state.get("fontes_recuperadas", []))
                correcoes_schema = ["JSON inválido após reparo -> texto livre com status derivado das Tools"]
            else:
                correcoes_schema = []
            try:
                final, correcoes = aplicar_invariantes(bruta, state)
                correcoes = correcoes_schema + correcoes
                motivo = "resposta_final"
            except ValidationError as erro:
                final = RespostaAgente(resposta="Não consegui montar uma resposta válida.", status="erro")
                correcoes, motivo = [f"falha de schema: {resumir(str(erro), 200)}"], "erro_schema"

        if correcoes:
            registro.evento("validacao", acao="correcoes", correcoes=correcoes)
        registro.evento(
            "fim", status=final.status, fontes=final.fontes, protocolo=final.protocolo,
            rodadas=state.get("rodadas", 0), motivo_termino=motivo,
            tools=[t["nome"] for t in state.get("tools_executadas", [])],
        )
        return {**atualizacao, "resposta_final": final.model_dump(), "correcoes": correcoes, "motivo_termino": motivo}

    def rota_entrada(state: EstadoAgente) -> str:
        return "validar" if state.get("resposta_final") else "agente"

    def rota_agente(state: EstadoAgente, runtime: Runtime[Contexto]) -> str:
        if state.get("erro"):
            return "validar"
        ultimo = state["messages"][-1]
        if isinstance(ultimo, AIMessage) and ultimo.tool_calls:
            if state.get("rodadas", 0) >= runtime.context.max_rodadas:
                runtime.context.registro.evento("limite_rodadas", rodadas=state["rodadas"])
                return "validar"
            return "tools"
        sem_tools = not state.get("tools_executadas")
        if sem_tools and not state.get("busca_forcada") and len((state.get("pergunta") or "").strip()) >= 3 \
                and state.get("rodadas", 0) < runtime.context.max_rodadas:
            return "forcar_busca"
        return "validar"

    def rota_validar(state: EstadoAgente) -> str:
        return "agente" if state.get("reparo_pendente") else END

    builder = StateGraph(EstadoAgente, context_schema=Contexto)
    builder.add_node("entrada", entrada)
    builder.add_node("agente", agente)
    builder.add_node("forcar_busca", forcar_busca)
    builder.add_node("tools", ToolNode(TOOLS, handle_tool_errors=True))
    builder.add_node("auditar_tools", auditar_tools)
    builder.add_node("validar", validar)
    builder.add_edge(START, "entrada")
    builder.add_conditional_edges("entrada", rota_entrada, ["agente", "validar"])
    builder.add_conditional_edges("agente", rota_agente, ["tools", "forcar_busca", "validar"])
    builder.add_edge("forcar_busca", "tools")
    builder.add_edge("tools", "auditar_tools")
    builder.add_edge("auditar_tools", "agente")
    builder.add_conditional_edges("validar", rota_validar, ["agente", END])
    # Memória da conversa só em RAM, por thread (sessão do terminal ou cenário)
    return builder.compile(checkpointer=checkpointer if checkpointer is not None else InMemorySaver())


def responder(grafo, pergunta: str, thread_id: str, registro: RegistroExecucao | None = None,
              max_rodadas: int = MAX_RODADAS) -> dict:
    """Executa um turno e devolve o estado final (com `resposta_final` validada)."""
    registro = registro or RegistroNulo()
    registro.iniciar_execucao(f"{thread_id}:{time.strftime('%H%M%S')}")
    registro.evento("inicio", thread=thread_id, max_rodadas=max_rodadas)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 2 * max_rodadas + 8}
    return grafo.invoke(
        {"messages": [HumanMessage(content=pergunta)], "pergunta": pergunta},
        config=config, context=Contexto(registro=registro, max_rodadas=max_rodadas),
    )


if __name__ == "__main__":
    import sys

    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel

    class _ModeloDiagrama(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    if "--mermaid" in sys.argv:
        print(criar_grafo(_ModeloDiagrama(responses=[])).get_graph().draw_mermaid())
    else:
        print("Uso: python graph.py --mermaid")
