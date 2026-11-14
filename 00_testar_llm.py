"""Teste rápido do LLM local: conexão e Tool Calling, sem executar Tools (TK-03).

Uso: python 00_testar_llm.py
"""
import time

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from llm import criar_modelo
from settings import LLM_BASE_URL, LLM_MODEL


@tool
def consultar_protocolo(protocolo: str) -> str:
    """Consulta o status de um protocolo acadêmico pelo ID, por exemplo SOL-1001."""
    return "não executada neste teste"


def main():
    print(f"Endpoint: {LLM_BASE_URL} | modelo: {LLM_MODEL}")
    modelo = criar_modelo()

    inicio = time.perf_counter()
    resposta = modelo.invoke([HumanMessage(content="Responda apenas: conexão OK")])
    print(f"1) Resposta ({time.perf_counter() - inicio:.1f} s): {resposta.content!r}")

    inicio = time.perf_counter()
    resposta = modelo.bind_tools([consultar_protocolo]).invoke(
        [HumanMessage(content="Qual o status do protocolo SOL-1001?")]
    )
    print(f"2) Tool calls ({time.perf_counter() - inicio:.1f} s): {resposta.tool_calls}")
    if not resposta.tool_calls:
        raise SystemExit("ATENÇÃO: o modelo não solicitou Tool Calling; verifique --jinja ou troque o modelo.")
    print("OK: o modelo solicitou a Tool.")


if __name__ == "__main__":
    main()
