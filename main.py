"""Atendimento acadêmico do Instituto Horizonte no terminal (TK-16, RF-08).

Uso: python main.py
Comandos: /nova (nova conversa), /ajuda, /sair
Também aceita entrada pelo stdin:  printf 'pergunta\\n/sair\\n' | python main.py
"""
import time
import uuid

from graph import criar_grafo, responder
from observabilidade import RegistroExecucao
from settings import LLM_MODEL

AJUDA = """Pergunte sobre normas acadêmicas, consulte um protocolo (ex.: SOL-1001)
ou peça para abrir uma solicitação. Comandos: /nova  /ajuda  /sair"""


def mostrar(estado: dict, segundos: float) -> None:
    final = estado["resposta_final"]
    print(f"\nAssistente: {final['resposta']}")
    detalhes = [f"status: {final['status']}"]
    if final["fontes"]:
        detalhes.append(f"fontes: {', '.join(final['fontes'])}")
    if final["protocolo"]:
        detalhes.append(f"protocolo: {final['protocolo']}")
    tools = [t["nome"] for t in estado.get("tools_executadas", [])]
    if tools:
        detalhes.append(f"tools: {', '.join(tools)}")
    detalhes.append(f"{segundos:.0f} s")
    print(f"  [{' | '.join(detalhes)}]\n")


def main():
    registro = RegistroExecucao("cli")
    print("Instituto Horizonte — atendimento acadêmico (protótipo, dados fictícios)")
    print(f"Modelo local: {LLM_MODEL} | log: {registro.caminho}")
    print(AJUDA, "\n")
    grafo = criar_grafo()
    thread = f"cli-{uuid.uuid4().hex[:8]}"

    while True:
        try:
            pergunta = input("Você: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        comando = pergunta.strip().lower()
        if comando in {"/sair", "sair", "exit"}:
            break
        if comando == "/ajuda":
            print(AJUDA, "\n")
            continue
        if comando == "/nova":
            thread = f"cli-{uuid.uuid4().hex[:8]}"
            print("(nova conversa)\n")
            continue
        inicio = time.perf_counter()
        print("  (consultando...)")
        mostrar(responder(grafo, pergunta, thread, registro), time.perf_counter() - inicio)
    print("Até logo!")


if __name__ == "__main__":
    main()
