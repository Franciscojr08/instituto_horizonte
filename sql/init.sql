-- Executado pelo pgvector na primeira subida do volume (docker-entrypoint-initdb.d).
-- O 12_ingestao.py também cria a tabela se ela não existir, para funcionar com volumes antigos.
CREATE EXTENSION IF NOT EXISTS vector;

-- Um registro por documento da base (ACAD-001..ACAD-012); id, título e categoria são os metadados.
-- vector(1024): dimensão do Qwen3-Embedding-0.6B.
CREATE TABLE IF NOT EXISTS documentos (
    id         TEXT PRIMARY KEY,
    titulo     TEXT NOT NULL,
    categoria  TEXT NOT NULL,
    conteudo   TEXT NOT NULL,
    embedding  vector(1024) NOT NULL
);
