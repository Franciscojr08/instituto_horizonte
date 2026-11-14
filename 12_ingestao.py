"""Indexa a base acadêmica no pgvector (TK-07).

Reaproveitado da aula "20260926". Agora guarda id, título e categoria como metadados e faz
upsert por id: rodar de novo atualiza os registros, sem duplicar (idempotente).

Uso: python 12_ingestao.py [--arquivo data/base_conhecimento_academica.json]
"""
import argparse
import time
from pathlib import Path

from rag_utils import SQL_TABELA, carregar_documentos, conectar, gerar_embedding, texto_documento, vector_para_sql
from settings import ARQUIVO_BASE, EMBEDDING_MODEL

SQL_UPSERT = """
INSERT INTO documentos (id, titulo, categoria, conteudo, embedding)
VALUES (%s, %s, %s, %s, %s::vector)
ON CONFLICT (id) DO UPDATE SET
    titulo = EXCLUDED.titulo,
    categoria = EXCLUDED.categoria,
    conteudo = EXCLUDED.conteudo,
    embedding = EXCLUDED.embedding
"""


def main():
    parser = argparse.ArgumentParser(description="Indexar a base acadêmica no pgvector")
    parser.add_argument("--arquivo", type=Path, default=ARQUIVO_BASE)
    args = parser.parse_args()

    documentos = carregar_documentos(args.arquivo)
    print(f"Arquivo: {args.arquivo.name} | documentos: {len(documentos)} | embedding: {EMBEDDING_MODEL}")

    inicio = time.perf_counter()
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(SQL_TABELA)
        for doc in documentos:
            vetor = vector_para_sql(gerar_embedding(texto_documento(doc)))
            cur.execute(SQL_UPSERT, (doc["id"], doc["titulo"], doc["categoria"], doc["conteudo"], vetor))
            print(f"  {doc['id']}  [{doc['categoria']}]  {doc['titulo']}")
        cur.execute("SELECT count(*), count(DISTINCT categoria) FROM documentos")
        total, categorias = cur.fetchone()

    print(f"\nIndexados: {len(documentos)} em {time.perf_counter() - inicio:.1f} s")
    print(f"Tabela documentos: {total} registros, {categorias} categorias")


if __name__ == "__main__":
    main()
