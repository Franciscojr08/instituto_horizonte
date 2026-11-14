"""Recuperação de conhecimento: embeddings + busca por similaridade no pgvector (TK-06).

Reaproveitado da aula "20260926" (gerar_embedding, vector_para_sql, busca com `<=>`),
agora com metadados (id/fonte, título, categoria), Top-K configurável, filtro por
categoria, corte por score mínimo (abstenção, RF-02) e erros de serviço tratados (RNF-05).
"""
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import openai
import psycopg

from llm import criar_cliente_embeddings
from settings import ARQUIVO_BASE, EMBEDDING_DIMENSOES, EMBEDDING_MODEL, PG_DSN, SCORE_MINIMO, TOP_K

# O Qwen3-Embedding recomenda instruir a consulta (não o documento) para busca assimétrica.
INSTRUCAO_CONSULTA = (
    "Instruct: Given a student's question, retrieve the academic regulation that answers it\nQuery: "
)

SQL_TABELA = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS documentos (
    id         TEXT PRIMARY KEY,
    titulo     TEXT NOT NULL,
    categoria  TEXT NOT NULL,
    conteudo   TEXT NOT NULL,
    embedding  vector({EMBEDDING_DIMENSOES}) NOT NULL
)
"""


class ErroRecuperacao(Exception):
    """Falha esperada de serviço (embeddings ou banco); a mensagem é segura para o usuário."""


@dataclass(frozen=True)
class Evidencia:
    fonte: str
    titulo: str
    categoria: str
    trecho: str
    score: float

    def como_dict(self) -> dict:
        return {
            "fonte": self.fonte, "titulo": self.titulo, "categoria": self.categoria,
            "trecho": self.trecho, "score": round(self.score, 4),
        }


def carregar_documentos(caminho: str | Path = ARQUIVO_BASE) -> list[dict]:
    documentos = json.loads(Path(caminho).read_text(encoding="utf-8"))
    obrigatorios = {"id", "titulo", "categoria", "conteudo"}
    for doc in documentos:
        faltando = obrigatorios - doc.keys()
        if faltando:
            raise ValueError(f"Documento {doc.get('id', '?')} sem os campos {sorted(faltando)}")
    ids = [doc["id"] for doc in documentos]
    if len(set(ids)) != len(ids):
        raise ValueError("A base tem IDs de documento repetidos")
    return documentos


@lru_cache(maxsize=1)
def categorias_da_base() -> frozenset[str]:
    """Categorias válidas para o filtro opcional de `buscar_normas`."""
    return frozenset(doc["categoria"] for doc in carregar_documentos())


def texto_documento(doc: dict) -> str:
    return f"{doc['titulo']}\n{doc['conteudo']}"


def gerar_embedding(texto: str) -> list[float]:
    try:
        resposta = criar_cliente_embeddings().embeddings.create(model=EMBEDDING_MODEL, input=texto)
    except openai.APIError as erro:
        raise ErroRecuperacao(f"servidor de embeddings indisponível ({type(erro).__name__})") from erro
    vetor = resposta.data[0].embedding
    if len(vetor) != EMBEDDING_DIMENSOES:
        raise ErroRecuperacao(
            f"embedding com {len(vetor)} dimensões; esperado {EMBEDDING_DIMENSOES} (EMBEDDING_DIMENSOES)"
        )
    return vetor


def gerar_embedding_consulta(pergunta: str) -> list[float]:
    return gerar_embedding(INSTRUCAO_CONSULTA + pergunta)


def vector_para_sql(vetor: list[float]) -> str:
    return "[" + ",".join(f"{valor:.8f}" for valor in vetor) + "]"


def conectar() -> psycopg.Connection:
    try:
        return psycopg.connect(PG_DSN, connect_timeout=5)
    except psycopg.OperationalError as erro:
        raise ErroRecuperacao("banco vetorial indisponível") from erro


def buscar_contexto(
    pergunta: str,
    top_k: int = TOP_K,
    categoria: str | None = None,
    score_minimo: float = SCORE_MINIMO,
) -> list[Evidencia]:
    """Top-K documentos mais parecidos com a pergunta, já sem os abaixo do score mínimo.

    score = 1 - distância cosseno (1 = idêntico). Lista vazia significa "sem evidência".
    """
    if not pergunta.strip():
        raise ValueError("A pergunta não pode ser vazia")
    if top_k < 1:
        raise ValueError("top_k deve ser positivo")
    vetor = vector_para_sql(gerar_embedding_consulta(pergunta))

    filtro, parametros = "", [vetor]
    if categoria:
        filtro, parametros = "WHERE categoria = %s", [vetor, categoria]
    sql = f"""
        SELECT id, titulo, categoria, conteudo, 1 - (embedding <=> %s::vector) AS score
        FROM documentos
        {filtro}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    try:
        with conectar() as conn, conn.cursor() as cur:
            cur.execute(sql, (*parametros, vetor, top_k))
            linhas = cur.fetchall()
    except psycopg.Error as erro:
        raise ErroRecuperacao(f"falha na consulta ao banco vetorial ({type(erro).__name__})") from erro

    evidencias = [
        Evidencia(fonte=id_, titulo=titulo, categoria=cat, trecho=conteudo, score=float(score))
        for id_, titulo, cat, conteudo, score in linhas
    ]
    return [e for e in evidencias if e.score >= score_minimo]
