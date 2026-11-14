"""Busca semântica sem LLM (TK-08): evidência de retrieval e calibração do SCORE_MINIMO.

Reaproveitado da aula "20260926". Mostra o Top-K com score, sem aplicar o corte, e marca
quais evidências passariam pelo SCORE_MINIMO atual.

Uso:
  python 13_busca_semantica.py "Qual o prazo da declaração de matrícula?"
  python 13_busca_semantica.py --cenarios          # as 10 perguntas oficiais
  python 13_busca_semantica.py --cenarios --top-k 5
"""
import argparse
import csv

from rag_utils import buscar_contexto
from settings import ARQUIVO_CENARIOS, SCORE_MINIMO, TOP_K


def carregar_cenarios() -> list[tuple[str, str]]:
    with open(ARQUIVO_CENARIOS, encoding="utf-8-sig", newline="") as arquivo:
        return [(linha["caso"], linha["pergunta"]) for linha in csv.DictReader(arquivo, delimiter=";")]


def mostrar(caso: str, pergunta: str, top_k: int) -> None:
    print(f"\n{caso}: {pergunta}")
    for posicao, ev in enumerate(buscar_contexto(pergunta, top_k=top_k, score_minimo=0.0), start=1):
        marca = "✔" if ev.score >= SCORE_MINIMO else "✘"
        print(f"  {posicao}. {marca} {ev.score:.4f}  {ev.fonte}  [{ev.categoria}]  {ev.titulo}")


def main():
    parser = argparse.ArgumentParser(description="Busca semântica sem LLM")
    parser.add_argument("pergunta", nargs="?")
    parser.add_argument("--cenarios", action="store_true", help="usar as 10 perguntas oficiais")
    parser.add_argument("--top-k", type=int, default=TOP_K)
    args = parser.parse_args()
    if not args.pergunta and not args.cenarios:
        parser.error("informe uma pergunta ou --cenarios")

    print(f"Top-K: {args.top_k} | SCORE_MINIMO: {SCORE_MINIMO} (✔ passa, ✘ seria descartada)")
    entradas = carregar_cenarios() if args.cenarios else [("consulta", args.pergunta)]
    for caso, pergunta in entradas:
        mostrar(caso, pergunta, args.top_k)


if __name__ == "__main__":
    main()
